"""
Management command to clean up unverified users (email verification expired).

This helps free up email slots for users who:
- Registered but never verified their email
- Have expired verification codes

Usage:
    python manage.py cleanup_unverified_users
    python manage.py cleanup_unverified_users --hours=24
    python manage.py cleanup_unverified_users --dry-run
    python manage.py cleanup_unverified_users --email=user@example.com
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta


class Command(BaseCommand):
    help = "Clean up inactive users with expired email verification"

    def add_arguments(self, parser):
        parser.add_argument(
            "--hours",
            type=int,
            default=1,
            help="Delete unverified users older than this many hours (default: 1)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be deleted without actually deleting",
        )
        parser.add_argument(
            "--email",
            type=str,
            help="Delete a specific unverified user by email address",
        )

    def handle(self, *args, **options):
        hours = options["hours"]
        dry_run = options["dry_run"]
        specific_email = options.get("email")

        if dry_run:
            self.stdout.write(
                self.style.WARNING("DRY RUN MODE - No actual deletions will occur")
            )

        # Handle specific email deletion
        if specific_email:
            self._delete_specific_user(specific_email, dry_run)
            return

        # General cleanup
        cutoff_date = timezone.now() - timedelta(hours=hours)

        self.stdout.write(
            self.style.SUCCESS(
                f"Cleaning up unverified users older than {hours} hours (before {cutoff_date})"
            )
        )

        # Find inactive users (excluding visitors) who joined before cutoff
        # These users registered but never verified their email
        unverified_users = (
            User.objects.filter(
                is_active=False,
                date_joined__lt=cutoff_date,
            )
            .exclude(username__startswith="visitor-")
            .exclude(username__startswith="guest-")
        )

        total_users = unverified_users.count()
        self.stdout.write(f"Found {total_users} unverified users to clean up")

        deleted_count = 0
        error_count = 0

        for user in unverified_users:
            try:
                self._process_user(user, dry_run)
                if not dry_run:
                    deleted_count += 1
            except Exception as e:
                error_count += 1
                self.stdout.write(
                    self.style.ERROR(f"  Error processing {user.username}: {e}")
                )

        # Summary
        self.stdout.write("\n" + "=" * 50)
        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN COMPLETE"))
            self.stdout.write(f"Would delete {total_users} unverified users")
        else:
            self.stdout.write(self.style.SUCCESS("CLEANUP COMPLETE"))
            self.stdout.write(f"Successfully deleted: {deleted_count} unverified users")
            if error_count > 0:
                self.stdout.write(
                    self.style.ERROR(f"Errors encountered: {error_count}")
                )

    def _delete_specific_user(self, email, dry_run):
        """Delete a specific unverified user by email."""
        user = User.objects.filter(email=email, is_active=False).first()

        if not user:
            self.stdout.write(
                self.style.ERROR(f"No inactive user found with email: {email}")
            )
            return

        try:
            self._process_user(user, dry_run)
            self.stdout.write(
                self.style.SUCCESS(f"Successfully processed user with email: {email}")
            )
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error processing user {email}: {e}"))

    def _process_user(self, user, dry_run):
        """Process a single user for deletion."""
        from apps.infra.auth_app.models import EmailVerification

        # Check verification status
        verifications = EmailVerification.objects.filter(user=user)
        verified = verifications.filter(is_verified=True).exists()

        self.stdout.write(f"\nProcessing: {user.username}")
        self.stdout.write(f"  - Email: {user.email}")
        self.stdout.write(f"  - Joined: {user.date_joined}")
        self.stdout.write(f"  - Active: {user.is_active}")
        self.stdout.write(f"  - Verified: {verified}")

        if verified:
            self.stdout.write(
                self.style.WARNING(
                    f"  SKIPPED: User has verified email but is_active=False (manual review needed)"
                )
            )
            return

        if not dry_run:
            user.delete()
            self.stdout.write(
                self.style.SUCCESS(f"  Deleted: {user.username} ({user.email})")
            )
        else:
            self.stdout.write(
                self.style.WARNING(f"  [DRY RUN] Would delete: {user.username}")
            )
