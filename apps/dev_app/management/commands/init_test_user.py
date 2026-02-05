#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Django management command to initialize test user for development.

Usage:
    python manage.py init_test_user

Or via Docker:
    docker exec scitex-cloud-dev-django-1 python manage.py init_test_user

Environment Variables (from SECRET/.env.dev):
    SCITEX_CLOUD_TEST_USER_USERNAME - Test user username (default: test-user)
    SCITEX_CLOUD_TEST_USER_PASSWORD - Test user password (default: Password123!)
    SCITEX_CLOUD_TEST_USER_EMAIL    - Test user email (default: test@example.com)
"""

import logging
import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

logger = logging.getLogger(__name__)

# Default values from environment variables
DEFAULT_USERNAME = os.getenv("SCITEX_CLOUD_TEST_USER_USERNAME", "test-user")
DEFAULT_PASSWORD = os.getenv("SCITEX_CLOUD_TEST_USER_PASSWORD", "Password123!")
DEFAULT_EMAIL = os.getenv("SCITEX_CLOUD_TEST_USER_EMAIL", "test@example.com")


class Command(BaseCommand):
    help = "Initialize test user for development with Gitea sync and default project"

    def add_arguments(self, parser):
        parser.add_argument(
            "--username",
            type=str,
            default=DEFAULT_USERNAME,
            help=f"Username for the test user (default: {DEFAULT_USERNAME})",
        )
        parser.add_argument(
            "--password",
            type=str,
            default=DEFAULT_PASSWORD,
            help="Password for the test user (from SCITEX_CLOUD_TEST_USER_PASSWORD)",
        )
        parser.add_argument(
            "--email",
            type=str,
            default=DEFAULT_EMAIL,
            help=f"Email for the test user (default: {DEFAULT_EMAIL})",
        )

    def handle(self, *args, **options):
        User = get_user_model()
        username = options["username"]
        password = options["password"]
        email = options["email"]

        # Create Django user
        user, created = User.objects.get_or_create(
            username=username,
            defaults={"email": email},
        )

        user.set_password(password)
        user.save()

        if created:
            self.stdout.write(self.style.SUCCESS(f"✓ Test user created: {username}"))
        else:
            self.stdout.write(self.style.SUCCESS(f"✓ Test user updated: {username}"))

        # Sync user to Gitea
        self._sync_to_gitea(user, password)

        # Create default project with Gitea repo
        self._create_default_project(user)

        self.stdout.write(
            self.style.SUCCESS(
                f"\nCredentials:\n  Username: {username}\n  Password: {password}\n  Email: {email}"
            )
        )

    def _sync_to_gitea(self, user, password):
        """Sync user to Gitea."""
        try:
            from apps.project_app.services.gitea_sync_service import sync_user_to_gitea

            if sync_user_to_gitea(user, password):
                self.stdout.write(
                    self.style.SUCCESS(f"✓ Synced to Gitea: {user.username}")
                )
            else:
                self.stdout.write(
                    self.style.WARNING("⚠ Failed to sync to Gitea (may already exist)")
                )
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"⚠ Gitea sync skipped: {e}"))

    def _create_default_project(self, user):
        """Create default project with Gitea repository."""
        try:
            from apps.gitea_app.api_client import GiteaClient
            from apps.project_app.models import Project

            project, created = Project.objects.get_or_create(
                owner=user,
                slug="default-project",
                defaults={
                    "name": "Default Project",
                    "description": "Default project for testing and development.",
                    "visibility": "public",
                },
            )
            # Ensure visibility is public
            if project.visibility != "public":
                project.visibility = "public"
                project.save()

            if created:
                self.stdout.write(
                    self.style.SUCCESS("✓ Created default-project in Django")
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS("✓ default-project exists in Django")
                )

            # Create Gitea repo if not exists
            if not project.gitea_repo_name:
                try:
                    client = GiteaClient()
                    repo_data = client.create_repository(
                        name="default-project",
                        description="Default project for testing and development.",
                        private=False,
                        owner=user.username,
                    )
                    project.gitea_repo_name = repo_data.get("name", "default-project")
                    project.save()
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"✓ Created Gitea repo: {project.gitea_repo_name}"
                        )
                    )
                except Exception as e:
                    # Repo may already exist
                    if "already exists" in str(e).lower():
                        project.gitea_repo_name = "default-project"
                        project.save()
                        self.stdout.write(
                            self.style.SUCCESS("✓ Gitea repo already exists")
                        )
                    else:
                        self.stdout.write(
                            self.style.WARNING(f"⚠ Gitea repo creation: {e}")
                        )
            else:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"✓ Gitea repo exists: {project.gitea_repo_name}"
                    )
                )

        except Exception as e:
            self.stdout.write(self.style.WARNING(f"⚠ Default project creation: {e}"))
