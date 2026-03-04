"""
Management command to create figrecipe as a living example app project.

Creates a project owned by ywatanabe at /ywatanabe/figrecipe/ that
serves as a real, working demonstration of the app maker framework.

Usage:
    python manage.py create_figrecipe_project
"""

import os
from pathlib import Path

from django.conf import settings
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from apps.project_app.models import Project


class Command(BaseCommand):
    help = "Create figrecipe as a living example app project for user ywatanabe"

    def add_arguments(self, parser):
        parser.add_argument(
            "--owner",
            default="ywatanabe",
            help="Username of the project owner (default: ywatanabe)",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Recreate symlink even if project already exists",
        )

    def handle(self, *args, **options):
        owner_username = options["owner"]
        force = options["force"]

        # Get or create user
        try:
            user = User.objects.get(username=owner_username)
        except User.DoesNotExist:
            self.stderr.write(
                self.style.ERROR(
                    f"User '{owner_username}' not found. Create the user first."
                )
            )
            return

        # Create or get project
        project, created = Project.objects.get_or_create(
            owner=user,
            slug="figrecipe",
            defaults={
                "name": "Figrecipe",
                "description": (
                    "Interactive figure editor for publication-ready matplotlib "
                    "plots. A living example of the SciTeX app maker framework."
                ),
                "status": "active",
                "project_type": "local",
            },
        )

        if created:
            self.stdout.write(self.style.SUCCESS("Created figrecipe project record"))
        else:
            self.stdout.write(self.style.WARNING("Figrecipe project already exists"))

        # Set up project directory as symlink to figrecipe source
        project_dir = (
            Path(settings.BASE_DIR)
            / "data"
            / "users"
            / owner_username
            / "proj"
            / "figrecipe"
        )
        figrecipe_source = Path(
            os.environ.get(
                "FIGRECIPE_SOURCE",
                str(Path.home() / "proj" / "figrecipe"),
            )
        )

        if not figrecipe_source.exists():
            self.stderr.write(
                self.style.ERROR(
                    f"Figrecipe source not found at {figrecipe_source}. "
                    f"Set FIGRECIPE_SOURCE env var to the correct path."
                )
            )
            return

        # Ensure parent directory exists
        project_dir.parent.mkdir(parents=True, exist_ok=True)

        if project_dir.exists() or project_dir.is_symlink():
            if force:
                if project_dir.is_symlink():
                    project_dir.unlink()
                    self.stdout.write("Removed existing symlink")
                else:
                    self.stdout.write(
                        self.style.WARNING(
                            f"Directory exists at {project_dir} and is not a symlink. "
                            "Remove it manually if you want to recreate."
                        )
                    )
                    return
            else:
                target = os.readlink(project_dir) if project_dir.is_symlink() else "dir"
                self.stdout.write(
                    self.style.WARNING(
                        f"Project directory already exists -> {target}. "
                        "Use --force to recreate."
                    )
                )
                self.stdout.write(
                    self.style.SUCCESS(
                        f"\nFigrecipe project ready at: /{owner_username}/figrecipe/"
                    )
                )
                return

        # Create symlink
        project_dir.symlink_to(figrecipe_source)
        self.stdout.write(
            self.style.SUCCESS(f"Created symlink: {project_dir} -> {figrecipe_source}")
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"\nFigrecipe project ready at: /{owner_username}/figrecipe/"
            )
        )
        self.stdout.write("  - Workspace: navigate to the figrecipe tab in any project")
        self.stdout.write("  - Standalone: run 'figrecipe gui' on port 5050")
