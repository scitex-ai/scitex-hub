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


class Command(BaseCommand):
    help = "Create the scitex/apps registry repo on Gitea (one-time setup)"

    def handle(self, *args, **options):
        from apps.gitea_app.api_client import GiteaClient

        client = GiteaClient()

        # ── 1. Ensure the `scitex` organisation exists ──────────────────
        self._ensure_org(client)

        # ── 1b. Add superusers to org Owners team ─────────────────────
        self._add_superusers_to_org(client)

        # ── 2. Create the `apps` repo under the org ─────────────────────
        if not self._create_repo(client):
            return  # repo already exists or creation failed

        # ── 3. Initialise `apps/` directory + README ────────────────────
        self._init_contents(client)

        # ── 4. Register webhook for PR-merge events ─────────────────────
        self._register_webhook(client)

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
    def _add_superusers_to_org(self, client):
        """Add Django superusers to the scitex org Owners team."""
        from django.contrib.auth.models import User

        from apps.gitea_app.api_client import GiteaAPIError

        # Find the Owners team ID
        try:
            teams = client._request("GET", f"/orgs/{REGISTRY_ORG}/teams").json()
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
