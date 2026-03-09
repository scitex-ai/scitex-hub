"""Rename MarketplaceModule to AppsModule (state only) and widen submission status field.

The actual DB table is marketplace_app_marketplacemodule (pinned in 0006).
We only need to update Django's internal state so the model name matches the code.
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("apps_app", "0008_rename_marketplace_to_apps_module_name"),
    ]

    operations = [
        # 1. Rename MarketplaceModule -> AppsModule in Django state only
        #    (the actual DB table stays marketplace_app_marketplacemodule)
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.RenameModel(
                    old_name="MarketplaceModule",
                    new_name="AppsModule",
                ),
            ],
            database_operations=[],
        ),
        # 2. Update verbose_name and ordering to match current model Meta
        migrations.AlterModelOptions(
            name="appsmodule",
            options={
                "verbose_name": "App",
                "ordering": ["-star_count", "-install_count"],
            },
        ),
        # 3. Widen status field on ModuleSubmission to support "changes_requested"
        migrations.AlterField(
            model_name="modulesubmission",
            name="status",
            field=models.CharField(
                choices=[
                    ("pending", "Pending Review"),
                    ("approved", "Approved"),
                    ("rejected", "Rejected"),
                    ("changes_requested", "Changes Requested"),
                ],
                default="pending",
                max_length=20,
            ),
        ),
    ]
