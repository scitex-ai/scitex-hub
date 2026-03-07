#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Registry API views — reverse-fork app submission and org-level webhook.

Reverse-fork model:
  1. ``_create_app_repo()`` creates a scaffold repo in ``scitex-apps/<app>``
  2. User forks it to ``user/<app>`` and develops
  3. ``_submit_app_pr()`` opens a cross-repo PR: ``user/<app>`` -> ``scitex-apps/<app>``
  4. Merge = approval (via org-level webhook on ``scitex-apps``)
"""

from __future__ import annotations

import json
import logging

from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from ..models import AppsModule, ModuleSubmission

logger = logging.getLogger(__name__)

APPS_ORG = "scitex-apps"


# ---------------------------------------------------------------------------
# JWT-authenticated app submission (CLI-facing, CSRF exempt)
# ---------------------------------------------------------------------------


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def api_submit_jwt(request):
    """JWT-authenticated app submission endpoint for CLI.

    Accepts: {"project_name": "...", "manifest": {...}}
    Creates AppsModule + ModuleSubmission + opens cross-repo PR.
    """
    project_name = request.data.get("project_name", "").strip()
    manifest = request.data.get("manifest", {})

    if not project_name:
        return Response(
            {"success": False, "error": "project_name is required"}, status=400
        )

    from apps.project_app.models import Project

    project = Project.objects.filter(name=project_name, owner=request.user).first()
    if not project:
        return Response(
            {"success": False, "error": f"Project '{project_name}' not found"},
            status=404,
        )

    module_name = manifest.get("name", project.slug)
    version = manifest.get("version", "0.1.0")

    # Fetch HEAD commit SHA from author's Gitea repo
    pinned_commit = _fetch_head_commit(request.user.username, project.slug)

    # Create or update AppsModule
    app_module, _created = AppsModule.objects.update_or_create(
        module_name=module_name,
        defaults={
            "author": request.user,
            "project": project,
            "short_description": manifest.get("description", ""),
            "category": manifest.get("category", "other"),
            "visibility": "private",
            "pinned_commit": pinned_commit,
        },
    )

    # Reject if already pending
    if ModuleSubmission.objects.filter(module=app_module, status="pending").exists():
        return Response(
            {"success": False, "error": "A submission is already pending review."},
            status=400,
        )

    # Open cross-repo PR: user/<app> -> scitex-apps/<app>
    pr_url = _submit_app_pr(
        app_module=app_module,
        version=version,
    )

    submission = ModuleSubmission.objects.create(
        module=app_module,
        submitted_by=request.user,
        pr_url=pr_url,
    )

    return Response(
        {
            "success": True,
            "message": f"Submitted {module_name} for review.",
            "pr_url": pr_url,
            "submission_id": submission.pk,
        },
        status=201,
    )


# ---------------------------------------------------------------------------
# Org-level Gitea webhook for PR merge -> auto-approval
# ---------------------------------------------------------------------------


@require_http_methods(["POST"])
def api_registry_webhook(request):
    """Org-level webhook handler for PR merge events on scitex-apps repos.

    When a PR is merged in any scitex-apps/<repo>, this activates the
    corresponding app (sets visibility=public, is_verified=True).
    """
    try:
        payload = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    action = payload.get("action")
    pr = payload.get("pull_request", {})
    is_merged = pr.get("merged", False)

    if action != "closed" or not is_merged:
        return JsonResponse({"ok": True, "skipped": "not a merge event"})

    # Extract repo name from the webhook payload
    repo_name = payload.get("repository", {}).get("name", "")
    if not repo_name:
        return JsonResponse({"ok": True, "skipped": "no repository name"})

    try:
        app_module = AppsModule.objects.get(module_name=repo_name)
    except AppsModule.DoesNotExist:
        return JsonResponse(
            {"ok": False, "error": f"AppsModule '{repo_name}' not found"}, status=404
        )

    submission = (
        ModuleSubmission.objects.filter(module=app_module, status="pending")
        .order_by("-submitted_at")
        .first()
    )
    if not submission:
        return JsonResponse(
            {"ok": False, "error": "No pending submission found"}, status=404
        )

    # Approve
    from django.utils import timezone

    from .api_submission import _activate_approved_app

    now = timezone.now()
    submission.status = "approved"
    submission.reviewed_at = now
    submission.save(update_fields=["status", "reviewed_at"])

    app_module.visibility = "public"
    app_module.is_verified = True
    app_module.registry_repo_url = f"/{APPS_ORG}/{repo_name}/"
    app_module.save(update_fields=["visibility", "is_verified", "registry_repo_url"])

    _activate_approved_app(app_module)

    pr_number = pr.get("number")
    return JsonResponse({"ok": True, "approved": repo_name, "pr": pr_number})


# ---------------------------------------------------------------------------
# Scaffold repo creation
# ---------------------------------------------------------------------------


def _create_app_repo(app_name: str, description: str = "") -> str:
    """Create a scaffold repo in scitex-apps org for a new app.

    Returns the repo HTML URL.  Raises on failure.
    """
    from apps.gitea_app.api_client import GiteaAPIError, GiteaClient

    client = GiteaClient()

    # Check if repo already exists
    try:
        existing = client.get_repository(owner=APPS_ORG, repo=app_name)
        return existing.get("html_url", f"/{APPS_ORG}/{app_name}/")
    except GiteaAPIError:
        pass  # 404 — doesn't exist, create it

    # Create repo in org
    repo_data = client.create_org_repository(
        org=APPS_ORG,
        name=app_name,
        description=description or f"SciTeX app: {app_name}",
        private=False,
        auto_init=True,
    )
    repo_url = repo_data.get("html_url", "")

    # Commit scaffold files
    _commit_scaffold_files(client, app_name)

    return repo_url


def _commit_scaffold_files(client, app_name: str) -> None:
    """Commit scaffold template files to the new app repo."""
    from apps.gitea_app.api_client import GiteaAPIError

    scaffold_files = {
        "manifest.json": json.dumps(
            {
                "name": app_name,
                "version": "0.1.0",
                "description": f"SciTeX app: {app_name}",
                "category": "other",
                "author": "",
                "entry_template": "templates/index_partial.html",
            },
            indent=2,
        ),
        "templates/index_partial.html": (
            f"{{% comment %}}Scaffold for {app_name}{{% endcomment %}}\n"
            '<div class="app-container">\n'
            f"  <h2>{app_name}</h2>\n"
            "  <p>Replace this with your app content.</p>\n"
            "</div>\n"
        ),
        "skill.py": (
            f'"""Skill module for {app_name}."""\n\n\n# Add your skill functions here\n'
        ),
        "README.md": (
            f"# {app_name}\n\n"
            f"SciTeX app scaffold. Fork this repo, develop your app, "
            f"and submit a PR back to publish.\n"
        ),
    }

    for filepath, content in scaffold_files.items():
        try:
            client.create_file(
                owner=APPS_ORG,
                repo=app_name,
                filepath=filepath,
                content=content,
                message=f"Add scaffold: {filepath}",
            )
        except GiteaAPIError as exc:
            logger.warning("Failed to create %s in %s: %s", filepath, app_name, exc)


# ---------------------------------------------------------------------------
# Cross-repo PR submission
# ---------------------------------------------------------------------------


def _submit_app_pr(app_module, version: str) -> str:
    """Open a cross-repo PR: author's fork -> scitex-apps/<repo>.

    Returns the PR HTML URL.  Raises on failure.
    """
    from apps.gitea_app.api_client import GiteaClient

    client = GiteaClient()
    repo = app_module.project.slug
    author = app_module.project.owner.username

    pr_data = client.create_pull_request(
        owner=APPS_ORG,
        repo=repo,
        title=f"[App] {app_module.module_name} v{version}",
        body=(
            f"**App:** {app_module.module_name}\n"
            f"**Version:** {version}\n"
            f"**Author:** {author}\n"
            f"**Description:** {app_module.short_description}\n\n"
            f"Source: `{author}/{repo}`\n"
            f"Pinned commit: `{app_module.pinned_commit[:12] if app_module.pinned_commit else 'N/A'}`"
        ),
        head=f"{author}:main",
        base="main",
    )
    pr_url = pr_data.get("html_url", "")
    if not pr_url:
        raise RuntimeError(
            f"PR created but no html_url returned for {app_module.module_name}"
        )

    return pr_url


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _fetch_head_commit(username: str, repo_slug: str) -> str:
    """Fetch the HEAD commit SHA from the user's Gitea repo."""
    from apps.gitea_app.api_client import GiteaClient

    client = GiteaClient()
    repo_info = client.get_repository(owner=username, repo=repo_slug)
    default_branch = repo_info.get("default_branch", "main")
    branch_data = client.get_branch(username, repo_slug, default_branch)
    commit_sha = branch_data.get("commit", {}).get("id", "")
    if not commit_sha:
        raise RuntimeError(f"Could not resolve HEAD commit for {username}/{repo_slug}")
    return commit_sha


# ---------------------------------------------------------------------------
# Gitea PR actions (used by staff review endpoints)
# ---------------------------------------------------------------------------


def merge_app_pr(pr_url: str, app_repo: str) -> None:
    """Merge a PR on a scitex-apps repo via Gitea API."""
    pr_number = _extract_pr_number(pr_url)
    if not pr_number:
        raise ValueError(f"Cannot extract PR number from: {pr_url}")

    from apps.gitea_app.api_client import GiteaClient

    client = GiteaClient()
    client.merge_pull_request(APPS_ORG, app_repo, pr_number)


def close_app_pr(pr_url: str, app_repo: str, comment: str = "") -> None:
    """Close a PR on a scitex-apps repo (rejection)."""
    pr_number = _extract_pr_number(pr_url)
    if not pr_number:
        raise ValueError(f"Cannot extract PR number from: {pr_url}")

    from apps.gitea_app.api_client import GiteaClient

    client = GiteaClient()

    if comment:
        client.comment_on_issue(APPS_ORG, app_repo, pr_number, comment)

    client.close_pull_request(APPS_ORG, app_repo, pr_number)


def comment_on_app_pr(pr_url: str, app_repo: str, comment: str) -> None:
    """Add a review comment on an app PR."""
    pr_number = _extract_pr_number(pr_url)
    if not pr_number:
        raise ValueError(f"Cannot extract PR number from: {pr_url}")

    from apps.gitea_app.api_client import GiteaClient

    client = GiteaClient()
    client.comment_on_issue(APPS_ORG, app_repo, pr_number, comment)


def _extract_pr_number(pr_url: str) -> str | None:
    """Extract PR number from a Gitea PR URL like .../pulls/42."""
    if not pr_url:
        return None
    parts = pr_url.rstrip("/").split("/")
    if len(parts) >= 2 and parts[-2] == "pulls":
        return parts[-1]
    return None


# EOF
