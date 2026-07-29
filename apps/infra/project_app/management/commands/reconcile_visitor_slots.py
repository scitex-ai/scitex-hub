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

``--async`` (used by the container entrypoints) keeps Phase 1
(quarantine — cheap, DB-only) synchronous but DISPATCHES Phase 2 (the
per-slot wipe+clone+verify, ~10s each) to the existing
``reset_visitor_slot`` Celery task instead of running it inline. This
takes the multi-minute re-clean OFF the web-serving startup path so
Django serves immediately after boot. The fail-safe is unchanged: every
slot is quarantined synchronously first, so NOTHING is allocatable until
a worker verifies it clean — visitors get the readonly-visitor fallback
during the async window (same gate as a Celery outage).

Usage:
    python manage.py reconcile_visitor_slots                    # full: quarantine + re-clean (inline)
    python manage.py reconcile_visitor_slots --async            # quarantine now, enqueue re-clean to Celery
    python manage.py reconcile_visitor_slots --quarantine-only  # mark only, no re-clean
    python manage.py reconcile_visitor_slots --visitor 2        # single slot
"""

from django.core.management.base import BaseCommand, CommandError

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
    # Kwarg-only test seam (never a CLI flag): lets tests inject a tiny real
    # recording function for the Phase-2 dispatch instead of fighting
    # Celery's process-global task_always_eager flag. Must be declared here
    # or Django's call_command() rejects it with
    # "Unknown option(s) for reconcile_visitor_slots command: enqueue_fn".
    stealth_options = ("enqueue_fn",)

    def add_arguments(self, parser):
        parser.add_argument(
            "--quarantine-only",
            action="store_true",
            help="Only move unverified slots to quarantine; skip the re-clean",
        )
        parser.add_argument(
            "--async",
            dest="async_dispatch",
            action="store_true",
            help=(
                "Quarantine synchronously (fast, DB-only) then ENQUEUE the "
                "per-slot wipe+verify re-clean to Celery instead of running it "
                "inline. Used by the container entrypoint so Django serves "
                "immediately; slots stay quarantined (not allocatable) until a "
                "worker verifies each clean."
            ),
        )
        parser.add_argument(
            "--visitor",
            type=int,
            help="Reconcile a single visitor slot number",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help=(
                "With --visitor, wipe the slot even if it is currently "
                "ALLOCATED. Destroys that visitor's session. Only meaningful "
                "for the single-slot operator path; the full boot reconcile "
                "always wipes, because after a restart an 'allocated' slot is "
                "stale by definition."
            ),
        )

    def handle(self, *args, **options):
        pool_size = VisitorPool.POOL_SIZE
        if options["visitor"]:
            numbers = [options["visitor"]]
        else:
            numbers = list(range(1, pool_size + 1))

        # GUARD — operator single-slot path only.
        #
        # `is_active` means two different things depending on who is calling:
        #   - full boot reconcile: the process died holding this slot, so the
        #     allocation is STALE and wiping it is exactly right.
        #   - operator `--visitor N` on a RUNNING system: someone may be using
        #     it right now, and the wipe destroys their session.
        # Same field, opposite meaning, same code path.
        #
        # Incident 2026-07-30: an operator (me) read a slot table, decided two
        # slots were "stuck unverified", and ran --visitor on each. In the
        # interval the async pipeline had finished and both had been ALLOCATED.
        # The command printed "slot was allocated" into its reason string and
        # wiped them anyway. The check existed, was observed, and gated nothing
        # -- which is the same defect shape this repo keeps finding elsewhere.
        # Refusing is the fix; a reason string is not a guard.
        if options["visitor"] and not options["force"]:
            allocation = get_or_create_allocation(options["visitor"])
            if allocation.is_active:
                raise CommandError(
                    f"REFUSING to wipe visitor slot #{options['visitor']}: it is "
                    f"currently ALLOCATED (is_active=True, "
                    f"workspace_ready={allocation.workspace_ready}, "
                    f"last_activity={allocation.last_activity}). Re-cleaning it "
                    f"destroys that visitor's session.\n"
                    f"  - If the slot only LOOKS stuck, re-read it first: the "
                    f"async wipe+verify pipeline takes ~10s per slot, so a "
                    f"not-ready slot right after a deploy is usually mid-flight, "
                    f"not broken.\n"
                    f"  - If you really mean to destroy it, pass --force."
                )

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

        # Phase 2 (async) — dispatch the expensive wipe+verify to Celery so
        # the caller (the container entrypoint) returns immediately and
        # Django serves without waiting on the per-slot clone. Every slot was
        # already quarantined synchronously above, so the ready-gate fail-safe
        # is unchanged: nothing is allocatable during the async window — a
        # worker flips a slot back to distributable only after it verifies
        # clean (identical guarantee to the release path, which enqueues the
        # same task).
        if options["async_dispatch"]:
            # Real wiring: reset_visitor_slot.delay (the SAME task the
            # release pipeline already enqueues — slot_lifecycle.release_slot
            # / apps.infra.project_app.tasks.reset_visitor_slot). Tests may
            # inject a tiny real recording function here (mirroring the
            # existing gitea_client=/clone_fn= seams on reset_and_verify_slot)
            # instead of fighting Celery's process-global eager-mode flag,
            # which the SQLite/CI gate forces True and does not allow
            # overriding mid-process.
            enqueue_fn = options.get("enqueue_fn")
            if enqueue_fn is None:
                from apps.infra.project_app.tasks import reset_visitor_slot

                enqueue_fn = reset_visitor_slot.delay

            enqueued = 0
            enqueue_failed = []
            for number in numbers:
                allocation = get_or_create_allocation(number)
                if not allocation.quarantined:
                    continue
                try:
                    enqueue_fn(allocation.id)
                    enqueued += 1
                except Exception as exc:
                    # Broker unreachable at boot, etc. Safe direction: the
                    # slot simply stays quarantined (not allocatable) until a
                    # later reconcile / the periodic sweep retries. Never
                    # silently return a dirty slot to circulation.
                    enqueue_failed.append(number)
                    self.stderr.write(
                        f"Could not enqueue re-clean for visitor-{number:03d}: "
                        f"{exc} — slot stays quarantined (safe)"
                    )
            self.stdout.write(
                self.style.SUCCESS(
                    f"Enqueued {enqueued} async re-clean task(s); slots stay "
                    f"quarantined (readonly-visitor fallback) until a worker "
                    f"verifies each clean"
                )
            )
            if enqueue_failed:
                self.stdout.write(
                    self.style.ERROR(
                        f"✗ {len(enqueue_failed)} slot(s) could not be enqueued "
                        f"{enqueue_failed} — they stay quarantined until "
                        f"reconciliation retries"
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
