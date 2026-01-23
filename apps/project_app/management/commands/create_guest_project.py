"""
Management command to create/update guest user and demo project.

Usage:
    python manage.py create_guest_project
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from apps.project_app.models import Project


class Command(BaseCommand):
    help = "Create or update guest user and demo project for visitor users"

    def handle(self, *args, **options):
        # Create or get guest user
        guest_user, created = User.objects.get_or_create(
            username="guest",
            defaults={
                "email": "guest@scitex.ai",
                "first_name": "Guest",
                "last_name": "User",
                "is_active": True,
            },
        )

        if created:
            guest_user.set_unusable_password()  # Guest cannot login
            guest_user.save()
            self.stdout.write(self.style.SUCCESS("Created guest user"))
        else:
            self.stdout.write(self.style.WARNING("Guest user already exists"))

        # Create or get demo project
        demo_project, created = Project.objects.get_or_create(
            owner=guest_user,
            slug="demo-project",
            defaults={
                "name": "Demo Project",
                "description": "Try SciTeX Cloud features without signing up. This is a read-only demo workspace.",
                "status": "active",
                "hypotheses": "This is a demonstration project for exploring SciTeX Cloud capabilities.",
            },
        )

        if created:
            self.stdout.write(self.style.SUCCESS("Created demo project"))

            # Initialize demo project structure
            from apps.project_app.services.project_filesystem import (
                get_project_filesystem_manager,
            )

            manager = get_project_filesystem_manager(guest_user)
            project_path = manager.get_project_root_path(demo_project)

            if project_path:
                # Create paper directory with template
                try:
                    from apps.writer_app.models import Manuscript

                    # Since project is OneToOneField, only use project for lookup
                    manuscript, ms_created = Manuscript.objects.get_or_create(
                        project=demo_project,
                        defaults={
                            "owner": demo_project.owner,
                            "title": "Demo Manuscript",
                            "slug": "demo-manuscript",
                            "is_modular": True,
                            "abstract": "This is a demonstration manuscript to showcase SciTeX Writer features.",
                        },
                    )

                    if ms_created:
                        manuscript.create_modular_structure()
                        self.stdout.write(
                            self.style.SUCCESS("Created demo manuscript structure")
                        )
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f"Failed to create manuscript: {e}")
                    )

        else:
            self.stdout.write(self.style.WARNING("Demo project already exists"))

        self.stdout.write(
            self.style.SUCCESS(f"\nGuest project ready at: /guest/demo-project/")
        )
        self.stdout.write(
            self.style.SUCCESS(
                "Visitor users will be routed here when clicking module links"
            )
        )
