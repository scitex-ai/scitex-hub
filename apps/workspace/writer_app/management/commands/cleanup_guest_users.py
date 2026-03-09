"""
Management command to clean up guest users and their data.

Usage:
    python manage.py cleanup_guest_users
    python manage.py cleanup_guest_users --days=7
    python manage.py cleanup_guest_users --dry-run
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from pathlib import Path
import shutil


class Command(BaseCommand):
    help = "Clean up guest users and their associated data older than specified days"

    def add_arguments(self, parser):
        parser.add_argument(
            "--days",
            type=int,
            default=1,
            help="Delete guest users older than this many days (default: 1)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be deleted without actually deleting",
        )

    def handle(self, *args, **options):
        days = options["days"]
        dry_run = options["dry_run"]

        cutoff_date = timezone.now() - timedelta(days=days)

        self.stdout.write(
            self.style.SUCCESS(
                f"Cleaning up guest users older than {days} days (before {cutoff_date})"
            )
        )

        if dry_run:
            self.stdout.write(
                self.style.WARNING("DRY RUN MODE - No actual deletions will occur")
            )

        # Find guest users
        guest_users = User.objects.filter(
            username__startswith="guest-", is_active=False, date_joined__lt=cutoff_date
        )

        total_users = guest_users.count()
        self.stdout.write(f"Found {total_users} guest users to clean up")

        deleted_count = 0
        error_count = 0

        for user in guest_users:
            try:
                # Get user's projects
                from apps.infra.project_app.models import Project

                projects = Project.objects.filter(owner=user)

                self.stdout.write(f"\nProcessing guest user: {user.username}")
                self.stdout.write(f"  - Joined: {user.date_joined}")
                self.stdout.write(f"  - Projects: {projects.count()}")

                # Clean up project directories
                for project in projects:
                    if project.data_location:
                        project_dir = Path(project.data_location).parent.parent
                        if project_dir.exists():
                            self.stdout.write(
                                f"  - Removing project directory: {project_dir}"
                            )
                            if not dry_run:
                                try:
                                    shutil.rmtree(project_dir)
                                except Exception as e:
                                    self.stdout.write(
                                        self.style.ERROR(
                                            f"    Error removing directory: {e}"
                                        )
                                    )

                # Delete user (cascade will delete projects and other related data)
                if not dry_run:
                    user.delete()
                    deleted_count += 1
                    self.stdout.write(
                        self.style.SUCCESS(f"  ✓ Deleted guest user: {user.username}")
                    )
                else:
                    self.stdout.write(
                        self.style.WARNING(f"  [DRY RUN] Would delete: {user.username}")
                    )

            except Exception as e:
                error_count += 1
                self.stdout.write(
                    self.style.ERROR(f"  ✗ Error processing {user.username}: {e}")
                )

        # Summary
        self.stdout.write("\n" + "=" * 50)
        if dry_run:
            self.stdout.write(self.style.WARNING(f"DRY RUN COMPLETE"))
            self.stdout.write(f"Would delete {total_users} guest users")
        else:
            self.stdout.write(self.style.SUCCESS(f"CLEANUP COMPLETE"))
            self.stdout.write(f"Successfully deleted: {deleted_count} guest users")
            if error_count > 0:
                self.stdout.write(
                    self.style.ERROR(f"Errors encountered: {error_count}")
                )
