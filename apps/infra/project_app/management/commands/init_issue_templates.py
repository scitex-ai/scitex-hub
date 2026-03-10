"""
Management command to initialize default issue templates and labels for projects.

Usage:
    python manage.py init_issue_templates                    # All projects
    python manage.py init_issue_templates --project=slug    # Specific project
    python manage.py init_issue_templates --user=username   # User's projects
"""

from django.core.management.base import BaseCommand

from apps.infra.project_app.models import Project
from apps.infra.project_app.models.issues import IssueLabel, IssueTemplate


class Command(BaseCommand):
    help = "Initialize default issue templates and labels for projects"

    def add_arguments(self, parser):
        parser.add_argument(
            "--project",
            type=str,
            help="Project slug to initialize (default: all projects)",
        )
        parser.add_argument(
            "--user",
            type=str,
            help="Initialize all projects owned by this user",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Overwrite existing templates and labels",
        )

    def handle(self, *args, **options):
        projects = Project.objects.all()

        if options["project"]:
            projects = projects.filter(slug=options["project"])
        if options["user"]:
            projects = projects.filter(owner__username=options["user"])

        if not projects.exists():
            self.stdout.write(self.style.WARNING("No projects found"))
            return

        for project in projects:
            self._init_project(project, force=options["force"])

        self.stdout.write(
            self.style.SUCCESS(f"Initialized {projects.count()} project(s)")
        )

    def _init_project(self, project, force=False):
        """Initialize templates and labels for a single project."""
        self.stdout.write(f"Initializing: {project.owner.username}/{project.slug}")

        # Create default labels
        labels_created = self._create_default_labels(project, force)

        # Create default templates
        templates_created = self._create_default_templates(project, force)

        self.stdout.write(f"  Labels: {labels_created}, Templates: {templates_created}")

    def _create_default_labels(self, project, force=False):
        """Create default issue labels."""
        default_labels = [
            {
                "name": "bug",
                "color": "#d73a4a",
                "description": "Something isn't working",
            },
            {
                "name": "enhancement",
                "color": "#a2eeef",
                "description": "New feature or request",
            },
            {
                "name": "documentation",
                "color": "#0075ca",
                "description": "Improvements or additions to documentation",
            },
            {
                "name": "question",
                "color": "#d876e3",
                "description": "Further information is requested",
            },
            {
                "name": "duplicate",
                "color": "#cfd3d7",
                "description": "This issue or PR already exists",
            },
            {
                "name": "wontfix",
                "color": "#ffffff",
                "description": "This will not be worked on",
            },
            {
                "name": "good first issue",
                "color": "#7057ff",
                "description": "Good for newcomers",
            },
            {
                "name": "help wanted",
                "color": "#008672",
                "description": "Extra attention is needed",
            },
            {
                "name": "invalid",
                "color": "#e4e669",
                "description": "This doesn't seem right",
            },
        ]

        created = 0
        for label_data in default_labels:
            label, was_created = IssueLabel.objects.get_or_create(
                project=project,
                name=label_data["name"],
                defaults={
                    "color": label_data["color"],
                    "description": label_data["description"],
                },
            )
            if was_created:
                created += 1
            elif force:
                label.color = label_data["color"]
                label.description = label_data["description"]
                label.save()

        return created

    def _create_default_templates(self, project, force=False):
        """Create default issue templates."""
        default_templates = IssueTemplate.get_default_templates()

        created = 0
        for template_data in default_templates:
            # Get or create the template
            template, was_created = IssueTemplate.objects.get_or_create(
                project=project,
                name=template_data["name"],
                defaults={
                    "description": template_data["description"],
                    "template_type": template_data["template_type"],
                    "icon": template_data["icon"],
                    "title_prefix": template_data["title_prefix"],
                    "body_template": template_data["body_template"],
                    "order": template_data["order"],
                },
            )
            if was_created:
                created += 1

                # Auto-assign matching label if exists
                label_map = {
                    "bug": "bug",
                    "feature": "enhancement",
                    "docs": "documentation",
                }
                label_name = label_map.get(template_data["template_type"])
                if label_name:
                    try:
                        label = IssueLabel.objects.get(project=project, name=label_name)
                        template.labels.add(label)
                    except IssueLabel.DoesNotExist:
                        pass

            elif force:
                for key, value in template_data.items():
                    if key != "name":
                        setattr(template, key, value)
                template.save()

        return created
