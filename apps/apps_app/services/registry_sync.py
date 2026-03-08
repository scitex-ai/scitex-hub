#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Sync scitex-apps Gitea org data into Django models.

Ensures Django User, Project, and PullRequest records exist so that
app submission PRs can be viewed on the platform's built-in PR pages
(not on external Gitea).
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

APPS_ORG = "scitex-apps"


def sync_app_pr_to_django(
    repo_slug: str, pr_number: int, pr_data: dict, author_username: str
) -> None:
    """Ensure Django User, Project, and PullRequest records exist for the app PR.

    This allows the platform's built-in PR page at
    /<APPS_ORG>/<repo>/pull/<pr_number>/ to display the review.
    """
    from django.conf import settings
    from django.contrib.auth.models import User

    from apps.project_app.models import Project
    from apps.project_app.models.pull_requests.pull_request import PullRequest

    try:
        # 1. Ensure scitex-apps system user exists
        org_user, _ = User.objects.get_or_create(
            username=APPS_ORG,
            defaults={
                "first_name": "SciTeX Apps",
                "is_active": False,  # Not a real login account
            },
        )

        # 2. Ensure Django Project record for the scitex-apps/<repo>
        project, _ = Project.objects.get_or_create(
            owner=org_user,
            slug=repo_slug,
            defaults={
                "name": repo_slug,
                "description": f"SciTeX app: {repo_slug}",
                "gitea_repo_url": f"{settings.GITEA_URL}/{APPS_ORG}/{repo_slug}",
            },
        )

        # 3. Ensure PullRequest record
        author_user = User.objects.filter(username=author_username).first()
        head_info = pr_data.get("head") or {}
        base_info = pr_data.get("base") or {}
        PullRequest.objects.update_or_create(
            project=project,
            number=pr_number,
            defaults={
                "title": pr_data.get("title", f"App submission #{pr_number}"),
                "description": pr_data.get("body", ""),
                "author": author_user or org_user,
                "source_branch": head_info.get("label", "submit"),
                "target_branch": base_info.get("label", "main"),
                "state": "open",
            },
        )
    except Exception as e:
        logger.warning("[registry_sync] Failed to sync PR to Django: %s", e)


def find_existing_pr_url(repo_slug: str) -> str | None:
    """Find an existing open PR for an app in scitex-apps and return platform URL.

    Returns platform-relative URL (e.g., /scitex-apps/<repo>/pull/<n>/).
    """
    from apps.gitea_app.api_client import GiteaClient

    try:
        client = GiteaClient()
        prs = client.list_pull_requests(owner=APPS_ORG, repo=repo_slug, state="open")
        if prs:
            pr_number = prs[0].get("number")
            if pr_number:
                return f"/{APPS_ORG}/{repo_slug}/pull/{pr_number}/"
    except Exception as e:
        logger.warning("[registry_sync] Failed to find existing PR: %s", e)
    return None


def ensure_registry_read_access(owner: str, repo: str) -> None:
    """Grant read access to the submitter on scitex-apps/<repo>."""
    from apps.gitea_app.api_client import GiteaClient

    try:
        client = GiteaClient()
        client.add_collaborator(
            owner=APPS_ORG, repo=repo, username=owner, permission="read"
        )
    except Exception as e:
        logger.warning(
            "[registry_sync] Failed to grant read access to %s: %s", owner, e
        )


def ensure_scitex_apps_org_membership(username: str) -> None:
    """Ensure scitex-apps Organization exists and add user as a member.

    Called after successful app submission so the submitter appears as a
    member of the scitex-apps organization in their profile sidebar.
    """
    from django.contrib.auth.models import User

    from apps.organizations_app.models import Organization, OrganizationMembership

    try:
        org, _ = Organization.objects.get_or_create(
            slug=APPS_ORG,
            defaults={
                "name": "SciTeX Apps",
                "description": "Official SciTeX app registry organization.",
            },
        )
        user = User.objects.filter(username=username).first()
        if user:
            OrganizationMembership.objects.get_or_create(
                user=user,
                organization=org,
                defaults={"role": "member"},
            )
    except Exception as e:
        logger.warning(
            "[registry_sync] Failed to ensure org membership for %s: %s", username, e
        )


# EOF
