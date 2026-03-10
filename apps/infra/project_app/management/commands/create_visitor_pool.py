"""
Management command to create visitor pool.

Usage:
    python manage.py create_visitor_pool                # Create 4 visitors (default)
    python manage.py create_visitor_pool --size 8       # Create 8 visitors
    python manage.py create_visitor_pool --status       # Show pool status
"""

from django.core.management.base import BaseCommand
from apps.infra.project_app.services.visitor_pool import VisitorPool


class Command(BaseCommand):
    help = "Create and manage visitor pool (visitor-001 to visitor-004)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--size",
            type=int,
            default=None,
            help="Pool size (default: 4)",
        )
        parser.add_argument(
            "--status",
            action="store_true",
            help="Show pool status without creating",
        )

    def handle(self, *args, **options):
        if options["status"]:
            # Show pool status
            status = VisitorPool.get_pool_status()
            self.stdout.write("\n=== Visitor Pool Status ===")
            self.stdout.write(f"Total slots: {status['total']}")
            self.stdout.write(f"Allocated: {status['allocated']}")
            self.stdout.write(f"Free: {status['free']}")
            self.stdout.write(f"Expired: {status['expired']}")
            return

        # Create visitor pool
        pool_size = options["size"] or VisitorPool.POOL_SIZE

        self.stdout.write(f"\nInitializing visitor pool (size={pool_size})...")
        self.stdout.write("This will create:")
        self.stdout.write(f"  - visitor-001 to visitor-{pool_size:03d} (users)")
        self.stdout.write(
            f'  - {pool_size} "default-project" projects (one per visitor user)'
        )
        self.stdout.write("")

        created = VisitorPool.initialize_pool(pool_size=pool_size)

        # Get pool status to show comprehensive feedback
        status = VisitorPool.get_pool_status()

        if created > 0:
            self.stdout.write(
                self.style.SUCCESS(
                    f"\n✓ Created {created} new visitor accounts with projects"
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"\n✓ Visitor pool already initialized (0 new accounts created)"
                )
            )

        self.stdout.write(f"\n📊 Pool Status:")
        self.stdout.write(f"  Total slots: {status['total']}")
        self.stdout.write(f"  Available: {status['free']}")
        self.stdout.write(f"  In use: {status['allocated']}")

        self.stdout.write("\nPool ready for visitors!")
        self.stdout.write(
            f"\nTo check status: python manage.py create_visitor_pool --status"
        )
