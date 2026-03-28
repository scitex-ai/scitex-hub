"""Confirm table names after marketplace_app -> apps_app rename.

Migration 0006 already pins all models to apps_app_ tables.
This migration is now a no-op but kept for migration graph integrity.
"""

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("apps_app", "0006_rename_marketplacemodule_to_appsmodule"),
    ]

    operations = [
        # No-op: 0006 already sets correct apps_app_ table names for all models.
        # Previously this incorrectly set marketplace_app_ prefixes.
    ]
