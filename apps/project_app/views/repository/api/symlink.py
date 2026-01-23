#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Timestamp: "2025-11-29 (auto-generated)"
# File: /home/ywatanabe/proj/scitex-cloud/apps/project_app/views/repository/api/symlink.py
# ----------------------------------------
"""
Symlink Management API

This module contains API endpoints for creating and managing symlinks.
"""

from __future__ import annotations
import json
import logging
import os

from django.shortcuts import get_object_or_404
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

from ....models import Project
from .permissions import check_project_write_access

logger = logging.getLogger(__name__)


@require_http_methods(["POST"])
def api_create_symlink(request, username, slug):
    """
    API endpoint to create a symlink in the project repository.
    Creates relative symlinks for cross-module references.

    POST data:
        source: Path to source file (relative to project root)
        target: Path where symlink should be created (relative to project root)
    """
    user = get_object_or_404(User, username=username)
    project = get_object_or_404(Project, slug=slug, owner=user)

    # Only owner and collaborators can create symlinks
    if not check_project_write_access(request, project):
        return JsonResponse({"success": False, "error": "Permission denied"}, status=403)

    # Parse request body
    try:
        data = json.loads(request.body)
        source_path = data.get("source", "").strip()
        target_path = data.get("target", "").strip()
    except json.JSONDecodeError:
        return JsonResponse({"success": False, "error": "Invalid JSON"}, status=400)

    if not source_path or not target_path:
        return JsonResponse(
            {"success": False, "error": "Both source and target paths are required"},
            status=400
        )

    # Get project directory
    from apps.project_app.services.project_filesystem import (
        get_project_filesystem_manager,
    )

    manager = get_project_filesystem_manager(project.owner)
    project_root = manager.get_project_root_path(project)

    if not project_root or not project_root.exists():
        return JsonResponse(
            {"success": False, "error": "Project directory not found"},
            status=404
        )

    # Resolve full paths
    source_full = (project_root / source_path).resolve()
    target_full = (project_root / target_path).resolve()

    # Security check: both paths must be within project root
    if not (
        str(source_full).startswith(str(project_root.resolve()))
        and str(target_full).startswith(str(project_root.resolve()))
    ):
        return JsonResponse(
            {"success": False, "error": "Paths must be within project directory"},
            status=400
        )

    # Check source exists
    if not source_full.exists():
        return JsonResponse(
            {"success": False, "error": f"Source file not found: {source_path}"},
            status=404
        )

    # Check target doesn't already exist
    if target_full.exists():
        return JsonResponse(
            {"success": False, "error": f"Target already exists: {target_path}"},
            status=400
        )

    # Create parent directory for target if needed
    target_full.parent.mkdir(parents=True, exist_ok=True)

    # Calculate relative path from target to source
    try:
        relative_source = os.path.relpath(source_full, target_full.parent)
    except ValueError:
        return JsonResponse(
            {"success": False, "error": "Cannot create relative path between source and target"},
            status=400
        )

    # Create symlink
    try:
        target_full.symlink_to(relative_source)
        logger.info(
            f"Created symlink: {target_path} -> {relative_source} "
            f"(project: {project.slug}, user: {request.user.username})"
        )

        return JsonResponse({
            "success": True,
            "source": source_path,
            "target": target_path,
            "relative_link": relative_source,
        })
    except OSError as e:
        logger.error(f"Failed to create symlink: {e}")
        return JsonResponse(
            {"success": False, "error": f"Failed to create symlink: {str(e)}"},
            status=500
        )


# EOF
