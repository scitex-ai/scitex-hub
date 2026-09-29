"""Move persisted project app identities to their canonical module names."""

from django.db import migrations

RENAMES = {
    "home": "my_projects",
    "discovery": "public_projects",
}


def _merge_duplicate_module(apps, old_module, canonical_module):
    """Move historical relationships onto a pre-created canonical row.

    Registry/bootstrap code can create the canonical built-in row before this
    migration sees the legacy identity. Historical per-user state wins over a
    duplicate canonical default row; canonical catalog metadata wins over the
    legacy row.
    """
    ModuleInstallation = apps.get_model("apps_app", "ModuleInstallation")
    ModuleVersion = apps.get_model("apps_app", "ModuleVersion")
    ModuleStar = apps.get_model("apps_app", "ModuleStar")
    ModuleReview = apps.get_model("apps_app", "ModuleReview")
    ModuleSubmission = apps.get_model("apps_app", "ModuleSubmission")

    if (
        old_module.project_id
        and canonical_module.project_id
        and old_module.project_id != canonical_module.project_id
    ):
        raise RuntimeError(
            "Cannot merge project app identities backed by different projects"
        )
    if old_module.project_id and not canonical_module.project_id:
        project_id = old_module.project_id
        # project is a OneToOneField. Release the legacy row's unique value
        # before assigning it to the canonical row; the migration transaction
        # keeps the transfer atomic.
        old_module.project_id = None
        old_module.save(update_fields=["project"])
        canonical_module.project_id = project_id
        canonical_module.save(update_fields=["project"])

    for installation in ModuleInstallation.objects.filter(module=old_module):
        ModuleInstallation.objects.filter(
            module=canonical_module,
            user_id=installation.user_id,
        ).delete()
        installation.module = canonical_module
        installation.save(update_fields=["module"])

    for version in ModuleVersion.objects.filter(module=old_module):
        ModuleVersion.objects.filter(
            module=canonical_module,
            version=version.version,
        ).delete()
        version.module = canonical_module
        version.save(update_fields=["module"])

    for star in ModuleStar.objects.filter(module=old_module):
        ModuleStar.objects.filter(
            module=canonical_module,
            user_id=star.user_id,
        ).delete()
        star.module = canonical_module
        star.save(update_fields=["module"])

    for review in ModuleReview.objects.filter(module=old_module):
        ModuleReview.objects.filter(
            module=canonical_module,
            user_id=review.user_id,
        ).delete()
        review.module = canonical_module
        review.save(update_fields=["module"])

    ModuleSubmission.objects.filter(module=old_module).update(module=canonical_module)
    old_module.delete()

    ratings = list(
        ModuleReview.objects.filter(module=canonical_module).values_list(
            "rating", flat=True
        )
    )
    canonical_module.install_count = ModuleInstallation.objects.filter(
        module=canonical_module, is_enabled=True
    ).count()
    canonical_module.star_count = ModuleStar.objects.filter(
        module=canonical_module
    ).count()
    canonical_module.avg_rating = round(sum(ratings) / len(ratings), 1) if ratings else 0
    canonical_module.save(
        update_fields=["install_count", "star_count", "avg_rating"]
    )


def rename_project_modules(apps, schema_editor):
    """Rename rows in place so every foreign-key relationship is retained."""
    AppsModule = apps.get_model("apps_app", "AppsModule")
    ModuleInstallation = apps.get_model("apps_app", "ModuleInstallation")
    for old_name, new_name in RENAMES.items():
        old_module = AppsModule.objects.filter(module_name=old_name).first()
        canonical_module = AppsModule.objects.filter(module_name=new_name).first()
        if old_module and canonical_module:
            _merge_duplicate_module(apps, old_module, canonical_module)
        elif old_module:
            old_module.module_name = new_name
            old_module.save(update_fields=["module_name"])

    for installation in ModuleInstallation.objects.all().iterator():
        config = installation.config
        if not isinstance(config, dict):
            continue
        updated = dict(config)
        dock = updated.get("launcher_dock")
        if isinstance(dock, list):
            updated["launcher_dock"] = [
                RENAMES.get(name, name)
                for name in dock
                if name not in {"slides", "mail", "screen-recorder"}
            ]
        order = updated.get("launcher_link_order")
        if isinstance(order, dict):
            updated["launcher_link_order"] = {
                RENAMES.get(name, name): value
                for name, value in order.items()
                if name not in {"slides", "mail", "screen-recorder"}
            }
        if updated != config:
            installation.config = updated
            installation.save(update_fields=["config"])


def remove_retired_apps(apps, schema_editor):
    """Delete retired catalog rows and their dependent installation state."""
    AppsModule = apps.get_model("apps_app", "AppsModule")
    PlannedAppInterest = apps.get_model("apps_app", "PlannedAppInterest")
    AppsModule.objects.filter(module_name="slides").delete()
    PlannedAppInterest.objects.filter(
        app_id__in=("slides", "mail", "screen-recorder")
    ).delete()


class Migration(migrations.Migration):
    dependencies = [("apps_app", "0021_plannedappinterest")]
    operations = [
        migrations.RunPython(rename_project_modules, migrations.RunPython.noop),
        migrations.RunPython(remove_retired_apps, migrations.RunPython.noop),
    ]
