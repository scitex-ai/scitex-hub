"""Fix table names after marketplace_app -> apps_app rename.

The actual DB tables still have marketplace_app_ prefix.
Django now expects apps_app_ prefix (because app_label changed).
We use SeparateDatabaseAndState to tell Django the table names without
actually running any ALTER TABLE.
"""

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("apps_app", "0005_add_pinned_commit_fields"),
    ]

    operations = [
        # Pin all model table names to their original marketplace_app_ tables
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AlterModelTable(
                    name="marketplacemodule",
                    table="marketplace_app_marketplacemodule",
                ),
                migrations.AlterModelTable(
                    name="moduleversion",
                    table="marketplace_app_moduleversion",
                ),
                migrations.AlterModelTable(
                    name="moduleinstallation",
                    table="marketplace_app_moduleinstallation",
                ),
                migrations.AlterModelTable(
                    name="modulestar",
                    table="marketplace_app_modulestar",
                ),
                migrations.AlterModelTable(
                    name="modulesubmission",
                    table="marketplace_app_modulesubmission",
                ),
                migrations.AlterModelTable(
                    name="modulereview",
                    table="marketplace_app_modulereview",
                ),
            ],
            database_operations=[],
        ),
    ]
