"""Fix remaining table names after marketplace_app -> apps_app rename.

Migration 0006 only fixed marketplacemodule. This fixes the other 5 models
whose actual DB tables still have marketplace_app_ prefix.
"""

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("apps_app", "0006_rename_marketplacemodule_to_appsmodule"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
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
