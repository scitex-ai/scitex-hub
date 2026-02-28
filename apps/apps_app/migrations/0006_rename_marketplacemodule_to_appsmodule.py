"""Rename MarketplaceModule to AppsModule (preserves existing DB table)."""

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("apps_app", "0005_add_pinned_commit_fields"),
    ]

    operations = [
        migrations.RenameModel(
            old_name="MarketplaceModule",
            new_name="AppsModule",
        ),
    ]
