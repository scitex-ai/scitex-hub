"""Rename hub -> home in AppsModule DB records."""

from django.core.management.base import BaseCommand

from apps.workspace.apps_app.models import AppsModule


class Command(BaseCommand):
    help = "Rename hub module to home in the apps catalog"

    def handle(self, *args, **options):
        updated = AppsModule.objects.filter(module_name="hub").update(
            module_name="home"
        )
        self.stdout.write(f"Renamed {updated} 'hub' record(s) to 'home'")
        deleted = AppsModule.objects.filter(module_name="hub").delete()
        self.stdout.write(f"Deleted {deleted} remaining stale 'hub' record(s)")
        self.stdout.write(self.style.SUCCESS("Done."))
