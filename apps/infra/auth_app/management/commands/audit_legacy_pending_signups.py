#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""READ-ONLY: list legacy accounts that may be pre-marker pending signups.

This command DECIDES NOTHING and WRITES NOTHING. It exists so that the choice is
made by a person looking at evidence, instead of by a migration applying a
heuristic.

WHY THERE IS NO AUTO-BACKFILL
An inactive account with a matching unverified verification row is either an
abandoned signup OR an admin-disabled account that never signed in and happens to
carry an old row. Nothing in the data distinguishes them. Auto-marking would give
the suspended account signup authority, so the predicate is used to produce a
CANDIDATE LIST for a human, never a verdict.

Two lists are printed:
  CANDIDATES — match the evidence predicate. An operator may reconcile these
               individually with reconcile_legacy_pending_signups.
  AMBIGUOUS  — inactive and NOT a candidate: the admin-disabled and
               otherwise-undecidable shapes. Reported so they are VISIBLE rather
               than silently ignored.

Usage:
    python manage.py audit_legacy_pending_signups
    python manage.py audit_legacy_pending_signups --limit 50
"""

from django.core.management.base import BaseCommand

from apps.infra.auth_app import pending_signup as ps


class Command(BaseCommand):
    help = (
        "READ-ONLY: list candidate and ambiguous legacy accounts for manual "
        "PendingSignup reconciliation. Writes nothing."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--limit",
            type=int,
            default=200,
            help="Maximum rows to print per list (default: 200).",
        )

    def handle(self, *args, **options):
        limit = options["limit"]

        candidates = list(ps.legacy_pending_candidates()[:limit])
        self.stdout.write(
            f"\n=== CANDIDATES ({len(candidates)} shown) — may be reconciled "
            f"individually, NOT automatically ==="
        )
        if not candidates:
            self.stdout.write("  none")
        for user in candidates:
            self.stdout.write(f"\n  user id={user.pk} username={user.username!r}")
            for line in ps.legacy_evidence(user):
                self.stdout.write(f"      {line}")

        ambiguous = list(ps.legacy_ambiguous_inactive()[:limit])
        self.stdout.write(
            f"\n=== AMBIGUOUS ({len(ambiguous)} shown) — reported, NEVER "
            f"reconciled automatically ==="
        )
        if not ambiguous:
            self.stdout.write("  none")
        for user in ambiguous:
            self.stdout.write(
                f"\n  user id={user.pk} username={user.username!r} "
                f"is_active={user.is_active}"
            )
            for line in ps.legacy_evidence(user):
                self.stdout.write(f"      {line}")

        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(
            self.style.WARNING(
                "NOTHING WAS CHANGED. Reconcile explicitly, by user ID:\n"
                "  python manage.py reconcile_legacy_pending_signups "
                "--user-id <ID> [--user-id <ID> ...]"
            )
        )
