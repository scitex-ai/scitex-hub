"""Pin table names after marketplace_app -> apps_app rename.

The actual DB tables have apps_app_ prefix (Django's default for the new
app_label). We use SeparateDatabaseAndState to explicitly tell Django the
correct table names so subsequent migrations generate valid SQL.
"""

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("apps_app", "0005_add_pinned_commit_fields"),
    ]

    operations = [
        # Pin all model table names to their actual apps_app_ tables
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AlterModelTable(
                    name="marketplacemodule",
                    table="apps_app_marketplacemodule",
                ),
                migrations.AlterModelTable(
                    name="moduleversion",
                    table="apps_app_moduleversion",
                ),
                migrations.AlterModelTable(
                    name="moduleinstallation",
                    table="apps_app_moduleinstallation",
                ),
                migrations.AlterModelTable(
                    name="modulestar",
                    table="apps_app_modulestar",
                ),
                migrations.AlterModelTable(
                    name="modulesubmission",
                    table="apps_app_modulesubmission",
                ),
                migrations.AlterModelTable(
                    name="modulereview",
                    table="apps_app_modulereview",
                ),
            ],
            database_operations=[],
        ),
    ]
