#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Registry API views — JWT app submission and Gitea webhook for PR-based review."""

from __future__ import annotations

import base64
import json
import logging

from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from ..models import AppsModule, ModuleSubmission

logger = logging.getLogger(__name__)

REGISTRY_REPO_NAME = "scitex-apps-registry"


# ---------------------------------------------------------------------------
# JWT-authenticated app submission (CLI-facing, CSRF exempt)
# ---------------------------------------------------------------------------


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def api_submit_jwt(request):
    """JWT-authenticated app submission endpoint for CLI.

    Accepts: {"project_name": "...", "manifest": {...}}
    Creates AppsModule + ModuleSubmission + opens PR on central registry.
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

    # Open PR on central registry
    pr_url = _open_registry_pr(
        app_module=app_module,
        manifest=manifest,
        version=version,
        author_username=request.user.username,
        pinned_commit=pinned_commit,
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
# Gitea webhook for PR merge → auto-approval
# ---------------------------------------------------------------------------


@require_http_methods(["POST"])
def api_registry_webhook(request):
    """Gitea webhook handler for PR merge events on the registry repo.

    When a PR is merged in scitex-apps-registry, this activates the
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

    head_branch = pr.get("head", {}).get("ref", "")
    if not head_branch.startswith("submit/"):
        return JsonResponse({"ok": True, "skipped": "not a submit branch"})

    # Parse app name from branch: submit/<app-name>-v<version>
    app_ref = head_branch.removeprefix("submit/")
    parts = app_ref.rsplit("-v", 1)
    app_name = parts[0] if len(parts) == 2 and parts[1] else app_ref

    try:
        app_module = AppsModule.objects.get(module_name=app_name)
    except AppsModule.DoesNotExist:
        return JsonResponse(
            {"ok": False, "error": f"AppsModule '{app_name}' not found"}, status=404
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

    from .api import _activate_approved_app

    now = timezone.now()
    submission.status = "approved"
    submission.reviewed_at = now
    submission.save(update_fields=["status", "reviewed_at"])

    app_module.visibility = "public"
    app_module.is_verified = True
    app_module.save(update_fields=["visibility", "is_verified"])

    _activate_approved_app(app_module)

    return JsonResponse({"ok": True, "approved": app_name, "pr": pr.get("number")})


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _fetch_head_commit(username, repo_slug):
    """Fetch the HEAD commit SHA from the user's Gitea repo."""
    try:
        from apps.gitea_app.api_client import GiteaClient

        client = GiteaClient()
        repo_info = client.get_repository(owner=username, repo=repo_slug)
        default_branch = repo_info.get("default_branch", "main")
        branch_resp = client._request(
            "GET",
            f"/repos/{username}/{repo_slug}/branches/{default_branch}",
        )
        return branch_resp.json().get("commit", {}).get("id", "")
    except Exception:
        return ""


def _open_registry_pr(app_module, manifest, version, author_username, pinned_commit):
    """Open a PR on the central registry repo with app metadata.

    Returns the PR HTML URL, or empty string on failure.
    """
    try:
        from apps.gitea_app.api_client import GiteaClient

        client = GiteaClient()

        admin_resp = client._request("GET", "/user")
        admin_user = admin_resp.json().get("login", "")

        metadata = {
            "name": app_module.module_name,
            "version": version,
            "description": manifest.get("description", ""),
            "category": manifest.get("category", "other"),
            "author": author_username,
            "source_repo": f"{author_username}/{app_module.project.slug}",
            "pinned_commit": pinned_commit,
            "manifest": manifest,
        }
        content_b64 = base64.b64encode(json.dumps(metadata, indent=2).encode()).decode()

        branch_name = f"submit/{app_module.module_name}-v{version}"
        file_path = f"apps/{app_module.module_name}.json"

        # Create branch from main
        try:
            client._request(
                "POST",
                f"/repos/{admin_user}/{REGISTRY_REPO_NAME}/branches",
                json={"new_branch_name": branch_name, "old_branch_name": "main"},
            )
        except Exception:
            pass  # Branch may already exist

        # Create or update metadata file on the branch
        sha = ""
        try:
            existing = client.get_file_contents(
                owner=admin_user,
                repo=REGISTRY_REPO_NAME,
                filepath=file_path,
                ref=branch_name,
            )
            sha = existing.get("sha", "")
        except Exception:
            pass

        if sha:
            client._request(
                "PUT",
                f"/repos/{admin_user}/{REGISTRY_REPO_NAME}/contents/{file_path}",
                json={
                    "message": f"Update {app_module.module_name} v{version}",
                    "content": content_b64,
                    "branch": branch_name,
                    "sha": sha,
                },
            )
        else:
            client._request(
                "POST",
                f"/repos/{admin_user}/{REGISTRY_REPO_NAME}/contents/{file_path}",
                json={
                    "message": f"Add {app_module.module_name} v{version}",
                    "content": content_b64,
                    "branch": branch_name,
                },
            )

        # Open PR
        pr_resp = client._request(
            "POST",
            f"/repos/{admin_user}/{REGISTRY_REPO_NAME}/pulls",
            json={
                "title": f"[App] {app_module.module_name} v{version}",
                "body": (
                    f"**App:** {app_module.module_name}\n"
                    f"**Version:** {version}\n"
                    f"**Author:** {author_username}\n"
                    f"**Description:** {manifest.get('description', '')}\n\n"
                    f"Source: `{author_username}/{app_module.project.slug}`\n"
                    f"Pinned commit: `{pinned_commit[:12]}`"
                ),
                "head": branch_name,
                "base": "main",
            },
        )
        return pr_resp.json().get("html_url", "")

    except Exception as exc:
        logger.warning(
            "Failed to open registry PR for %s: %s",
            app_module.module_name,
            exc,
        )
        return ""


# EOF
