# Rename app_label from modulemaker_app to appmaker_app.
#
# Phase 1 renamed the directory; this migration fixes Django's internal tracking tables.
# The django_migrations table must ALSO be updated before this migration runs.
# Run this SQL first (one-time, idempotent):
#
#   UPDATE django_migrations
#   SET app = 'appmaker_app'
#   WHERE app = 'modulemaker_app';
#

from django.db import migrations


def update_content_types(apps, schema_editor):
    """Update django_content_type rows from old to new app_label."""
    ContentType = apps.get_model("contenttypes", "ContentType")
    ContentType.objects.filter(app_label="modulemaker_app").update(
        app_label="appmaker_app"
    )


def revert_content_types(apps, schema_editor):
    """Revert django_content_type rows."""
    ContentType = apps.get_model("contenttypes", "ContentType")
    ContentType.objects.filter(app_label="appmaker_app").update(
        app_label="modulemaker_app"
    )


class Migration(migrations.Migration):

    dependencies = [
        ("appmaker_app", "0002_add_source_repo_fields"),
        ("contenttypes", "0002_remove_content_type_name"),
    ]

    operations = [
        migrations.RunPython(update_content_types, revert_content_types),
        # Freeze db_table so Django doesn't try to rename the actual tables
        migrations.AlterModelOptions(
            name="usermodule",
            options={
                "ordering": ["-updated_at"],
                "verbose_name": "User App",
            },
        ),
        migrations.AlterModelTable(
            name="usermodule",
            table="modulemaker_app_usermodule",
        ),
        migrations.AlterModelOptions(
            name="moduleexecution",
            options={
                "ordering": ["-started_at"],
                "verbose_name": "App Execution",
            },
        ),
        migrations.AlterModelTable(
            name="moduleexecution",
            table="modulemaker_app_moduleexecution",
        ),
    ]
