"""
Management command to create a project with Gitea repo and workspace.

Triggers the same signal chain as the web UI:
  Project.objects.create() → post_save signal → Gitea repo → workspace clone

Usage:
    python manage.py create_project --owner ywatanabe --name my-project
    python manage.py create_project --owner ywatanabe --name my-project --description "Research project"
    python manage.py create_project --owner ywatanabe --name my-project --template research
"""

import logging

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError

from apps.infra.project_app.models import Project
from apps.infra.project_app.views.projects.create_helpers import (
    generate_unique_slug,
)

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Create a project with Gitea repository and workspace directory"

    def add_arguments(self, parser):
        parser.add_argument(
            "--owner", required=True, help="Username of the project owner"
        )
        parser.add_argument("--name", required=True, help="Project name")
        parser.add_argument("--description", default="", help="Project description")
        parser.add_argument(
            "--template",
            choices=["empty", "research", "minimal", "app"],
            default="empty",
            help="Initialization template (default: empty)",
        )
        parser.add_argument("--json", action="store_true", help="Output JSON")

    def handle(self, *args, **options):
        import json as _json

        username = options["owner"]
        name = options["name"]
        description = options["description"]
        template_type = options["template"]
        output_json = options["json"]

        # Resolve owner
        try:
            owner = User.objects.get(username=username)
        except User.DoesNotExist:
            raise CommandError(f"User '{username}' does not exist")

        # Generate unique slug
        slug = generate_unique_slug(name, owner)

        # Create project — post_save signal creates Gitea repo + workspace
        try:
            project = Project.objects.create(
                name=name,
                slug=slug,
                description=description,
                owner=owner,
            )
        except Exception as e:
            raise CommandError(f"Failed to create project: {e}")

        # Apply template if requested
        if template_type != "empty":
            try:
                from apps.infra.project_app.services.project_filesystem import (
                    get_project_filesystem_manager,
                )

                manager = get_project_filesystem_manager(owner)

                if template_type == "app":

                    # create_handlers expects request, but we only need project + manager
                    manager.initialize_project_from_template(project, "app")
                else:
                    manager.initialize_project_from_template(project, template_type)
            except Exception as e:
                logger.warning("Template initialization failed: %s", e)
                if not output_json:
                    self.stderr.write(
                        self.style.WARNING(
                            f"Template init failed: {e} (project created without template)"
                        )
                    )

        # Refresh to get signal-updated fields
        project.refresh_from_db()

        result = {
            "success": True,
            "project": {
                "id": project.id,
                "name": project.name,
                "slug": project.slug,
                "owner": project.owner.username,
                "gitea_enabled": project.gitea_enabled,
                "gitea_repo_id": project.gitea_repo_id,
                "url": f"/{project.owner.username}/{project.slug}/",
            },
        }

        if output_json:
            self.stdout.write(_json.dumps(result))
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Created project: {project.owner.username}/{project.slug}"
                    f" (Gitea: {'yes' if project.gitea_enabled else 'no'})"
                )
            )
