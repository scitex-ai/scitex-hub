#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Git staging operations API.

Provides endpoints for:
- Stage/unstage files
- Stage all / unstage all
"""

from __future__ import annotations

import json
import logging

from django.contrib.auth.models import User
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_http_methods

from ....models import Project
from .git_utils import get_project_path, run_git_command
from .permissions import check_project_write_access

logger = logging.getLogger(__name__)


@require_http_methods(["POST"])
def api_git_stage(request, username, slug):
    """Stage files for commit."""
    try:
        user = get_object_or_404(User, username=username)
        project = get_object_or_404(Project, slug=slug, owner=user)

        if not check_project_write_access(request, project):
            return JsonResponse(
                {"success": False, "error": "Permission denied"}, status=403
            )

        data = json.loads(request.body)
        paths = data.get("paths", [])

        if not paths:
            return JsonResponse(
                {"success": False, "error": "No paths specified"}, status=400
            )

        project_path = get_project_path(project)
        if not project_path or not project_path.exists():
            return JsonResponse(
                {"success": False, "error": "Project directory not found"}, status=404
            )

        # Stage each file
        staged = []
        errors = []
        for path in paths:
            success, stdout, stderr = run_git_command(project_path, ["add", "--", path])
            if success:
                staged.append(path)
            else:
                errors.append({"path": path, "error": stderr.strip()})

        return JsonResponse(
            {
                "success": len(errors) == 0,
                "staged": staged,
                "errors": errors,
                "message": (
                    f"Staged {len(staged)} file(s)" if staged else "No files staged"
                ),
            }
        )

    except json.JSONDecodeError:
        return JsonResponse({"success": False, "error": "Invalid JSON"}, status=400)
    except Exception as e:
        logger.error(f"Error staging files: {e}", exc_info=True)
        return JsonResponse({"success": False, "error": str(e)}, status=500)


@require_http_methods(["POST"])
def api_git_unstage(request, username, slug):
    """Unstage files (remove from staging area)."""
    try:
        user = get_object_or_404(User, username=username)
        project = get_object_or_404(Project, slug=slug, owner=user)

        if not check_project_write_access(request, project):
            return JsonResponse(
                {"success": False, "error": "Permission denied"}, status=403
            )

        data = json.loads(request.body)
        paths = data.get("paths", [])

        if not paths:
            return JsonResponse(
                {"success": False, "error": "No paths specified"}, status=400
            )

        project_path = get_project_path(project)
        if not project_path or not project_path.exists():
            return JsonResponse(
                {"success": False, "error": "Project directory not found"}, status=404
            )

        # Unstage each file
        unstaged = []
        errors = []
        for path in paths:
            success, stdout, stderr = run_git_command(
                project_path, ["reset", "HEAD", "--", path]
            )
            if success:
                unstaged.append(path)
            else:
                errors.append({"path": path, "error": stderr.strip()})

        return JsonResponse(
            {
                "success": len(errors) == 0,
                "unstaged": unstaged,
                "errors": errors,
                "message": (
                    f"Unstaged {len(unstaged)} file(s)"
                    if unstaged
                    else "No files unstaged"
                ),
            }
        )

    except json.JSONDecodeError:
        return JsonResponse({"success": False, "error": "Invalid JSON"}, status=400)
    except Exception as e:
        logger.error(f"Error unstaging files: {e}", exc_info=True)
        return JsonResponse({"success": False, "error": str(e)}, status=500)


@require_http_methods(["POST"])
def api_git_stage_all(request, username, slug):
    """Stage all changes."""
    try:
        user = get_object_or_404(User, username=username)
        project = get_object_or_404(Project, slug=slug, owner=user)

        if not check_project_write_access(request, project):
            return JsonResponse(
                {"success": False, "error": "Permission denied"}, status=403
            )

        project_path = get_project_path(project)
        if not project_path or not project_path.exists():
            return JsonResponse(
                {"success": False, "error": "Project directory not found"}, status=404
            )

        success, stdout, stderr = run_git_command(project_path, ["add", "-A"])
        if not success:
            return JsonResponse(
                {
                    "success": False,
                    "error": f"Failed to stage all: {stderr.strip()}",
                },
                status=500,
            )

        return JsonResponse(
            {
                "success": True,
                "message": "All changes staged",
            }
        )

    except Exception as e:
        logger.error(f"Error staging all: {e}", exc_info=True)
        return JsonResponse({"success": False, "error": str(e)}, status=500)


@require_http_methods(["POST"])
def api_git_unstage_all(request, username, slug):
    """Unstage all changes."""
    try:
        user = get_object_or_404(User, username=username)
        project = get_object_or_404(Project, slug=slug, owner=user)

        if not check_project_write_access(request, project):
            return JsonResponse(
                {"success": False, "error": "Permission denied"}, status=403
            )

        project_path = get_project_path(project)
        if not project_path or not project_path.exists():
            return JsonResponse(
                {"success": False, "error": "Project directory not found"}, status=404
            )

        success, stdout, stderr = run_git_command(project_path, ["reset", "HEAD"])
        if not success:
            return JsonResponse(
                {
                    "success": False,
                    "error": f"Failed to unstage all: {stderr.strip()}",
                },
                status=500,
            )

        return JsonResponse(
            {
                "success": True,
                "message": "All changes unstaged",
            }
        )

    except Exception as e:
        logger.error(f"Error unstaging all: {e}", exc_info=True)
        return JsonResponse({"success": False, "error": str(e)}, status=500)


# EOF
