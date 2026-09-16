"""Move persisted project app identities to their canonical module names."""

from django.db import migrations


RENAMES = {
    "home": "my_projects",
    "discovery": "public_projects",
}


def rename_project_modules(apps, schema_editor):
    """Rename rows in place so every foreign-key relationship is retained."""
    AppsModule = apps.get_model("apps_app", "AppsModule")
    ModuleInstallation = apps.get_model("apps_app", "ModuleInstallation")
    for old_name, new_name in RENAMES.items():
        if AppsModule.objects.filter(module_name=old_name).exists() and AppsModule.objects.filter(
            module_name=new_name
        ).exists():
            raise RuntimeError(
                f"Cannot rename {old_name!r} to {new_name!r}: both module identities exist"
            )
        AppsModule.objects.filter(module_name=old_name).update(module_name=new_name)

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
