"""
Management command to reset all visitor workspaces.

Reinitializes visitor project directories with latest template.
Use after template updates or when projects are stale.

Usage:
    python manage.py reset_visitor_workspaces           # Reset all visitor workspaces
    python manage.py reset_visitor_workspaces --dry-run # Preview what would be reset
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User

from apps.infra.project_app.services.visitor_pool.workspace_manager import (
    WorkspaceManager,
)


class Command(BaseCommand):
    help = "Reset all visitor workspaces to latest template"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Preview what would be reset without making changes",
        )
        parser.add_argument(
            "--username",
            type=str,
            help="Reset only specific visitor (e.g., visitor-001)",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        specific_user = options.get("username")

        if specific_user:
            visitors = User.objects.filter(username=specific_user)
        else:
            visitors = User.objects.filter(
                username__startswith=WorkspaceManager.VISITOR_USER_PREFIX
            )

        count = visitors.count()
        self.stdout.write(f"\n=== Visitor Workspace Reset ===")
        self.stdout.write(f"Found {count} visitor accounts")

        if dry_run:
            self.stdout.write(self.style.WARNING("\n[DRY RUN] Would reset:"))
            for visitor in visitors:
                self.stdout.write(f"  - {visitor.username}")
            return

        from apps.infra.project_app.services.visitor_pool.slot_lifecycle import (
            get_or_create_allocation,
            reset_and_verify_slot,
        )

        reset_count = 0
        error_count = 0

        for visitor in visitors:
            self.stdout.write(f"Resetting {visitor.username}...")
            try:
                visitor_num = int(visitor.username.split("-", 1)[1])
            except (IndexError, ValueError):
                error_count += 1
                self.stdout.write(
                    self.style.ERROR(
                        f"  ✗ Cannot parse slot number from {visitor.username}"
                    )
                )
                continue

            allocation = get_or_create_allocation(visitor_num)
            if reset_and_verify_slot(allocation):
                reset_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f"  ✓ {visitor.username} reset successfully")
                )
            else:
                error_count += 1
                self.stdout.write(
                    self.style.ERROR(
                        f"  ✗ {visitor.username} not reset (active slot, or "
                        f"reset failed and slot quarantined — see logs; "
                        f"reconcile_visitor_slots re-cleans)"
                    )
                )

        self.stdout.write(f"\n=== Summary ===")
        self.stdout.write(self.style.SUCCESS(f"Reset: {reset_count}"))
        if error_count:
            self.stdout.write(self.style.ERROR(f"Errors: {error_count}"))

        self.stdout.write("\nVisitor workspaces refreshed with latest template!")
