"""Delete the stale pre-rebrand "todo" catalog row (Cards duplicate tile).

Root cause (prod DB, 2026-09-27): two public AppsModule rows describe the
same board — ("todo", "Cards", "fas fa-list-check") [stale legacy] and
("scitex-cards", "Cards", "fas fa-diagram-project") [plugin]. The launcher's
step 2 re-adds every public row the registry does not know, so the stale
"todo" row rendered a second Work tile next to the plugin one.

Code audit found nothing depending on module_name "todo": the only live
reference is the hub-owned /apps/todo/ -> /apps/cards/ legacy redirect
(config/urls.py, pinned by tests/config/test_todo_mount.py), which this
migration does not touch. The remaining hits are unrelated substrings
("TODO" comments, a "todo" stub-marker, a forbidden-word test).

Mirrors 0022's remove_retired_apps: delete the catalog row (dependent
installation state cascades) and strip the retired id from per-user
launcher configs so no dangling dock/order entry survives.
"""

from django.db import migrations

_RETIRED = {"todo"}


def remove_stale_todo_module(apps, schema_editor):
    """Delete the stale "todo" row and scrub it from user launcher configs."""
    AppsModule = apps.get_model("apps_app", "AppsModule")
    ModuleInstallation = apps.get_model("apps_app", "ModuleInstallation")
    PlannedAppInterest = apps.get_model("apps_app", "PlannedAppInterest")

    AppsModule.objects.filter(module_name__in=_RETIRED).delete()
    PlannedAppInterest.objects.filter(app_id__in=_RETIRED).delete()

    for installation in ModuleInstallation.objects.all().iterator():
        config = installation.config
        if not isinstance(config, dict):
            continue
        updated = dict(config)
        dock = updated.get("launcher_dock")
        if isinstance(dock, list):
            updated["launcher_dock"] = [name for name in dock if name not in _RETIRED]
        order = updated.get("launcher_link_order")
        if isinstance(order, dict):
            updated["launcher_link_order"] = {
                name: value for name, value in order.items() if name not in _RETIRED
            }
        if updated != config:
            installation.config = updated
            installation.save(update_fields=["config"])


class Migration(migrations.Migration):
    dependencies = [("apps_app", "0022_canonical_project_module_names")]
    operations = [
        migrations.RunPython(remove_stale_todo_module, migrations.RunPython.noop),
    ]
