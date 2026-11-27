"""Copy spend_app.WorkloadSession rows into console_app.WorkloadSession.

Until now one launch could be written to BOTH tables (a SLURM job by
``begin_workload`` and again by spend_app's ``open_workload``). The spend row
is folded into the console row of the same launch where one exists, and
copied as a new row only where it does not:

* job      -> the console row of the same user and SLURM job id;
* terminal -> every not-yet-annotated console terminal row of the user that
              overlaps the spend row in time (the spend row was ONE record
              per user for the shared allocation, so it may cover several);
* service  -> always a new row (console never recorded services).

Every touched console row keeps the spend row's id and times under
``tags["spend_app.workload"]`` so the reverse migration recreates the spend
rows exactly, and deletes the rows this migration created.
"""

import uuid

from django.db import migrations

MARK = "spend_app.workload"
CREATED = "spend_app.migrated"
RESOURCE_FIELDS = ("cpus", "memory_gb", "gpus", "max_seconds", "label")


def _mark(old) -> dict:
    return {
        "id": old.pk,
        "kind": old.kind,
        "project_id": old.project_id,
        "scheduler_id": old.scheduler_id,
        "started_at": old.started_at.isoformat(),
        "stopped_at": old.stopped_at.isoformat() if old.stopped_at else None,
        "stop_reason": old.stop_reason,
    }


def _matches(Console, old):
    if old.kind == "job" and old.scheduler_id:
        return list(
            Console.objects.filter(
                user_id=old.user_id, workload="job", scheduler_job_id=old.scheduler_id
            ).exclude(tags__has_key=MARK)
        )
    if old.kind == "terminal":
        qs = Console.objects.filter(user_id=old.user_id, workload="terminal").exclude(
            stopped_at__lt=old.started_at
        )
        if old.stopped_at is not None:
            qs = qs.filter(started_at__lt=old.stopped_at)
        return list(qs.exclude(tags__has_key=MARK))
    return []


def copy_spend_rows(apps, schema_editor):
    Spend = apps.get_model("spend_app", "WorkloadSession")
    Console = apps.get_model("console_app", "WorkloadSession")
    Project = apps.get_model("project_app", "Project")

    for old in Spend.objects.order_by("started_at", "pk").iterator():
        resources = {name: getattr(old, name) for name in RESOURCE_FIELDS}
        matches = _matches(Console, old)
        for row in matches:
            for name, value in resources.items():
                setattr(row, name, value)
            if old.kind == "job" and row.stopped_at is None and old.stopped_at:
                row.stopped_at = old.stopped_at
            if row.stopped_at is not None and not row.stop_reason:
                row.stop_reason = old.stop_reason
            row.tags = {**row.tags, MARK: _mark(old)}
            row.save()
        if matches:
            continue
        project_id = old.project_id
        if (
            project_id is not None
            and not Project.objects.filter(pk=project_id).exists()
        ):
            project_id = None
        Console.objects.create(
            session_id=uuid.uuid4(),
            user_id=old.user_id,
            project_id=project_id,
            workload=old.kind,
            scheduler="local" if old.kind == "service" else "slurm",
            scheduler_job_id=old.scheduler_id[:64],
            host="",
            tags={MARK: _mark(old), CREATED: True},
            started_at=old.started_at,
            stopped_at=old.stopped_at,
            stop_reason=old.stop_reason,
            **resources,
        )


def restore_spend_rows(apps, schema_editor):
    from django.utils.dateparse import parse_datetime

    Spend = apps.get_model("spend_app", "WorkloadSession")
    Console = apps.get_model("console_app", "WorkloadSession")

    restored = set()
    for row in Console.objects.filter(tags__has_key=MARK).order_by("started_at"):
        mark = row.tags[MARK]
        if mark["id"] not in restored and row.user_id is not None:
            restored.add(mark["id"])
            stopped = mark["stopped_at"]
            Spend.objects.create(
                pk=mark["id"],
                user_id=row.user_id,
                project_id=mark["project_id"],
                kind=mark["kind"],
                scheduler_id=mark["scheduler_id"],
                started_at=parse_datetime(mark["started_at"]),
                stopped_at=parse_datetime(stopped) if stopped else None,
                stop_reason=mark["stop_reason"],
                **{name: getattr(row, name) for name in RESOURCE_FIELDS},
            )
        if row.tags.get(CREATED):
            row.delete()
        else:
            row.tags = {k: v for k, v in row.tags.items() if k != MARK}
            row.save(update_fields=["tags"])

    if restored:
        # Rows were inserted with explicit ids: move the id sequence past them.
        from django.core.management.color import no_style

        connection = schema_editor.connection
        with connection.cursor() as cursor:
            for sql in connection.ops.sequence_reset_sql(no_style(), [Spend]):
                cursor.execute(sql)


class Migration(migrations.Migration):
    dependencies = [
        ("console_app", "0008_workloadsession_spend_fields"),
        ("spend_app", "0001_initial"),
        ("project_app", "0043_app_store_copy"),
    ]

    operations = [
        migrations.RunPython(copy_spend_rows, restore_spend_rows),
    ]
