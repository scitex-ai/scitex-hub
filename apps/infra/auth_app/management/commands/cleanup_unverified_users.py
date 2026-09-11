"""Management command to clean up unverified users (email verification expired).

This helps free up email slots for users who:
- Registered but never verified their email
- Have expired verification codes

NOTE (hub auth lifecycle P0): the SIGNUP REQUEST PATH NO LONGER DEPENDS ON THIS
COMMAND. Expiry and resume are decided in ``auth_app.pending_signup`` when a
signup is submitted, so a pending signup is resumable whether or not any sweep
has ever run — the pending window used to live only here as an unscheduled
manual command, which made "wait 1 hour for the account to expire" advice that
nothing performed. This command remains useful for reclaiming abandoned
addresses and for the audit below.

Usage:
    python manage.py cleanup_unverified_users
    python manage.py cleanup_unverified_users --hours=24
    python manage.py cleanup_unverified_users --dry-run
    python manage.py cleanup_unverified_users --email=user@example.com
"""

from datetime import timedelta

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.infra.auth_app.pending_signup import PENDING_SIGNUP_WINDOW


class Command(BaseCommand):
    help = "Clean up inactive users with expired email verification"

    def add_arguments(self, parser):
        parser.add_argument(
            "--hours",
            type=int,
            default=int(PENDING_SIGNUP_WINDOW.total_seconds() // 3600),
            help=(
                "Delete unverified users older than this many hours "
                f"(default: {int(PENDING_SIGNUP_WINDOW.total_seconds() // 3600)}, "
                "derived from auth_app.pending_signup.PENDING_SIGNUP_WINDOW so "
                "the sweep and the request path cannot drift apart)"
            ),
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
        # PENDING-SIGNUP EVIDENCE REQUIRED (PR #775 seventh review). Deleting on
        # is_active=False ALONE destroys ADMIN-DISABLED accounts: they are
        # inactive too, and unlike a pending signup they hold data and a real
        # user. The sweep may reclaim ONLY rows carrying the typed marker.
        unverified_users = (
            User.objects.filter(
                is_active=False,
                date_joined__lt=cutoff_date,
                pending_signup__isnull=False,
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
                self._process_user(user, dry_run, cutoff_date)
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

        self._audit_active_accounts()

    def _audit_active_accounts(self):
        """Report, and NEVER mutate, ACTIVE accounts whose verification rows say
        otherwise.

        This is the invariant I1 check (``is_active=True`` IS a verified
        account) and it exists because of live evidence: an active account can
        carry a LATER, EXPIRED ``EmailVerification`` with ``is_verified=False``.
        Nothing here deletes or edits anything — an active account holds real
        data and, in the observed case, a real user. The point is to make the
        contradiction visible and attributable instead of invisible, so the
        repair is a deliberate decision rather than a sweep.
        """
        from apps.infra.auth_app.models import EmailVerification

        self.stdout.write("\n" + "=" * 50)
        self.stdout.write("AUDIT: active accounts with unverified verification rows")

        active_with_stale = (
            User.objects.filter(is_active=True)
            .filter(auth_email_verifications__is_verified=False)
            .distinct()
        )
        count = active_with_stale.count()

        if count == 0:
            self.stdout.write(
                self.style.SUCCESS(
                    "  OK: no active account carries an unverified verification row"
                )
            )
            return

        self.stdout.write(
            self.style.WARNING(
                f"  {count} active account(s) have unverified verification rows. "
                "NOT modified by this command — review each deliberately."
            )
        )
        for user in active_with_stale[:20]:
            stale = EmailVerification.objects.filter(
                user=user, is_verified=False
            ).order_by("-created_at")
            latest = stale.first()
            self.stdout.write(
                f"  - {user.username} (active since {user.date_joined:%Y-%m-%d}): "
                f"{stale.count()} unverified row(s)"
                + (f", latest {latest.created_at:%Y-%m-%d} expired" if latest else "")
            )
        if count > 20:
            self.stdout.write(f"  ... and {count - 20} more")

    def _delete_specific_user(self, email, dry_run):
        """Delete a specific unverified user by email."""
        # Marker required here too, for the same reason as the bulk sweep.
        user = User.objects.filter(
            email__iexact=email, is_active=False, pending_signup__isnull=False
        ).first()

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

    def _process_user(self, user, dry_run, cutoff_date=None):
        """Delete ONE user under a ROW LOCK, rechecking every predicate.

        THE RACE THIS CLOSES (review blocker 1). This used to READ the row, check
        verification, and then call delete() — three separate steps with no lock
        between them. A concurrent CORRECT OTP claim can activate the account in
        that window, after which the delete removes an account its owner had just
        verified. So the lock is taken FIRST, the row is re-read UNDER it, and
        EVERY deletion predicate is re-evaluated against the LOCKED row
        immediately before deletion. A predicate evaluated before the lock is a
        snapshot, and a snapshot is exactly what the race exploits.
        """
        from django.db import transaction

        from apps.infra.auth_app.models import EmailVerification, PendingSignup

        with transaction.atomic():
            locked = User.objects.select_for_update().filter(pk=user.pk).first()
            if locked is None:
                self.stdout.write(
                    f"\nSKIPPED: user {user.pk} no longer exists (already swept)"
                )
                return

            verifications = EmailVerification.objects.filter(user=locked)
            verified = verifications.filter(is_verified=True).exists()
            has_marker = PendingSignup.objects.filter(user_id=locked.pk).exists()
            past_cutoff = cutoff_date is None or locked.date_joined < cutoff_date

            self.stdout.write(f"\nProcessing: {locked.username}")
            self.stdout.write(f"  - Email: {locked.email}")
            self.stdout.write(f"  - Joined: {locked.date_joined}")
            self.stdout.write(f"  - Active: {locked.is_active}")
            self.stdout.write(f"  - Verified: {verified}")
            self.stdout.write(f"  - Has PendingSignup marker: {has_marker}")

            # EVERY predicate below is rechecked UNDER THE LOCK. Any one of them
            # means DO NOT DELETE.
            if locked.is_active:
                self.stdout.write(
                    self.style.WARNING(
                        "  SKIPPED: the account is ACTIVE — it was verified while "
                        "this sweep was running, so deleting it would destroy an "
                        "account its owner just confirmed (cleanup-vs-claim race)"
                    )
                )
                return

            if verified:
                self.stdout.write(
                    self.style.WARNING(
                        "  SKIPPED: User has verified email but is_active=False (manual review needed)"
                    )
                )
                return

            if not has_marker:
                self.stdout.write(
                    self.style.WARNING(
                        "  SKIPPED: no PendingSignup marker — this is not a signup, "
                        "so it is not this sweep's to delete"
                    )
                )
                return

            if not past_cutoff:
                self.stdout.write(
                    self.style.WARNING(
                        "  SKIPPED: no longer past the cutoff (rechecked under the lock)"
                    )
                )
                return

            if not dry_run:
                locked.delete()
                self.stdout.write(
                    self.style.SUCCESS(f"  Deleted: {locked.username} ({locked.email})")
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f"  [DRY RUN] Would delete: {locked.username}")
                )
