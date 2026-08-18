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

It reports ``allocatable``, never ``free`` and never "the workspace is clean".
``free`` is merely total-minus-occupied and counts slots that can never be
handed out; a UI that showed ``free`` claimed spare capacity while every
visitor was correctly downgraded to read-only (prod 2026-07-30). "Clean" is
looser still — on 2026-08-16 15:55Z twelve slots were clean and zero
quarantined while exactly ONE was allocatable. See ``pool_health``.

AND IT NAMES THE CAUSE. The failure text used to hardcode
``reconcile_visitor_slots --repair-only`` for every failure. That command
re-cleans only ``quarantined=True`` rows, so against a SATURATED pool it is a
no-op that reads to the operator as "I ran the documented fix and nothing
changed" — worse than naming no repair at all. The repair is now derived from
the measured cause.

Usage:
    python manage.py visitor_pool_ready                       # assert now
    python manage.py visitor_pool_ready --wait 600            # poll for 10 min
    python manage.py visitor_pool_ready --min-ready 4         # demand headroom
    python manage.py visitor_pool_ready --warn-below 4        # loud, still 0
"""

import time

from django.core.management.base import BaseCommand, CommandError

from apps.infra.project_app.services.visitor_pool import VisitorPool
from apps.infra.project_app.services.visitor_pool.pool_health import (
    CAUSE_QUARANTINED,
    REPAIR_BY_CAUSE,
    WARN_BELOW_ALLOCATABLE,
    capacity_cause,
    describe_partition,
    partition_pool_status,
)

# Named so the failure message, the deploy gate and the tests all quote the
# SAME repair. A gate that reports a symptom without naming its fix hands the
# next operator the identical archaeology this incident already cost. This is
# the QUARANTINE repair specifically — see ``REPAIR_BY_CAUSE`` for the others.
REPAIR_COMMAND = REPAIR_BY_CAUSE[CAUSE_QUARANTINED]


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
                "Minimum number of ALLOCATABLE slots required to pass "
                "(default 1). Not 'free', not 'clean' — see the module "
                "docstring. Kept at 1 as the FAIL threshold on purpose: a "
                "deploy that lands one slot is not a failed deploy. Thin "
                "headroom is reported by --warn-below instead."
            ),
        )
        parser.add_argument(
            "--warn-below",
            type=int,
            default=WARN_BELOW_ALLOCATABLE,
            help=(
                "Print a loud WARNING (still exit 0) when fewer than this many "
                f"slots are allocatable (default {WARN_BELOW_ALLOCATABLE}). At "
                "1 allocatable the SECOND visitor in the next half hour gets "
                "the shared readonly account, because a consumed slot does not "
                "return for tens of minutes."
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
        warn_below = options["warn_below"]
        deadline = time.monotonic() + options["wait"]

        part = partition_pool_status(VisitorPool.get_pool_status())
        while True:
            if part["allocatable"] >= min_ready:
                self._report_pass(part, warn_below)
                return
            if time.monotonic() >= deadline:
                break
            self.stdout.write(
                f"   waiting: allocatable={part['allocatable']}/{min_ready} "
                f"required — {describe_partition(part)} "
                f"— re-clean is ~10s/slot"
            )
            time.sleep(options["interval"])
            part = partition_pool_status(VisitorPool.get_pool_status())

        cause = capacity_cause(part)
        # CommandError exits 1, which is what makes this usable as a gate.
        raise CommandError(
            f"VISITOR POOL NOT READY: allocatable={part['allocatable']} "
            f"(need {min_ready}) of {part['total']} slot(s).\n"
            f"  -> {describe_partition(part)}.\n"
            f"  -> EVERY anonymous visitor is being served the shared "
            f"readonly-visitor account (reason=no_ready_slot).\n"
            f"  -> Cause: {cause}.\n"
            f"  -> Repair: {REPAIR_BY_CAUSE[cause]}\n"
            f"  -> Do NOT run plain `reconcile_visitor_slots` against a live "
            f"pool: its Phase 1 quarantines every slot, healthy ones included."
        )

    def _report_pass(self, part: dict, warn_below: int) -> None:
        """Print the passing result — loudly when the headroom is thin.

        Passing and being healthy are different questions, and the deploy gate
        must answer both. A pool with 1 of 16 allocatable passes ``--min-ready
        1`` and is one arrival from the outage; printing a bare OK there is the
        same over-narrow report this whole change exists to fix.
        """
        summary = (
            f"{part['allocatable']}/{part['total']} visitor slot(s) "
            f"allocatable ({describe_partition(part)})"
        )
        if part["allocatable"] < warn_below:
            cause = capacity_cause(part)
            self.stdout.write(
                self.style.WARNING(
                    f"WARNING: only {summary}.\n"
                    f"  -> the next arrival takes the last slot, and a consumed "
                    f"slot does not return for tens of minutes.\n"
                    f"  -> Cause: {cause}. {REPAIR_BY_CAUSE[cause]}"
                )
            )
            return
        self.stdout.write(self.style.SUCCESS(f"OK: {summary}"))
