#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Management command to create the central app registry repo on Gitea.

Creates an org-owned `scitex/apps` repo (like MELPA) where every app
submission opens a PR.  Merge = approval via webhook.
"""

from __future__ import annotations

import base64
import logging

from django.core.management.base import BaseCommand

logger = logging.getLogger(__name__)

REGISTRY_ORG = "scitex"
REGISTRY_REPO_NAME = "apps"
REGISTRY_REPO_DESC = (
    "Central registry for SciTeX app submissions — "
    "submit via PR, merge to approve (like MELPA)"
)
APPS_ORG = "scitex-apps"


class Command(BaseCommand):
    help = "Create the scitex/apps registry repo on Gitea (one-time setup)"

    def handle(self, *args, **options):
        from apps.gitea_app.api_client import GiteaClient

        client = GiteaClient()

        # ── 1. Ensure the `scitex` organisation exists ──────────────────
        self._ensure_org(client)

        # ── 1b. Add superusers to org Owners team ─────────────────────
        self._add_superusers_to_org(client)

        # ── 1c. Ensure the `scitex-apps` organisation exists ────────────
        self._ensure_apps_org(client)

        # ── 2. Create the `apps` repo under the org ─────────────────────
        created = self._create_repo(client)

        # ── 3. Initialise `apps/` directory + README (first time only) ──
        if created:
            self._init_contents(client)
            self._register_webhook(client)

        # ── 4. Ensure Django Project record exists (always) ──────────────
        self._ensure_django_project()

    # ------------------------------------------------------------------
    def _ensure_org(self, client):
        """Create the `scitex` Gitea organisation if it doesn't exist."""
        from apps.gitea_app.api_client import GiteaAPIError

        try:
            client._request("GET", f"/orgs/{REGISTRY_ORG}")
            self.stdout.write(f"Organisation '{REGISTRY_ORG}' already exists.")
        except GiteaAPIError:
            try:
                client._request(
                    "POST",
                    "/orgs",
                    json={
                        "username": REGISTRY_ORG,
                        "full_name": "SciTeX",
                        "description": "SciTeX open-source scientific research platform",
                        "visibility": "public",
                    },
                )
                self.stdout.write(
                    self.style.SUCCESS(f"Created organisation: {REGISTRY_ORG}")
                )
            except GiteaAPIError as exc:
                self.stderr.write(f"Failed to create org '{REGISTRY_ORG}': {exc}")
                raise

    # ------------------------------------------------------------------
    def _ensure_apps_org(self, client):
        """Create the `scitex-apps` Gitea organisation for published app forks."""
        from apps.gitea_app.api_client import GiteaAPIError

        try:
            client._request("GET", f"/orgs/{APPS_ORG}")
            self.stdout.write(f"Organisation '{APPS_ORG}' already exists.")
        except GiteaAPIError:
            try:
                client._request(
                    "POST",
                    "/orgs",
                    json={
                        "username": APPS_ORG,
                        "full_name": "SciTeX Apps",
                        "description": (
                            "Published SciTeX apps — canonical forks "
                            "of approved app source repositories"
                        ),
                        "visibility": "public",
                    },
                )
                self.stdout.write(
                    self.style.SUCCESS(f"Created organisation: {APPS_ORG}")
                )
            except GiteaAPIError as exc:
                self.stderr.write(f"Failed to create org '{APPS_ORG}': {exc}")
                raise

        # Add superusers to apps org too
        self._add_superusers_to_org(client, org_name=APPS_ORG)

        # Ensure Django Organization record exists
        self._ensure_django_org()

    # ------------------------------------------------------------------
    def _ensure_django_org(self):
        """Create a Django Organization record for scitex-apps so /<slug>/ works."""
        from apps.organizations_app.models import Organization

        org, created = Organization.objects.get_or_create(
            slug=APPS_ORG,
            defaults={
                "name": "SciTeX Apps",
                "description": (
                    "Published SciTeX apps — canonical forks "
                    "of approved app source repositories"
                ),
            },
        )
        if created:
            self.stdout.write(
                self.style.SUCCESS(f"Created Django Organisation: {APPS_ORG}")
            )
        else:
            self.stdout.write(f"Django Organisation '{APPS_ORG}' exists.")

    # ------------------------------------------------------------------
    def _add_superusers_to_org(self, client, org_name=None):
        """Add Django superusers to an org's Owners team."""
        org = org_name or REGISTRY_ORG
        from django.contrib.auth.models import User

        from apps.gitea_app.api_client import GiteaAPIError

        # Find the Owners team ID
        try:
            teams = client._request("GET", f"/orgs/{org}/teams").json()
            owners_team = next((t for t in teams if t.get("name") == "Owners"), None)
            if not owners_team:
                self.stderr.write("No Owners team found in org")
                return
            team_id = owners_team["id"]
        except (GiteaAPIError, StopIteration):
            return

        for user in User.objects.filter(is_superuser=True):
            try:
                client._request("PUT", f"/teams/{team_id}/members/{user.username}")
                self.stdout.write(f"Added {user.username} to Owners team")
            except GiteaAPIError:
                pass  # user may not exist in Gitea

    # ------------------------------------------------------------------
    def _create_repo(self, client) -> bool:
        """Create `apps` repo under the org.  Returns True if created."""
        from apps.gitea_app.api_client import GiteaAPIError

        try:
            client.get_repository(owner=REGISTRY_ORG, repo=REGISTRY_REPO_NAME)
            self.stdout.write(
                self.style.WARNING(
                    f"Repository {REGISTRY_ORG}/{REGISTRY_REPO_NAME} already exists."
                )
            )
            return False
        except GiteaAPIError:
            pass  # 404 — doesn't exist, proceed

        try:
            repo = client._request(
                "POST",
                f"/orgs/{REGISTRY_ORG}/repos",
                json={
                    "name": REGISTRY_REPO_NAME,
                    "description": REGISTRY_REPO_DESC,
                    "private": False,
                    "auto_init": True,
                    "readme": "Default",
                },
            )
            full_name = repo.json().get(
                "full_name", f"{REGISTRY_ORG}/{REGISTRY_REPO_NAME}"
            )
            self.stdout.write(self.style.SUCCESS(f"Created registry repo: {full_name}"))
            return True
        except GiteaAPIError as exc:
            self.stderr.write(f"Failed to create registry repo: {exc}")
            raise

    # ------------------------------------------------------------------
    def _init_contents(self, client):
        """Populate the repo with an initial README and apps/ directory."""
        from apps.gitea_app.api_client import GiteaAPIError

        readme_content = (
            "# SciTeX Apps Registry\n\n"
            "Central package registry for SciTeX app plugins — "
            "modelled after [MELPA](https://melpa.org/).\n\n"
            "## How it works\n\n"
            "1. Author runs `scitex cloud app submit` (or clicks **Submit** in the web UI)\n"
            "2. A PR is opened here adding `apps/<app-name>.json` with app metadata\n"
            "3. Staff (or community) reviews the PR\n"
            "4. **Merge = approval** — a webhook auto-activates the app on SciTeX Cloud\n"
            "5. **Close without merge = rejection**\n"
        )

        # Create apps/.gitkeep
        try:
            client._request(
                "POST",
                f"/repos/{REGISTRY_ORG}/{REGISTRY_REPO_NAME}/contents/apps/.gitkeep",
                json={
                    "message": "Initialize apps directory",
                    "content": base64.b64encode(b"").decode(),
                },
            )
        except GiteaAPIError as exc:
            logger.warning("apps/.gitkeep init failed (may already exist): %s", exc)

        # Update README
        try:
            existing = client.get_file_contents(
                owner=REGISTRY_ORG,
                repo=REGISTRY_REPO_NAME,
                filepath="README.md",
            )
            sha = existing.get("sha", "")
            client._request(
                "PUT",
                f"/repos/{REGISTRY_ORG}/{REGISTRY_REPO_NAME}/contents/README.md",
                json={
                    "message": "Update README with MELPA-like workflow description",
                    "content": base64.b64encode(readme_content.encode()).decode(),
                    "sha": sha,
                },
            )
            self.stdout.write(
                self.style.SUCCESS("Initialised apps/ directory and README")
            )
        except GiteaAPIError as exc:
            logger.warning("README update failed: %s", exc)
            self.stdout.write(
                self.style.WARNING(f"README update failed (non-critical): {exc}")
            )

    # ------------------------------------------------------------------
    def _ensure_django_project(self):
        """Create a Django Project record for scitex/apps so it shows in Hub."""
        from django.contrib.auth.models import User

        from apps.project_app.models import Project

        # Get or create a system user for the org
        system_user, created = User.objects.get_or_create(
            username=REGISTRY_ORG,
            defaults={"is_active": False, "email": f"{REGISTRY_ORG}@scitex.local"},
        )
        if created:
            system_user.set_unusable_password()
            system_user.save()
            self.stdout.write(
                self.style.SUCCESS(f"Created system user: {REGISTRY_ORG}")
            )

        # Get or create the Project record
        project, created = Project.objects.update_or_create(
            owner=system_user,
            name=REGISTRY_REPO_NAME,
            defaults={
                "slug": REGISTRY_REPO_NAME,
                "description": REGISTRY_REPO_DESC,
                "visibility": "public",
                "project_type": "local",
            },
        )
        if created:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Created Django Project: {REGISTRY_ORG}/{REGISTRY_REPO_NAME}"
                )
            )
        else:
            self.stdout.write(
                f"Django Project {REGISTRY_ORG}/{REGISTRY_REPO_NAME} exists."
            )

    # ------------------------------------------------------------------
    def _register_webhook(self, client):
        """Register a Gitea webhook for pull_request events."""
        from apps.gitea_app.api_client import GiteaAPIError

        django_url = "http://django:8000"
        webhook_url = f"{django_url}/api/apps/webhook/"

        try:
            client._request(
                "POST",
                f"/repos/{REGISTRY_ORG}/{REGISTRY_REPO_NAME}/hooks",
                json={
                    "type": "gitea",
                    "active": True,
                    "events": ["pull_request"],
                    "config": {
                        "url": webhook_url,
                        "content_type": "json",
                        "secret": "",
                    },
                },
            )
            self.stdout.write(self.style.SUCCESS(f"Registered webhook: {webhook_url}"))
        except GiteaAPIError as exc:
            self.stderr.write(
                f"Webhook registration failed (configure manually): {exc}"
            )


# EOF
