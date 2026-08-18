#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Django management command to initialize test user for development.

Usage:
    python manage.py init_test_user

Or via Docker:
    docker exec scitex-hub-dev-django-1 python manage.py init_test_user

Environment Variables (from deployment/docker/envs/.env.dev):
    SCITEX_HUB_TEST_USER_USERNAME - Test user username (default: test-user)
    SCITEX_HUB_TEST_USER_PASSWORD - Test user password. NO DEFAULT: when unset a
                                    random password is generated and printed.
    SCITEX_HUB_TEST_USER_EMAIL    - Test user email (default: test@example.com)
"""

import logging
import os
import secrets

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

logger = logging.getLogger(__name__)

# Default values from environment variables
DEFAULT_USERNAME = os.getenv("SCITEX_HUB_TEST_USER_USERNAME", "test-user")
DEFAULT_EMAIL = os.getenv("SCITEX_HUB_TEST_USER_EMAIL", "test@example.com")

# There is deliberately NO built-in password default.
#
# A literal here is not a placeholder, it is a SHARED credential: every
# deployment that omits the env var converges on the same value, and this
# repository is PUBLIC. The previous default, "Password123!", was documented in
# the README, the setup page and the docs — and on 2026-08-16 it was found to
# authenticate as `test-user` on PRODUCTION. The account was closed; this
# removes the code path that recreates it.
#
# Absent an explicit password we mint a random one and print it. A forgotten
# env var then yields a credential NOBODY knows instead of one EVERYBODY does,
# which is the only difference that matters. The password is echoed at the end
# of this command, so the dev workflow is "read the output" rather than "read
# the source" — a small ergonomic cost, taken deliberately.
PASSWORD_ENV_VAR = "SCITEX_HUB_TEST_USER_PASSWORD"


def resolve_password(explicit=None):
    """Return ``(password, was_generated)``.

    Precedence: ``--password`` > ``$SCITEX_HUB_TEST_USER_PASSWORD`` > generated.
    Never returns a value baked into this file.
    """
    if explicit:
        return explicit, False
    from_env = os.getenv(PASSWORD_ENV_VAR)
    if from_env:
        return from_env, False
    return secrets.token_urlsafe(24), True


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
            default=None,
            help=(
                f"Password for the test user. Falls back to ${PASSWORD_ENV_VAR}, "
                "then to a generated random password (printed below)."
            ),
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
        password, generated = resolve_password(options["password"])
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
        if generated:
            # Say it was generated. Otherwise this looks like a fixed value
            # somebody could go and look up later, which is the habit that put
            # a published literal onto production in the first place.
            self.stdout.write(
                self.style.WARNING(
                    f"\n  ^ generated for this run because ${PASSWORD_ENV_VAR} is unset."
                    "\n    It is NOT stored anywhere else and NOT recoverable from the"
                    f"\n    source. Copy it now, or set ${PASSWORD_ENV_VAR} and re-run."
                )
            )

    def _sync_to_gitea(self, user, password):
        """Sync user to Gitea."""
        try:
            from apps.infra.project_app.services.gitea_sync_service import (
                sync_user_to_gitea,
            )

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
            from apps.infra.gitea_app.api_client import GiteaClient
            from apps.infra.project_app.models import Project

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
