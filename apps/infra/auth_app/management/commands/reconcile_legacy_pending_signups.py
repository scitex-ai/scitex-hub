#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EXPLICIT reconciliation: grant a PendingSignup marker to named user IDs.

This is the ONLY way a pre-existing account may acquire signup authority, and it
takes EXPLICIT ids because the evidence is NOT self-authenticating: an abandoned
signup and an admin-disabled never-signed-in account with an old matching row are
indistinguishable from the data. An operator decides; this command applies the
decision and RECORDS it.

Per ID, inside one transaction and with the user row LOCKED:
  * recheck the evidence predicate against the LOCKED row (a snapshot outside the
    lock is exactly the stale-read mistake this PR has already been corrected for
    twice) — an ID that fails the recheck is REFUSED, not silently skipped;
  * refuse an id that already has a marker (nothing to do; reported);
  * create the marker with reconciled_at + reconciled_by provenance.

Usage:
    python manage.py reconcile_legacy_pending_signups --user-id 42
    python manage.py reconcile_legacy_pending_signups --user-id 42 --user-id 43
    python manage.py reconcile_legacy_pending_signups --user-id 42 --dry-run
"""

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.infra.auth_app import pending_signup as ps
from apps.infra.auth_app.models import PendingSignup


class Command(BaseCommand):
    help = (
        "Reconcile EXPLICIT user IDs into PendingSignup markers, rechecking the "
        "evidence under a row lock and recording provenance."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--user-id",
            dest="user_ids",
            type=int,
            action="append",
            default=[],
            help="User ID to reconcile. Repeatable. At least one is required.",
        )
        parser.add_argument(
            "--reconciled-by",
            default="operator",
            help="Who is making this decision; recorded on every marker.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Recheck and report without writing anything.",
        )

    def handle(self, *args, **options):
        user_ids = options["user_ids"]
        if not user_ids:
            # No default target, ever. A command that guesses is the auto-backfill
            # this replaced.
            raise CommandError(
                "at least one --user-id is required. There is deliberately no "
                "default: choosing which legacy accounts become signups is an "
                "operator decision, not a heuristic. Run "
                "`audit_legacy_pending_signups` to see the candidates."
            )

        reconciled, refused, already = [], [], []
        for user_id in user_ids:
            outcome = self._reconcile_one(
                user_id, options["reconciled_by"], options["dry_run"]
            )
            {"reconciled": reconciled, "refused": refused, "already": already}[
                outcome[0]
            ].append(outcome[1])

        self.stdout.write("\n" + "=" * 60)
        for label, rows in (
            ("RECONCILED", reconciled),
            ("ALREADY HAD A MARKER", already),
            ("REFUSED", refused),
        ):
            if rows:
                self.stdout.write(f"{label}: {rows}")

        if refused:
            # Nonzero: a refusal means the operator's selection did not match the
            # evidence, and automation must not treat that as success.
            raise CommandError(
                f"{len(refused)} id(s) refused: {refused}. Nothing was written "
                "for those ids."
            )
        if options["dry_run"]:
            self.stdout.write(self.style.WARNING("DRY RUN — nothing was written."))
        else:
            self.stdout.write(
                self.style.SUCCESS(f"Reconciled {len(reconciled)} id(s).")
            )

    def _reconcile_one(self, user_id: int, reconciled_by: str, dry_run: bool):
        with transaction.atomic():
            user = User.objects.select_for_update().filter(pk=user_id).first()
            if user is None:
                return ("refused", f"{user_id}: no such user")

            if PendingSignup.objects.filter(user_id=user_id).exists():
                return ("already", f"{user_id}: marker already exists")

            # RECHECK under the lock, against THE LOCKED ROW.
            candidate_ids = set(
                ps.legacy_pending_candidates().values_list("pk", flat=True)
            )
            if user_id not in candidate_ids:
                self.stdout.write(
                    f"  {user_id} ({user.username}) FAILS the evidence recheck: "
                    + "; ".join(ps.legacy_evidence(user))
                )
                return ("refused", f"{user_id}: fails the strict evidence recheck")

            if dry_run:
                return ("reconciled", f"{user_id} ({user.username}) [dry-run]")

            PendingSignup.objects.create(
                user_id=user_id,
                email=user.email,
                reconciled_at=timezone.now(),
                reconciled_by=reconciled_by,
            )
            self.stdout.write(f"  reconciled {user_id} ({user.username})")
            return ("reconciled", f"{user_id} ({user.username})")
