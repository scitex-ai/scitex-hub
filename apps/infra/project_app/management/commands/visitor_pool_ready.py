"""
Assert the visitor pool has distributable slots — the deploy's post-condition.

WHY THIS EXISTS (incident 2026-08-16, measured on the prod host).
Every deploy quarantines all 16 visitor slots. That is the boot fail-safe in
``entrypoint-prod.sh`` (``reconcile_visitor_slots --async``) and it is
CORRECT: after a restart no slot's on-disk state can be trusted. Slots come
back only as ``celery_worker_vis`` verifies each one clean.

On that day they never came back, and NOTHING WENT RED. The image was built
22:06:16 JST, ``scitex-hub-prod-django-1`` was recreated 22:08:34 JST, and for
~1h35m every anonymous visitor was funnelled onto the single shared
``readonly-visitor`` account — while containers were healthy, the deploy
reported success, and ``/api/server-health/`` reported "healthy". The repair
was a command that existed only inside a card comment addressed to whoever
deployed next; the agent holding that intention died mid-deploy and the rule
died with it (constitution §7).

This command is the missing ASSERTION. ``reconcile_visitor_slots --async``
only DISPATCHES the re-clean; every message it prints says "dispatched", and
until now nothing anywhere asked the follow-up question "did any slot actually
come back?". A deploy that declares success on dispatch rather than on outcome
is exactly the §2 failure: a declaration that cannot be honoured evaporating
instead of failing.

READ-ONLY BY CONSTRUCTION. It performs only ``VisitorPool.get_pool_status()``
ORM reads. It never quarantines and never wipes, so it is safe to run against
a LIVE pool — unlike ``reconcile_visitor_slots``, whose Phase 1 quarantines
EVERY slot including healthy ones ("boot-reconcile: re-verify idle slot at
startup"), dropping ``ready`` to 0 until each re-clean succeeds. That command
is a boot fail-safe, not a probe; running it to "check" the pool breaks it.

It reports ``ready``, never ``free``. ``free`` is merely total-minus-occupied
and counts slots that can never be handed out; a UI that showed ``free``
claimed spare capacity while every visitor was correctly downgraded to
read-only (prod 2026-07-30). See ``PoolAllocator.get_pool_status``' docstring.

Usage:
    python manage.py visitor_pool_ready                       # assert now
    python manage.py visitor_pool_ready --wait 600            # poll for 10 min
    python manage.py visitor_pool_ready --min-ready 4         # demand headroom
"""

import time

from django.core.management.base import BaseCommand, CommandError

from apps.infra.project_app.services.visitor_pool import VisitorPool

# Named so the failure message, the deploy gate and the tests all quote the
# SAME repair. A gate that reports a symptom without naming its fix hands the
# next operator the identical archaeology this incident already cost.
REPAIR_COMMAND = "python manage.py reconcile_visitor_slots --repair-only"


class Command(BaseCommand):
    help = (
        "Exit non-zero unless at least --min-ready visitor slots are "
        "distributable. Read-only; safe on a live pool."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--min-ready",
            type=int,
            default=1,
            help=(
                "Minimum number of DISTRIBUTABLE slots required to pass "
                "(default 1). 'ready', not 'free' — see the module docstring."
            ),
        )
        parser.add_argument(
            "--wait",
            type=int,
            default=0,
            help=(
                "Seconds to keep polling before failing. The async wipe+verify "
                "is ~10s per slot, so a deploy gate must allow for a merely-slow "
                "pool rather than failing one that is still mid-flight."
            ),
        )
        parser.add_argument(
            "--interval",
            type=float,
            default=10.0,
            help="Seconds between polls while --wait has not elapsed (default 10).",
        )

    def handle(self, *args, **options):
        min_ready = options["min_ready"]
        deadline = time.monotonic() + options["wait"]

        status = VisitorPool.get_pool_status()
        while True:
            if status["ready"] >= min_ready:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"OK: {status['ready']}/{status['total']} visitor slot(s) "
                        f"distributable (quarantined={status['quarantined']}, "
                        f"allocated={status['allocated']})"
                    )
                )
                return
            if time.monotonic() >= deadline:
                break
            self.stdout.write(
                f"   waiting: ready={status['ready']}/{min_ready} required "
                f"(quarantined={status['quarantined']}) — re-clean is ~10s/slot"
            )
            time.sleep(options["interval"])
            status = VisitorPool.get_pool_status()

        # CommandError exits 1, which is what makes this usable as a gate.
        raise CommandError(
            f"VISITOR POOL NOT READY: ready={status['ready']} "
            f"(need {min_ready}), quarantined={status['quarantined']}, "
            f"allocated={status['allocated']}, of {status['total']} slot(s).\n"
            f"  -> EVERY anonymous visitor is being served the shared "
            f"readonly-visitor account (reason=no_ready_slot).\n"
            f"  -> Repair: {REPAIR_COMMAND}\n"
            f"  -> Do NOT run plain `reconcile_visitor_slots` against a live "
            f"pool: its Phase 1 quarantines every slot, healthy ones included."
        )
