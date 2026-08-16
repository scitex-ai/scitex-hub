"""Fail loudly unless the visitor pool can actually hand out a slot.

WHY THIS EXISTS. ``create_visitor_pool`` creates users, projects and
workspaces; ``reconcile_visitor_slots`` wipes, verifies and un-quarantines
them. NEITHER of them exits non-zero when the result is a pool that can
serve nobody:

  * ``create_visitor_pool`` never creates a ``VisitorAllocation`` row at
    all, and ``PoolAllocator._try_allocate_slot`` refuses a slot whose row
    is missing ("no allocation row (unverified)"). So a pool that
    "initialized successfully" can still be 100% unallocatable.
  * ``reconcile_visitor_slots`` prints ``NO slot verified clean`` and
    exits 0.

In both cases allocation silently falls back to the SHARED
``readonly-visitor`` account, every page still renders, and any caller
downstream — a screenshot job, a smoke test, a human reading a deploy log
— concludes the product is fine. Production ran in exactly that state on
2026-08-16 with 15 of 16 slots quarantined.

This command asks the ONE question that matters — "can a visitor get a
writable slot right now?" — using the same predicate allocation itself
uses (``get_pool_status()['ready']``: not quarantined, not allocated,
workspace verified). Non-zero exit when the answer is no.

It is a CHECK, not a fixer: it changes nothing, so it is safe to run
anywhere, and a green run means the next visitor really can be served.

Usage:
    python manage.py assert_visitor_pool_ready          # need >= 1 ready
    python manage.py assert_visitor_pool_ready --min 2  # need >= 2 ready
"""

from django.core.management.base import BaseCommand, CommandError

from apps.infra.project_app.services.visitor_pool import VisitorPool


class Command(BaseCommand):
    help = (
        "Exit non-zero unless at least --min visitor slots are ready to be "
        "allocated (not quarantined, not in use, workspace verified clean)"
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--min",
            dest="minimum",
            type=int,
            default=1,
            help=(
                "Minimum number of READY slots required (default: 1). One is "
                "enough for a single-session consumer such as the screenshot "
                "capture; raise it when several concurrent visitors matter."
            ),
        )

    def handle(self, *args, **options):
        minimum = options["minimum"]
        if minimum < 1:
            raise CommandError(
                f"--min must be at least 1; {minimum} would make this command "
                f"incapable of failing, which is the defect it exists to catch."
            )

        status = VisitorPool.get_pool_status()
        ready = status["ready"]

        self.stdout.write(
            "Visitor pool: total=%s ready=%s allocated=%s free=%s "
            "quarantined=%s expired=%s"
            % (
                status["total"],
                ready,
                status["allocated"],
                status["free"],
                status["quarantined"],
                status["expired"],
            )
        )

        if ready < minimum:
            raise CommandError(
                f"Visitor pool CANNOT serve a writable slot: ready={ready}, "
                f"required={minimum} (of {status['total']} slots; "
                f"{status['quarantined']} quarantined, {status['allocated']} "
                f"in use).\n"
                f"  Every visitor would be downgraded to the shared "
                f"readonly-visitor account, which renders perfectly — so "
                f"nothing downstream can tell the difference. That is why "
                f"this check exists rather than trusting the pages to look "
                f"right.\n"
                f"  Repair: run `manage.py create_visitor_pool` then "
                f"`manage.py reconcile_visitor_slots` and read their output; "
                f"a slot that fails re-clean records the reason in "
                f"VisitorAllocation.quarantine_reason."
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"✓ {ready} visitor slot(s) ready (>= {minimum} required) — "
                f"a visitor gets a writable pooled slot, not the "
                f"readonly-visitor fallback"
            )
        )
