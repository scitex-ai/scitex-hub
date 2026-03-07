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


@login_required
@require_POST
def api_submit_dev_app(request, owner, repo):
    """Submit a dev app to the App Store via registry PR.

    POST /apps/api/dev/<owner>/<repo>/submit/
    Validates the app, creates an AppsModule record, opens a PR on scitex/apps.
    """
    import subprocess

    from apps.project_app.models import Project

    from ..models import AppsModule, ModuleSubmission
    from .api_registry import _open_registry_pr

    # 1. Verify user owns this dev installation
    dev_install = DevInstallation.objects.filter(
        user=request.user, source_owner=owner, source_repo=repo
    ).first()
    if not dev_install:
        return JsonResponse(
            {"success": False, "error": "Dev app not found"}, status=404
        )

    # 2. Resolve project directory
    project_dir = resolve_dev_project_dir(owner, repo)
    if not project_dir or not project_dir.exists():
        return JsonResponse(
            {"success": False, "error": "Project directory not found"}, status=404
        )

    # 3. Read and validate manifest
    manifest = read_manifest(project_dir)
    if not manifest:
        return JsonResponse(
            {"success": False, "error": "manifest.json not found or invalid"},
            status=400,
        )

    # 4. Run validation
    from scitex_cloud.app_tools import validate

    errors = validate(str(project_dir))
    if errors:
        return JsonResponse(
            {"success": False, "error": "Validation failed", "errors": errors},
            status=400,
        )

    # 5. Look up Django Project record
    project = Project.objects.filter(owner__username=owner, slug=repo).first()
    if not project:
        return JsonResponse(
            {"success": False, "error": f"Project '{owner}/{repo}' not found"},
            status=404,
        )

    # 6. Create or update AppsModule record
    app_name = manifest.get("slug") or manifest.get("name") or repo.replace("-", "_")
    module_name = (
        app_name
        if (app_name.endswith("_app") or app_name.endswith("-app"))
        else f"{app_name}_app"
    )

    app_module, created = AppsModule.objects.update_or_create(
        module_name=module_name,
        defaults={
            "author": request.user,
            "short_description": manifest.get("description", ""),
            "category": manifest.get("category", "other"),
            "visibility": "private",
            "project": project,
            "repository_url": project.gitea_repo_url or "",
        },
    )

    # 7. Get pinned commit
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(project_dir),
            capture_output=True,
            text=True,
            timeout=10,
        )
        pinned_commit = result.stdout.strip() or "unknown"
    except Exception:
        pinned_commit = "unknown"

    # 8. Open registry PR
    try:
        pr_url = _open_registry_pr(
            app_module=app_module,
            manifest=manifest,
            version=manifest.get("version", "0.1.0"),
            author_username=owner,
            pinned_commit=pinned_commit,
        )
    except Exception as e:
        logger.error("[api_dev] Failed to open registry PR: %s", e)
        return JsonResponse(
            {"success": False, "error": f"Failed to open registry PR: {e}"},
            status=500,
        )

    # 9. Create submission record
    ModuleSubmission.objects.create(
        module=app_module,
        submitted_by=request.user,
        pr_url=pr_url,
    )

    logger.info(
        "[api_dev] User %s submitted dev app %s/%s → PR: %s",
        request.user.username,
        owner,
        repo,
        pr_url,
    )

    return JsonResponse({"success": True, "pr_url": pr_url})


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
