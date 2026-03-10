"""
Management command to clean up expired demo projects.

Usage:
    python manage.py cleanup_demo_projects                    # Clean up projects older than 24 hours
    python manage.py cleanup_demo_projects --hours 48         # Clean up projects older than 48 hours
    python manage.py cleanup_demo_projects --dry-run          # See what would be deleted
    python manage.py cleanup_demo_projects --orphaned-only    # Only clean up orphaned demo users
"""

from django.core.management.base import BaseCommand
from apps.infra.project_app.services.demo_project_pool import DemoProjectPool


class Command(BaseCommand):
    help = "Clean up expired demo projects and orphaned demo users"

    def add_arguments(self, parser):
        parser.add_argument(
            "--hours",
            type=int,
            default=None,
            help="Clean up projects older than this many hours (default: 24)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be deleted without actually deleting",
        )
        parser.add_argument(
            "--orphaned-only",
            action="store_true",
            help="Only clean up orphaned demo users (no project cleanup)",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        hours = options["hours"]
        orphaned_only = options["orphaned_only"]

        if dry_run:
            self.stdout.write(
                self.style.WARNING("DRY RUN MODE - No actual deletions will occur")
            )

        if orphaned_only:
            # Only clean up orphaned users
            self.stdout.write("Cleaning up orphaned demo users...")
            deleted = DemoProjectPool.cleanup_orphaned_users(dry_run=dry_run)
            self.stdout.write(
                self.style.SUCCESS(f"✓ Cleaned up {deleted} orphaned demo users")
            )
        else:
            # Clean up projects
            hours_msg = f"{hours} hours" if hours else "24 hours (default)"
            self.stdout.write(f"Cleaning up demo projects older than {hours_msg}...")

            deleted_projects = DemoProjectPool.cleanup_expired_projects(
                older_than_hours=hours, dry_run=dry_run
            )

            self.stdout.write(
                self.style.SUCCESS(
                    f"✓ Cleaned up {deleted_projects} expired demo projects"
                )
            )

            # Also clean up orphaned users
            self.stdout.write("Cleaning up orphaned demo users...")
            deleted_users = DemoProjectPool.cleanup_orphaned_users(dry_run=dry_run)
            self.stdout.write(
                self.style.SUCCESS(f"✓ Cleaned up {deleted_users} orphaned demo users")
            )

        if dry_run:
            self.stdout.write(
                self.style.WARNING("DRY RUN COMPLETE - No actual changes were made")
            )
        else:
            self.stdout.write(self.style.SUCCESS("Cleanup complete!"))
