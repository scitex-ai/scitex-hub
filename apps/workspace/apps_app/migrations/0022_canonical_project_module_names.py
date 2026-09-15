"""Move persisted project app identities to their canonical module names."""

from django.db import migrations


RENAMES = {
    "home": "my_projects",
    "discovery": "public_projects",
}


def rename_project_modules(apps, schema_editor):
    """Rename rows in place so every foreign-key relationship is retained."""
    AppsModule = apps.get_model("apps_app", "AppsModule")
    for old_name, new_name in RENAMES.items():
        AppsModule.objects.filter(module_name=old_name).update(module_name=new_name)


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
