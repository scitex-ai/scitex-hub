"""
Management command to reset visitor pool.

Usage:
    python manage.py reset_visitor_pool                 # Reset all visitor workspaces
    python manage.py reset_visitor_pool --visitor 5     # Reset only visitor-005
    python manage.py reset_visitor_pool --free-expired  # Free expired allocations
"""

from django.core.management.base import BaseCommand

from apps.infra.project_app.services.visitor_pool import VisitorPool


class Command(BaseCommand):
    help = "Reset visitor pool workspaces and free expired slots"

    def add_arguments(self, parser):
        parser.add_argument(
            "--visitor",
            type=int,
            help="Reset specific visitor number (1-4 default, depends on pool size)",
        )
        parser.add_argument(
            "--free-expired",
            action="store_true",
            help="Only free expired allocations (no workspace reset)",
        )

    def handle(self, *args, **options):
        if options["free_expired"]:
            # Free expired allocations
            self.stdout.write("Freeing expired visitor allocations...")
            freed = VisitorPool.cleanup_expired_allocations()
            self.stdout.write(
                self.style.SUCCESS(f"✓ Freed {freed} expired allocations")
            )

            # Show updated status
            status = VisitorPool.get_pool_status()
            self.stdout.write(
                f"\nPool status: {status['free']}/{status['total']} slots free"
            )
            return

        if options["visitor"]:
            # Reset specific visitor
            visitor_num = options["visitor"]
            if visitor_num < 1 or visitor_num > VisitorPool.POOL_SIZE:
                self.stdout.write(
                    self.style.ERROR(
                        f"Error: Visitor number must be 1-{VisitorPool.POOL_SIZE}"
                    )
                )
                return

            self.stdout.write(f"Resetting visitor-{visitor_num:03d}...")
            # TODO: Implement single visitor reset
            self.stdout.write(
                self.style.WARNING("Single visitor reset not yet implemented")
            )
            return

        # Reset all visitor workspaces - hard reset on restart/rebuild/daily
        self.stdout.write(
            self.style.WARNING("Resetting ALL visitor allocations and workspaces...")
        )

        # Deactivate all allocations and take them out of circulation
        # until each one re-verifies clean below (security: a slot with
        # an unverified workspace must never be redistributed).
        from apps.infra.project_app.models import VisitorAllocation

        deactivated_count = VisitorAllocation.objects.filter(is_active=True).update(
            is_active=False
        )
        VisitorAllocation.objects.update(workspace_ready=False)

        # Wipe + verify each slot through the canonical pipeline; a
        # failed reset quarantines the slot (never redistributed).
        from apps.infra.project_app.services.visitor_pool.slot_lifecycle import (
            get_or_create_allocation,
            reset_and_verify_slot,
        )

        reset_count = 0
        for visitor_num in range(1, VisitorPool.POOL_SIZE + 1):
            allocation = get_or_create_allocation(visitor_num)
            if reset_and_verify_slot(allocation):
                reset_count += 1
            else:
                self.stdout.write(
                    self.style.ERROR(
                        f"  Failed to reset visitor-{visitor_num:03d} — slot "
                        f"QUARANTINED (see logs; reconcile_visitor_slots re-cleans)"
                    )
                )

        self.stdout.write(
            self.style.SUCCESS(
                f"✓ Reset complete: {deactivated_count} allocations freed, "
                f"{reset_count} workspaces cleaned"
            )
        )

        # Show updated status
        status = VisitorPool.get_pool_status()
        self.stdout.write(
            f"\nPool status: {status['free']}/{status['total']} slots free"
        )
