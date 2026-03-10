"""
Management command: sync_unix_users

Backfills Linux accounts and data directory ownership for all existing Django users.
Run this:
  - On container startup (root-init.sh) to provision any users that predate the UID system
  - After importing users in bulk (e.g., LDAP sync)

Usage:
    python manage.py sync_unix_users
    python manage.py sync_unix_users --dry-run
"""

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from apps.infra.accounts_app.services.unix_user import (
    enforce_data_dir_ownership,
    ensure_linux_account,
    get_unix_uid,
)


class Command(BaseCommand):
    help = "Provision Linux accounts and data-dir ownership for all Django users"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Report what would be done without making any changes",
        )

    def handle(self, *args, **options):
        User = get_user_model()
        dry_run = options["dry_run"]

        users = User.objects.select_related("auth_profile").order_by("pk")
        total = users.count()

        self.stdout.write(
            f"Syncing Unix accounts for {total} users"
            + (" [DRY RUN]" if dry_run else "")
        )

        created = 0
        ownership_fixed = 0
        errors = 0

        for user in users:
            uid = get_unix_uid(user)

            if dry_run:
                self.stdout.write(
                    f"  {user.username}: UID={uid} (would ensure account + chown data dir)"
                )
                continue

            ok_account = ensure_linux_account(user)
            if ok_account:
                created += 1

            ok_ownership = enforce_data_dir_ownership(user)
            if ok_ownership:
                ownership_fixed += 1

            if not ok_account or not ok_ownership:
                errors += 1
                self.stderr.write(
                    f"  WARN: partial failure for {user.username} "
                    f"(account={ok_account}, ownership={ok_ownership})"
                )

            # Update UserProfile.unix_uid/unix_gid if not already set
            try:
                profile = user.profile
                if profile.unix_uid != uid:
                    profile.unix_uid = uid
                    profile.unix_gid = uid
                    profile.save(update_fields=["unix_uid", "unix_gid"])
            except Exception as exc:
                self.stderr.write(
                    f"  WARN: could not update profile for {user.username}: {exc}"
                )

        if not dry_run:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Done: {created} accounts ensured, "
                    f"{ownership_fixed} data dirs owned, "
                    f"{errors} errors"
                )
            )
