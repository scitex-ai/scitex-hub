"""Rename module_name='marketplace' to 'apps' in AppsModule.

The workspace registry was renamed from marketplace to apps, but the
DB record's module_name field was not updated.
"""

from django.db import migrations


def rename_marketplace_to_apps(apps, schema_editor):
    AppsModule = apps.get_model("apps_app", "MarketplaceModule")
    AppsModule.objects.filter(module_name="marketplace").update(module_name="apps")


def rename_apps_to_marketplace(apps, schema_editor):
    AppsModule = apps.get_model("apps_app", "MarketplaceModule")
    AppsModule.objects.filter(module_name="apps").update(module_name="marketplace")


class Migration(migrations.Migration):
    dependencies = [
        ("apps_app", "0007_fix_remaining_table_names"),
    ]

    operations = [
        migrations.RunPython(rename_marketplace_to_apps, rename_apps_to_marketplace),
    ]
