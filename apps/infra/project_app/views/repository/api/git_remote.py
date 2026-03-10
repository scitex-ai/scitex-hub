#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Git remote operations API.

Provides endpoints for:
- Push to remote
- Pull from remote
"""

from __future__ import annotations

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
def api_git_push(request, username, slug):
    """Push commits to remote."""
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

        success, stdout, stderr = run_git_command(
            project_path, ["push", "origin", "HEAD"], timeout=60
        )

        if success:
            return JsonResponse({"success": True, "message": "Pushed to remote"})
        else:
            return JsonResponse(
                {"success": False, "error": f"Push failed: {stderr.strip()}"},
                status=500,
            )

    except Exception as e:
        logger.error(f"Error pushing: {e}", exc_info=True)
        return JsonResponse({"success": False, "error": str(e)}, status=500)


@require_http_methods(["POST"])
def api_git_pull(request, username, slug):
    """Pull from remote."""
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

        success, stdout, stderr = run_git_command(
            project_path, ["pull", "--ff-only"], timeout=60
        )

        if success:
            return JsonResponse({"success": True, "message": "Pulled from remote"})
        else:
            return JsonResponse(
                {"success": False, "error": f"Pull failed: {stderr.strip()}"},
                status=500,
            )

    except Exception as e:
        logger.error(f"Error pulling: {e}", exc_info=True)
        return JsonResponse({"success": False, "error": str(e)}, status=500)


# EOF
