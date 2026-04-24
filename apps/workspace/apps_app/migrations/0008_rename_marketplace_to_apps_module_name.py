"""Rename module_name='marketplace' to 'apps' in AppsModule.

The workspace registry was renamed from marketplace to apps, but the
DB record's module_name field was not updated.
"""

from django.db import migrations


def rename_marketplace_to_apps(apps, schema_editor):
    # Use raw SQL because migration state table name (marketplace_app_marketplacemodule)
    # may not match actual DB table (apps_app_marketplacemodule) due to 0006/0007
    # SeparateDatabaseAndState mismatch. Table may also be empty — safe either way.
    with schema_editor.connection.cursor() as cursor:
        for table in ("apps_app_marketplacemodule", "marketplace_app_marketplacemodule"):
            try:
                cursor.execute(
                    f'UPDATE "{table}" SET module_name=%s WHERE module_name=%s',
                    ["apps", "marketplace"],
                )
                break
            except Exception:
                pass


def rename_apps_to_marketplace(apps, schema_editor):
    with schema_editor.connection.cursor() as cursor:
        for table in ("apps_app_marketplacemodule", "marketplace_app_marketplacemodule"):
            try:
                cursor.execute(
                    f'UPDATE "{table}" SET module_name=%s WHERE module_name=%s',
                    ["marketplace", "apps"],
                )
                break
            except Exception:
                pass


class Migration(migrations.Migration):
    dependencies = [
        ("apps_app", "0007_fix_remaining_table_names"),
    ]

    operations = [
        migrations.RunPython(rename_marketplace_to_apps, rename_apps_to_marketplace),
    ]
