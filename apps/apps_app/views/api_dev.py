#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Dev install API — install/uninstall app repos from the Hub as personal dev apps.

Dev apps are personal workspace tabs that load live from source repos.
No approval needed. Only the installing user sees the tab.
"""

from __future__ import annotations

import logging

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from ..models import DevInstallation
from ..services.dev_app_loader import (
    read_manifest,
    resolve_dev_project_dir,
    validate_dev_repo,
)

logger = logging.getLogger(__name__)


@login_required
@require_POST
def api_dev_install(request):
    """Install a Hub repo as a personal dev app.

    POST body: {"owner": "...", "repo": "..."}
    Creates a DevInstallation record. The app tab appears in the workspace
    on next page load.
    """
    import json

    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({"success": False, "error": "Invalid JSON"}, status=400)

    owner = data.get("owner", "").strip()
    repo = data.get("repo", "").strip()

    if not owner or not repo:
        return JsonResponse(
            {"success": False, "error": "owner and repo are required"}, status=400
        )

    # Check if already installed
    if DevInstallation.objects.filter(
        user=request.user, source_owner=owner, source_repo=repo
    ).exists():
        return JsonResponse(
            {"success": False, "error": "Already installed as dev app"}, status=409
        )

    # Check repo accessibility
    if not _can_access_repo(request.user, owner, repo):
        return JsonResponse(
            {"success": False, "error": "Repository not accessible"}, status=403
        )

    # Validate repo has templates
    is_valid, error = validate_dev_repo(owner, repo)
    if not is_valid:
        return JsonResponse({"success": False, "error": error}, status=400)

    # Read manifest for metadata
    project_dir = resolve_dev_project_dir(owner, repo)
    manifest = read_manifest(project_dir) if project_dir else {}

    module_name = f"dev__{owner}__{repo}"

    dev_install = DevInstallation.objects.create(
        user=request.user,
        source_owner=owner,
        source_repo=repo,
        module_name=module_name,
        label=manifest.get("label", repo.replace("-", " ").replace("_", " ").title()),
        icon=manifest.get("icon", "fas fa-puzzle-piece"),
        description=manifest.get("description", ""),
    )

    logger.info(
        "[api_dev] User %s installed dev app %s/%s",
        request.user.username,
        owner,
        repo,
    )

    return JsonResponse(
        {
            "success": True,
            "module_name": dev_install.module_name,
            "label": dev_install.label,
            "icon": dev_install.icon,
        }
    )


@login_required
@require_POST
def api_dev_uninstall(request, owner, repo):
    """Uninstall a dev app.

    POST /apps/api/dev/<owner>/<repo>/uninstall/
    Deletes the DevInstallation record.
    """
    deleted, _ = DevInstallation.objects.filter(
        user=request.user, source_owner=owner, source_repo=repo
    ).delete()

    if not deleted:
        return JsonResponse(
            {"success": False, "error": "Dev app not found"}, status=404
        )

    logger.info(
        "[api_dev] User %s uninstalled dev app %s/%s",
        request.user.username,
        owner,
        repo,
    )

    return JsonResponse({"success": True})


@login_required
def api_dev_app_url(request):
    """Return the workspace URL for a dev app given a project slug.

    GET /apps/api/dev/url/?project_id=<slug>
    Returns: {"success": true, "url": "/dev__<owner>__<repo>/", "module_name": "..."}
    """
    project_id = request.GET.get("project_id", "").strip()
    if not project_id:
        return JsonResponse(
            {"success": False, "error": "project_id required"}, status=400
        )

    dev_install = DevInstallation.objects.filter(
        user=request.user,
        source_repo=project_id,
    ).first()

    if not dev_install:
        return JsonResponse(
            {"success": False, "error": "No dev installation for this project"},
            status=404,
        )

    rest = dev_install.module_name.removeprefix("dev__")
    url = f"/dev__{rest}/"

    return JsonResponse(
        {
            "success": True,
            "url": url,
            "module_name": dev_install.module_name,
        }
    )


def _can_access_repo(user, owner, repo) -> bool:
    """Check if user can access the repo via Gitea.

    Access is granted if:
    - The repo is public, OR
    - The user is the owner, OR
    - The user is a collaborator
    """
    try:
        from apps.gitea_app.api_client import GiteaClient

        client = GiteaClient()
        repo_info = client.get_repository(owner=owner, repo=repo)

        # Public repos are accessible to anyone
        if not repo_info.get("private", True):
            return True

        # Owner can always access
        if owner == user.username:
            return True

        # Check collaborator access
        try:
            client._request(
                "GET",
                f"/repos/{owner}/{repo}/collaborators/{user.username}",
            )
            return True
        except Exception:
            return False

    except Exception:
        # If Gitea is down or repo doesn't exist, deny
        return False


# EOF
