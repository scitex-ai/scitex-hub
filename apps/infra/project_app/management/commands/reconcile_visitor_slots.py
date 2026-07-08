"""
Reconcile visitor pool slots — boot-time fail-safe + quarantine release.

Security contract (visitor-slot isolation audit 2026-07-07 + operator
directive msg 606/607): after an unclean shutdown/restart, EVERY slot
that was allocated or in an unknown/mid-reset state must be treated as
UNVERIFIED. This command quarantines all such slots, then runs the
wipe+verify pipeline on each quarantined slot; only slots that pass
return to the distributable pool. Until at least one slot verifies
clean, allocation serves only readonly-visitor (with the fail-loud
session reason flag) — that behavior is emergent from the allocation
ready-gate, not special-cased here.

Invoked by the container entrypoints right after ``create_visitor_pool``
(AppConfig.ready is discouraged for DB work). Also the operator /
automation command that releases quarantined slots after a re-clean
(``manage.py reconcile_visitor_slots``).

Usage:
    python manage.py reconcile_visitor_slots                    # full: quarantine + re-clean
    python manage.py reconcile_visitor_slots --quarantine-only  # mark only, no re-clean
    python manage.py reconcile_visitor_slots --visitor 2        # single slot
"""

from django.core.management.base import BaseCommand

from apps.infra.project_app.services.visitor_pool import VisitorPool
from apps.infra.project_app.services.visitor_pool.slot_lifecycle import (
    get_or_create_allocation,
    quarantine_slot,
    reset_and_verify_slot,
)


class Command(BaseCommand):
    help = (
        "Quarantine every visitor slot in an unverified state (boot fail-safe) "
        "and re-clean quarantined slots; only verified-clean slots return to "
        "the distributable pool"
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--quarantine-only",
            action="store_true",
            help="Only move unverified slots to quarantine; skip the re-clean",
        )
        parser.add_argument(
            "--visitor",
            type=int,
            help="Reconcile a single visitor slot number",
        )

    def handle(self, *args, **options):
        pool_size = VisitorPool.POOL_SIZE
        if options["visitor"]:
            numbers = [options["visitor"]]
        else:
            numbers = list(range(1, pool_size + 1))

        # Phase 1 — quarantine: at boot no slot's on-disk state can be
        # trusted (a reset may have been interrupted mid-wipe), so every
        # slot is treated as unverified until the pipeline proves it
        # clean.
        for number in numbers:
            allocation = get_or_create_allocation(number)
            if allocation.is_active:
                reason = "boot-reconcile: slot was allocated at shutdown"
            elif allocation.quarantined:
                reason = allocation.quarantine_reason or "boot-reconcile"
            elif not allocation.workspace_ready:
                reason = "boot-reconcile: slot was mid-reset/unverified at shutdown"
            else:
                reason = "boot-reconcile: re-verify idle slot at startup"
            quarantine_slot(allocation, reason)

        self.stdout.write(
            f"Quarantined {len(numbers)} slot(s) pending wipe+verify"
        )

        if options["quarantine_only"]:
            self.stdout.write(
                self.style.WARNING(
                    "--quarantine-only: slots stay quarantined; allocation will "
                    "serve readonly-visitor until reconcile re-clean runs"
                )
            )
            return

        # Phase 2 — re-clean: wipe + verify each quarantined slot; only
        # survivors return to the pool.
        recovered = 0
        failed = []
        for number in numbers:
            allocation = get_or_create_allocation(number)
            if not allocation.quarantined:
                continue
            if reset_and_verify_slot(allocation):
                recovered += 1
            else:
                failed.append(number)

        if recovered:
            self.stdout.write(
                self.style.SUCCESS(
                    f"✓ {recovered}/{len(numbers)} slot(s) verified clean and "
                    f"returned to the pool"
                )
            )
        if failed:
            self.stdout.write(
                self.style.ERROR(
                    f"✗ {len(failed)} slot(s) FAILED re-clean and stay "
                    f"quarantined: {failed} — see logs; visitors get "
                    f"readonly-visitor fallback while no slot is ready"
                )
            )
        if not recovered:
            self.stdout.write(
                self.style.ERROR(
                    "NO slot verified clean — pool serves readonly-visitor only "
                    "(reason=no_ready_slot) until reconciliation succeeds"
                )
            )
