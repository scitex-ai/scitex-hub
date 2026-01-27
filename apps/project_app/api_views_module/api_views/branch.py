#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""API views for branch switching."""

from __future__ import annotations

import json
import logging
import subprocess

from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_http_methods

from apps.project_app.models import Project

from .utils import error_response

logger = logging.getLogger(__name__)


@login_required
@require_http_methods(["POST"])
def api_switch_branch(request, username, slug):
    """
    API endpoint to switch the current branch for file browsing.

    This does NOT actually run `git checkout` - it only updates the session
    to read files from the selected branch using `git show branch:path`.
    """
    user = get_object_or_404(User, username=username)
    project = get_object_or_404(Project, slug=slug, owner=user)

    has_access = (
        project.owner == request.user
        or project.collaborators.filter(id=request.user.id).exists()
        or getattr(project, "visibility", None) == "public"
    )

    if not has_access:
        return error_response("Permission denied", status=403)

    try:
        data = json.loads(request.body)
        branch_name = data.get("branch", "").strip()

        if not branch_name:
            return error_response("Branch name is required", status=400)

        project_path = _get_project_path(project)
        if not project_path:
            return error_response("Project directory not found", status=404)

        branches = _list_branches(project_path)
        if branches is None:
            return error_response("Failed to list branches", status=500)

        if branch_name not in branches:
            return error_response(
                f"Branch '{branch_name}' not found. Available: {', '.join(branches)}",
                status=404,
            )

        session_key = f"project_{project.id}_branch"
        request.session[session_key] = branch_name

        logger.info(
            f"Switched branch for project {project.slug} to {branch_name} "
            f"(user: {request.user.username})"
        )

        return JsonResponse(
            {
                "success": True,
                "branch": branch_name,
                "message": f"Switched to branch '{branch_name}'",
            }
        )

    except json.JSONDecodeError:
        return error_response("Invalid JSON in request body", status=400)
    except subprocess.TimeoutExpired:
        return error_response("Git command timed out", status=500)
    except Exception as e:
        logger.error(f"Error switching branch: {e}")
        return JsonResponse({"success": False, "error": str(e)}, status=500)


def get_current_branch_from_session(request, project):
    """
    Helper function to get the current branch from session.

    Returns the session-stored branch for this project, or the repository's
    current branch if not set in session.
    """
    session_key = f"project_{project.id}_branch"

    if session_key in request.session:
        return request.session[session_key]

    project_path = _get_project_path(project)
    if not project_path:
        return "main"

    try:
        result = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=project_path,
            capture_output=True,
            text=True,
            timeout=5,
        )

        if result.returncode == 0 and result.stdout.strip():
            branch = result.stdout.strip()
            request.session[session_key] = branch
            return branch

    except Exception as e:
        logger.debug(f"Error getting current branch: {e}")

    return "main"


def _get_project_path(project):
    """Get the filesystem path for a project."""
    from apps.project_app.services.project_filesystem import (
        get_project_filesystem_manager,
    )

    manager = get_project_filesystem_manager(project.owner)
    project_path = manager.get_project_root_path(project)

    if not project_path or not project_path.exists():
        return None
    return project_path


def _list_branches(project_path) -> list[str] | None:
    """List all branches in a git repository."""
    try:
        result = subprocess.run(
            ["git", "branch", "-a"],
            cwd=project_path,
            capture_output=True,
            text=True,
            timeout=5,
        )

        if result.returncode != 0:
            return None

        branches = []
        for line in result.stdout.split("\n"):
            line = line.strip()
            if line:
                branch = line.replace("*", "").strip()
                branch = branch.replace("remotes/origin/", "")
                if branch and branch not in branches:
                    branches.append(branch)
        return branches

    except subprocess.TimeoutExpired:
        return None


# EOF
