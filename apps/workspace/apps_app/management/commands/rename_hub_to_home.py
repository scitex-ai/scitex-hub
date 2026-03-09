"""Rename hub -> home in AppsModule DB records."""

from django.core.management.base import BaseCommand

from apps.workspace.apps_app.models import AppsModule


class Command(BaseCommand):
    help = "Rename hub module to home in the apps catalog"

    def handle(self, *args, **options):
        home_exists = AppsModule.objects.filter(module_name="home").exists()
        if home_exists:
            # "home" already exists — just remove the stale "hub" duplicate
            deleted, _ = AppsModule.objects.filter(module_name="hub").delete()
            self.stdout.write(
                f"Deleted {deleted} stale 'hub' record(s) ('home' already exists)"
            )
        else:
            updated = AppsModule.objects.filter(module_name="hub").update(
                module_name="home"
            )
            self.stdout.write(f"Renamed {updated} 'hub' record(s) to 'home'")
        self.stdout.write(self.style.SUCCESS("Done."))
