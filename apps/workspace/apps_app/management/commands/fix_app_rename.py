"""Fix DB records after marketplace_app -> apps_app rename."""

from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = "Update django_migrations and django_content_type for app rename"

    def handle(self, *args, **options):
        cursor = connection.cursor()
        cursor.execute(
            "UPDATE django_migrations SET app = 'apps_app' WHERE app = 'marketplace_app'"
        )
        self.stdout.write(f"Updated {cursor.rowcount} migration records")
        cursor.execute(
            "UPDATE django_content_type SET app_label = 'apps_app'"
            " WHERE app_label = 'marketplace_app'"
        )
        self.stdout.write(f"Updated {cursor.rowcount} content_type records")
        self.stdout.write(self.style.SUCCESS("Done."))
