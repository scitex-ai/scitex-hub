"""
Django management command to delete all projects and Gitea repositories

Usage:
    python manage.py cleanup_all_projects --username <username>
    python manage.py cleanup_all_projects --all  # Delete for all users
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from apps.infra.project_app.models import Project
from apps.infra.gitea_app.api_client import GiteaClient
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Delete all projects and associated Gitea repositories"

    def add_arguments(self, parser):
        parser.add_argument(
            "--username", type=str, help="Username to clean up projects for"
        )
        parser.add_argument(
            "--all", action="store_true", help="Clean up all projects for all users"
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be deleted without actually deleting",
        )

    def handle(self, *args, **options):
        username = options.get("username")
        all_users = options.get("all")
        dry_run = options.get("dry_run")

        if not username and not all_users:
            self.stdout.write(self.style.ERROR("Please specify --username or --all"))
            return

        # Get users to process
        if all_users:
            users = User.objects.all()
        else:
            try:
                users = [User.objects.get(username=username)]
            except User.DoesNotExist:
                self.stdout.write(self.style.ERROR(f'User "{username}" not found'))
                return

        total_deleted = 0
        total_gitea_deleted = 0
        total_errors = 0

        for user in users:
            self.stdout.write(self.style.WARNING(f"\nProcessing user: {user.username}"))

            # Get all projects for this user
            projects = Project.objects.filter(owner=user)
            project_count = projects.count()

            if project_count == 0:
                self.stdout.write("  No projects found")
                continue

            self.stdout.write(f"  Found {project_count} projects")

            for project in projects:
                try:
                    # Delete Gitea repository if exists
                    if project.gitea_enabled and project.gitea_repo_name:
                        if dry_run:
                            self.stdout.write(
                                f"    [DRY RUN] Would delete Gitea repo: {project.gitea_repo_name}"
                            )
                        else:
                            try:
                                client = GiteaClient()
                                client.delete_repository(
                                    user.username, project.gitea_repo_name
                                )
                                total_gitea_deleted += 1
                                self.stdout.write(
                                    self.style.SUCCESS(
                                        f"    ✓ Deleted Gitea repo: {project.gitea_repo_name}"
                                    )
                                )
                            except Exception as e:
                                self.stdout.write(
                                    self.style.ERROR(
                                        f"    ✗ Failed to delete Gitea repo {project.gitea_repo_name}: {e}"
                                    )
                                )
                                total_errors += 1

                    # Delete Django project
                    project_name = project.name
                    if dry_run:
                        self.stdout.write(
                            f"    [DRY RUN] Would delete project: {project_name}"
                        )
                    else:
                        project.delete()
                        total_deleted += 1
                        self.stdout.write(
                            self.style.SUCCESS(f"    ✓ Deleted project: {project_name}")
                        )

                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(
                            f"    ✗ Error processing project {project.name}: {e}"
                        )
                    )
                    total_errors += 1

        # Summary
        self.stdout.write("\n" + "=" * 60)
        if dry_run:
            self.stdout.write(
                self.style.WARNING("[DRY RUN] No actual deletions performed")
            )
        self.stdout.write(self.style.SUCCESS(f"\nSummary:"))
        self.stdout.write(f"  Projects deleted: {total_deleted}")
        self.stdout.write(f"  Gitea repositories deleted: {total_gitea_deleted}")
        if total_errors > 0:
            self.stdout.write(self.style.ERROR(f"  Errors: {total_errors}"))
        self.stdout.write("=" * 60 + "\n")
