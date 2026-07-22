#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""File Operations API - Utility Functions."""

from __future__ import annotations

import logging
from pathlib import Path

from django.contrib.auth.models import User
from django.http import JsonResponse
from django.shortcuts import get_object_or_404

from ....models import Project
from ....services.filesystem.permissions import validate_path_in_project
from .permissions import check_project_write_access

logger = logging.getLogger(__name__)

# Common error responses
ERR_PERMISSION = JsonResponse(
    {"success": False, "error": "Permission denied"}, status=403
)
ERR_NO_PATH = JsonResponse({"success": False, "error": "Path is required"}, status=400)
ERR_INVALID_PATH = JsonResponse({"success": False, "error": "Invalid path"}, status=400)
ERR_NOT_FOUND = JsonResponse({"success": False, "error": "File not found"}, status=404)
ERR_NO_PROJECT = JsonResponse(
    {"success": False, "error": "Project directory not found"}, status=404
)
ERR_EXISTS = JsonResponse(
    {"success": False, "error": "File already exists"}, status=400
)
ERR_JSON = JsonResponse({"success": False, "error": "Invalid JSON"}, status=400)


def get_project_context(request, username, slug):
    """Get project and validate write access. Returns (project, project_path, error)."""
    user = get_object_or_404(User, username=username)
    project = get_object_or_404(Project, slug=slug, owner=user)

    if not check_project_write_access(request, project):
        return None, None, ERR_PERMISSION

    project_path = get_project_path(project)
    if not project_path or not project_path.exists():
        return None, None, ERR_NO_PROJECT

    return project, project_path, None


def get_project_path(project):
    """Get the filesystem path for a project."""
    from apps.infra.project_app.services.project_service_manager import (
        ProjectServiceManager,
    )

    service_manager = ProjectServiceManager(project)
    return service_manager.get_project_path()


def validate_path(project_path: Path, file_path: str) -> Path | None:
    """
    Validate that file_path is within project_path.

    Returns resolved path or None if invalid.

    Uses component-wise containment (validate_path_in_project), NOT a string
    prefix match: `project_path / "../proj-other/secret"` string-prefix-matches
    project_path and would otherwise escape into a sibling tenant's project.

    This is the sole containment validator for the file_ops_crud and
    file_ops_transfer endpoints (create/delete/rename/copy/move/upload), whose
    sinks include Path.unlink, shutil.move and shutil.rmtree. Ownership is
    enforced separately by get_project_context() above.
    """
    try:
        full_path = (project_path / file_path).resolve()
    except (ValueError, OSError, RuntimeError):
        return None
    if not validate_path_in_project(project_path, full_path):
        return None
    return full_path


def git_auto_commit(project, project_path, file_path, action):
    """
    Auto-commit disabled - users should commit manually when ready.

    This function is kept as a no-op for backward compatibility.
    Git tracks changes but doesn't auto-commit, so git gutter shows modifications.
    """
    pass  # Auto-commit disabled


# EOF
