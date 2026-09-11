#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Report case-insensitive identity collisions. READS ONLY, WRITES NOTHING.

This is the PREFLIGHT for migration 0009_identity_case_insensitive_uniqueness.
That migration creates functional UNIQUE indexes on lower(username) and
lower(email), and it FAILS LOUD if any current row collides — deliberately, so
that a skipped index can never be mistaken for a guarded database.

Run this first, reconcile by hand, then migrate.

WHY RECONCILIATION IS NOT AUTOMATED
Two accounts differing only in case are either two real people or one duplicated
person, and nothing in the data can tell you which. Merging accounts is
destructive and judgement-bearing; it must not be something a migration does to
production unattended. So this command reports and stops.

Usage:
    python manage.py audit_identity_duplicates
    python manage.py audit_identity_duplicates --include-blank-email
"""

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.db.models.functions import Lower


class Command(BaseCommand):
    help = (
        "PREFLIGHT (read-only): list case-insensitive username/email collisions "
        "that would block migration 0009. Writes nothing."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--include-blank-email",
            action="store_true",
            help=(
                "Also list users sharing a BLANK email. The unique index "
                "excludes blank on purpose (it is the absence of an address), so "
                "these are NOT migration blockers — reported only if asked for."
            ),
        )

    def handle(self, *args, **options):
        blockers = 0

        self.stdout.write("\n=== usernames colliding case-insensitively ===")
        blockers += self._report(User.objects.annotate(low=Lower("username")), "low")

        self.stdout.write("\n=== non-blank emails colliding case-insensitively ===")
        blockers += self._report(
            User.objects.exclude(email="").annotate(low=Lower("email")), "low"
        )

        if options["include_blank_email"]:
            self.stdout.write("\n=== users sharing a BLANK email (not a blocker) ===")
            blank = User.objects.filter(email="").count()
            self.stdout.write(f"  {blank} user(s) have no email address")

        self.stdout.write("\n" + "=" * 60)
        if blockers:
            self.stdout.write(
                self.style.ERROR(
                    f"NOT READY: {blockers} colliding value(s). Migration 0009 "
                    "WILL FAIL until these are reconciled by hand. Nothing was "
                    "changed by this command."
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    "READY: no collisions. Migration 0009 can create its unique "
                    "indexes."
                )
            )

    def _report(self, queryset, key_field: str) -> int:
        """Print every group of rows sharing a normalized value."""
        from django.db.models import Count

        duplicates = (
            queryset.values(key_field)
            .annotate(total=Count("id"))
            .filter(total__gt=1)
            .order_by("-total")
        )
        found = 0
        for group in duplicates:
            users = queryset.filter(**{key_field: group[key_field]}).order_by(
                "date_joined"
            )
            found += 1
            self.stdout.write(
                self.style.WARNING(
                    f"  {group[key_field]!r} — {group['total']} accounts:"
                )
            )
            for user in users:
                self.stdout.write(
                    f"    id={user.pk} username={user.username!r} "
                    f"email={user.email!r} "
                    f"is_active={user.is_active} "
                    f"joined={user.date_joined:%Y-%m-%d %H:%M}"
                )
        if not found:
            self.stdout.write("  none")
        return found
