#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Management command to create the central app registry repo on Gitea."""

from __future__ import annotations

import logging

from django.core.management.base import BaseCommand

logger = logging.getLogger(__name__)

REGISTRY_REPO_NAME = "scitex-apps-registry"
REGISTRY_REPO_DESC = "Central registry for SciTeX app submissions and reviews"


class Command(BaseCommand):
    help = "Create the scitex-apps-registry repo on Gitea (one-time setup)"

    def handle(self, *args, **options):
        from apps.gitea_app.api_client import GiteaAPIError, GiteaClient

        client = GiteaClient()

        # Determine the admin owner (the Gitea token owner)
        try:
            resp = client._request("GET", "/user")
            admin_user = resp.json().get("login", "")
        except GiteaAPIError as exc:
            self.stderr.write(f"Cannot determine Gitea admin user: {exc}")
            return

        self.stdout.write(f"Gitea admin user: {admin_user}")

        # Check if repo already exists
        try:
            client.get_repository(owner=admin_user, repo=REGISTRY_REPO_NAME)
            self.stdout.write(
                self.style.WARNING(
                    f"Repository {admin_user}/{REGISTRY_REPO_NAME} already exists."
                )
            )
            return
        except GiteaAPIError:
            pass  # 404 = doesn't exist, proceed to create

        # Create the registry repo
        try:
            repo = client.create_repository(
                name=REGISTRY_REPO_NAME,
                description=REGISTRY_REPO_DESC,
                private=False,
                auto_init=True,
                readme="Default",
            )
            self.stdout.write(
                self.style.SUCCESS(
                    f"Created registry repo: {repo.get('full_name', REGISTRY_REPO_NAME)}"
                )
            )
        except GiteaAPIError as exc:
            self.stderr.write(f"Failed to create registry repo: {exc}")
            return

        # Add initial apps/ directory with a placeholder README
        try:
            import base64

            readme_content = (
                "# SciTeX Apps Registry\n\n"
                "Each app submission creates a PR adding an "
                "`apps/<app-name>.json` metadata file.\n\n"
                "- **Pending**: PR open, awaiting review\n"
                "- **Approved**: PR merged by admin\n"
                "- **Rejected**: PR closed without merge\n"
            )
            client._request(
                "POST",
                f"/repos/{admin_user}/{REGISTRY_REPO_NAME}/contents/apps/.gitkeep",
                json={
                    "message": "Initialize apps directory",
                    "content": base64.b64encode(b"").decode(),
                },
            )
            # Update the repo README with registry info
            # First get current README to obtain its SHA
            try:
                existing = client.get_file_contents(
                    owner=admin_user,
                    repo=REGISTRY_REPO_NAME,
                    filepath="README.md",
                )
                sha = existing.get("sha", "")
                client._request(
                    "PUT",
                    f"/repos/{admin_user}/{REGISTRY_REPO_NAME}/contents/README.md",
                    json={
                        "message": "Update README with registry description",
                        "content": base64.b64encode(readme_content.encode()).decode(),
                        "sha": sha,
                    },
                )
            except GiteaAPIError:
                pass  # README update is best-effort

            self.stdout.write(self.style.SUCCESS("Initialized apps/ directory"))
        except GiteaAPIError as exc:
            self.stdout.write(
                self.style.WARNING(
                    f"Registry repo created but directory init failed: {exc}"
                )
            )

        # Register a webhook for PR merge events
        try:
            from django.conf import settings

            server_url = getattr(settings, "SCITEX_CLOUD_GITEA_URL", "")
            # The webhook target is the Django server (inside Docker network)
            django_url = "http://django:8000"
            webhook_url = f"{django_url}/api/apps/webhook/"

            client._request(
                "POST",
                f"/repos/{admin_user}/{REGISTRY_REPO_NAME}/hooks",
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
            self.stdout.write(
                self.style.WARNING(
                    f"Webhook registration failed (configure manually): {exc}"
                )
            )


# EOF
