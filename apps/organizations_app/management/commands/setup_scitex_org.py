"""
Management command to set up the scitex-ai organization.
"""

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from apps.organizations_app.models import Organization, OrganizationMembership


class Command(BaseCommand):
    help = "Create the scitex-ai organization for internal project hosting"

    def add_arguments(self, parser):
        parser.add_argument(
            "--admin",
            type=str,
            default="ywatanabe",
            help="Username to set as organization admin (default: ywatanabe)",
        )

    def handle(self, *args, **options):
        admin_username = options["admin"]

        # Create or get the organization
        org, created = Organization.objects.get_or_create(
            slug="scitex-ai",
            defaults={
                "name": "SciTeX AI",
                "description": "Official SciTeX organization for core projects and infrastructure.",
                "website": "https://scitex.ai",
            },
        )

        if created:
            self.stdout.write(
                self.style.SUCCESS(f"Created organization: {org.name} ({org.slug})")
            )
        else:
            self.stdout.write(
                self.style.WARNING(
                    f"Organization already exists: {org.name} ({org.slug})"
                )
            )

        # Add admin user if specified
        try:
            admin_user = User.objects.get(username=admin_username)
            membership, mem_created = OrganizationMembership.objects.get_or_create(
                user=admin_user,
                organization=org,
                defaults={"role": "admin"},
            )
            if mem_created:
                self.stdout.write(
                    self.style.SUCCESS(f"Added {admin_username} as admin")
                )
            else:
                # Update to admin if not already
                if membership.role != "admin":
                    membership.role = "admin"
                    membership.save()
                    self.stdout.write(
                        self.style.SUCCESS(f"Updated {admin_username} to admin role")
                    )
                else:
                    self.stdout.write(
                        self.style.WARNING(f"{admin_username} is already an admin")
                    )
        except User.DoesNotExist:
            self.stdout.write(
                self.style.WARNING(
                    f"User '{admin_username}' not found, skipping admin setup"
                )
            )

        self.stdout.write(self.style.SUCCESS(f"\nOrganization URL: /{org.slug}/"))
