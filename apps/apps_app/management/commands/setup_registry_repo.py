#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Management command to set up the scitex-apps org and webhook on Gitea.

Creates the ``scitex`` and ``scitex-apps`` organisations.  Registers an
org-level webhook on ``scitex-apps`` so that every merged PR across any
repo in the org triggers app activation.

Reverse-fork model:
  1. ``scitex-apps/<app>`` is created from a scaffold template
  2. Users fork to ``user/<app>`` and develop
  3. Users PR back to ``scitex-apps/<app>``
  4. Merge = approval (via org-level webhook)
"""

from __future__ import annotations

import logging

from django.core.management.base import BaseCommand

logger = logging.getLogger(__name__)

SCITEX_ORG = "scitex"
APPS_ORG = "scitex-apps"


class Command(BaseCommand):
    help = "Set up scitex-apps org and webhook on Gitea (one-time setup)"

    def handle(self, *args, **options):
        from apps.gitea_app.api_client import GiteaClient

        client = GiteaClient()

        # 1. Ensure the `scitex` organisation exists
        self._ensure_org(
            client,
            SCITEX_ORG,
            "SciTeX",
            "SciTeX open-source scientific research platform",
        )
        self._add_superusers_to_org(client, SCITEX_ORG)

        # 2. Ensure the `scitex-apps` organisation exists
        self._ensure_org(
            client,
            APPS_ORG,
            "SciTeX Apps",
            "SciTeX app repositories — fork, develop, PR back",
        )
        self._add_superusers_to_org(client, APPS_ORG)

        # 3. Ensure Django Organization record for scitex-apps
        self._ensure_django_org()

        # 4. Register org-level webhook on scitex-apps (PR merge → app approval)
        self._register_org_webhook(client)

        # 5. Register org-level sync webhook on scitex-apps (member events → Django)
        self._register_sync_webhook(client, APPS_ORG)

        # 6. Register org-level sync webhook on scitex (member events → Django)
        self._register_sync_webhook(client, SCITEX_ORG)

    # ------------------------------------------------------------------
    def _ensure_org(self, client, org_name, full_name, description):
        """Create a Gitea organisation if it doesn't exist."""
        from apps.gitea_app.api_client import GiteaAPIError

        try:
            client.get_organization(org_name)
            self.stdout.write(f"Organisation '{org_name}' already exists.")
        except GiteaAPIError:
            try:
                client.create_organization(
                    org_name,
                    full_name=full_name,
                    description=description,
                    visibility="public",
                )
                self.stdout.write(
                    self.style.SUCCESS(f"Created organisation: {org_name}")
                )
            except GiteaAPIError as exc:
                self.stderr.write(f"Failed to create org '{org_name}': {exc}")
                raise

    # ------------------------------------------------------------------
    def _ensure_django_org(self):
        """Create a Django Organization record for scitex-apps."""
        from apps.organizations_app.models import Organization

        org, created = Organization.objects.get_or_create(
            slug=APPS_ORG,
            defaults={
                "name": "SciTeX Apps",
                "description": "SciTeX app repositories — fork, develop, PR back",
            },
        )
        if created:
            self.stdout.write(
                self.style.SUCCESS(f"Created Django Organisation: {APPS_ORG}")
            )
        else:
            self.stdout.write(f"Django Organisation '{APPS_ORG}' exists.")

    # ------------------------------------------------------------------
    def _add_superusers_to_org(self, client, org_name):
        """Add Django superusers to an org's Owners team."""
        from django.contrib.auth.models import User

        from apps.gitea_app.api_client import GiteaAPIError

        try:
            teams = client.list_org_teams(org_name)
            owners_team = next((t for t in teams if t.get("name") == "Owners"), None)
            if not owners_team:
                self.stderr.write(f"No Owners team found in {org_name}")
                return
            team_id = owners_team["id"]
        except (GiteaAPIError, StopIteration):
            return

        for user in User.objects.filter(is_superuser=True):
            try:
                client.add_team_member(team_id, user.username)
                self.stdout.write(f"Added {user.username} to {org_name} Owners")
            except GiteaAPIError:
                pass  # user may not exist in Gitea

    # ------------------------------------------------------------------
    def _register_org_webhook(self, client):
        """Register an org-level webhook on scitex-apps for PR events.

        Idempotent: skips if a webhook with the same URL already exists.
        """
        from apps.gitea_app.api_client import GiteaAPIError

        django_url = "http://django:8000"
        webhook_url = f"{django_url}/api/apps/webhook/"

        # Check for existing webhook to avoid duplicates
        try:
            hooks = client.list_org_webhooks(APPS_ORG)
            for hook in hooks:
                if hook.get("config", {}).get("url") == webhook_url:
                    self.stdout.write(f"Org webhook already registered: {webhook_url}")
                    return
        except GiteaAPIError:
            pass  # no hooks yet, proceed

        try:
            client.create_org_webhook(
                org=APPS_ORG,
                url=webhook_url,
                events=["pull_request"],
                content_type="json",
                secret="",
                active=True,
            )
            self.stdout.write(
                self.style.SUCCESS(f"Registered org webhook: {webhook_url}")
            )
        except GiteaAPIError as exc:
            self.stderr.write(f"Org webhook registration failed: {exc}")

    # ------------------------------------------------------------------
    def _register_sync_webhook(self, client, org_name: str):
        """Register a member-sync webhook on an org (Gitea → Django).

        Idempotent: skips if a webhook with the same URL already exists.
        """
        from apps.gitea_app.api_client import GiteaAPIError

        django_url = "http://django:8000"
        webhook_url = f"{django_url}/api/gitea/webhook/sync/"

        try:
            hooks = client.list_org_webhooks(org_name)
            for hook in hooks:
                if hook.get("config", {}).get("url") == webhook_url:
                    self.stdout.write(
                        f"Sync webhook already registered on {org_name}: {webhook_url}"
                    )
                    return
        except GiteaAPIError:
            pass  # no hooks yet, proceed

        try:
            client.create_org_webhook(
                org=org_name,
                url=webhook_url,
                events=["member"],
                content_type="json",
                active=True,
            )
            self.stdout.write(
                self.style.SUCCESS(
                    f"Registered sync webhook on {org_name}: {webhook_url}"
                )
            )
        except GiteaAPIError as exc:
            self.stderr.write(f"Sync webhook registration failed on {org_name}: {exc}")


# EOF
