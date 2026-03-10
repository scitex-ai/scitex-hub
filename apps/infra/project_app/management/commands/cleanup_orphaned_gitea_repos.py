#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Management command to cleanup orphaned Gitea repositories.

An orphaned Gitea repository is one that exists in Gitea but has no
corresponding Django Project. This violates the strict 1:1 mapping
principle: Local ↔ Django ↔ Gitea
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from apps.infra.project_app.models import Project
from apps.infra.gitea_app.api_client import GiteaClient
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Find and optionally delete orphaned Gitea repositories"

    def add_arguments(self, parser):
        parser.add_argument(
            "--delete",
            action="store_true",
            help="Actually delete orphaned repositories (default: dry run)",
        )
        parser.add_argument(
            "--username", type=str, help="Only check repositories for specific user"
        )

    def handle(self, *args, **options):
        delete_mode = options["delete"]
        username_filter = options.get("username")

        self.stdout.write(
            self.style.WARNING(
                "Checking for orphaned Gitea repositories...\n"
                "Orphaned = exists in Gitea but no Django Project\n"
            )
        )

        if not delete_mode:
            self.stdout.write(
                self.style.WARNING(
                    "DRY RUN MODE - Use --delete to actually remove orphaned repos\n"
                )
            )

        client = GiteaClient()

        # Get users to check
        users = User.objects.all()
        if username_filter:
            users = users.filter(username=username_filter)

        total_users = users.count()
        total_orphaned = 0
        total_deleted = 0
        errors = 0

        for user in users:
            self.stdout.write(f"\nChecking user: {user.username}")

            try:
                # Get all Gitea repos for this user
                gitea_repos = client.list_repositories(user.username)

                if not gitea_repos:
                    self.stdout.write(f"  No Gitea repositories found")
                    continue

                self.stdout.write(f"  Found {len(gitea_repos)} Gitea repositories")

                # Get all Django projects for this user
                django_projects = set(
                    Project.objects.filter(owner=user).values_list("slug", flat=True)
                )

                # Find orphaned repos
                for repo in gitea_repos:
                    repo_name = repo["name"]
                    repo_id = repo["id"]

                    if repo_name not in django_projects:
                        # Orphaned repository found!
                        total_orphaned += 1
                        self.stdout.write(
                            self.style.ERROR(
                                f"  ❌ ORPHANED: {user.username}/{repo_name} (Gitea ID: {repo_id})"
                            )
                        )

                        if delete_mode:
                            try:
                                client.delete_repository(user.username, repo_name)
                                total_deleted += 1
                                self.stdout.write(
                                    self.style.SUCCESS(f"     ✓ DELETED from Gitea")
                                )
                            except Exception as del_error:
                                errors += 1
                                self.stdout.write(
                                    self.style.ERROR(
                                        f"     ✗ FAILED TO DELETE: {del_error}"
                                    )
                                )
                                logger.error(
                                    f"Failed to delete {user.username}/{repo_name}: {del_error}",
                                    exc_info=True,
                                )
                    else:
                        # Has Django project - this is correct
                        self.stdout.write(
                            f"  ✓ OK: {user.username}/{repo_name} (has Django project)"
                        )

            except Exception as e:
                errors += 1
                self.stdout.write(
                    self.style.ERROR(f"  ✗ ERROR checking {user.username}: {e}")
                )
                logger.error(
                    f"Failed to check user {user.username}: {e}", exc_info=True
                )

        # Summary
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(f"Total users checked: {total_users}")
        self.stdout.write(
            self.style.ERROR(f"Orphaned repositories found: {total_orphaned}")
        )

        if delete_mode:
            self.stdout.write(
                self.style.SUCCESS(f"Successfully deleted: {total_deleted}")
            )
        else:
            self.stdout.write(
                self.style.WARNING(
                    f"\nTo delete these {total_orphaned} orphaned repos, run:"
                )
            )
            self.stdout.write(
                self.style.WARNING(
                    "  python manage.py cleanup_orphaned_gitea_repos --delete"
                )
            )

        if errors > 0:
            self.stdout.write(self.style.ERROR(f"Errors: {errors}"))

        self.stdout.write("=" * 60)
