#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bundle Extraction API

This module contains API endpoints for extracting .figz and .pltz bundles.
"""

from __future__ import annotations
import json
import logging
import zipfile

from django.shortcuts import get_object_or_404
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

from ....models import Project
from .permissions import check_project_write_access

logger = logging.getLogger(__name__)


@require_http_methods(["POST"])
def api_extract_bundle(request, username, slug):
    """
    API endpoint to extract a .figz or .pltz bundle file to a directory.

    POST data:
        bundle_path: Path to bundle file (relative to project root)
        output_path: Path where bundle should be extracted (relative to project root)
    """
    user = get_object_or_404(User, username=username)
    project = get_object_or_404(Project, slug=slug, owner=user)

    # Only owner and collaborators can extract bundles
    if not check_project_write_access(request, project):
        return JsonResponse({"success": False, "error": "Permission denied"}, status=403)

    # Parse request body
    try:
        data = json.loads(request.body)
        bundle_path = data.get("bundle_path", "").strip()
        output_path = data.get("output_path", "").strip()
    except json.JSONDecodeError:
        return JsonResponse({"success": False, "error": "Invalid JSON"}, status=400)

    if not bundle_path or not output_path:
        return JsonResponse(
            {"success": False, "error": "Both bundle_path and output_path are required"},
            status=400
        )

    # Validate file extension
    if not (bundle_path.endswith('.figz') or bundle_path.endswith('.pltz')):
        return JsonResponse(
            {"success": False, "error": "Only .figz and .pltz files can be extracted"},
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
    bundle_full = (project_root / bundle_path).resolve()
    output_full = (project_root / output_path).resolve()

    # Security check: both paths must be within project root
    if not (
        str(bundle_full).startswith(str(project_root.resolve()))
        and str(output_full).startswith(str(project_root.resolve()))
    ):
        return JsonResponse(
            {"success": False, "error": "Paths must be within project directory"},
            status=400
        )

    # Check bundle file exists
    if not bundle_full.exists():
        return JsonResponse(
            {"success": False, "error": f"Bundle file not found: {bundle_path}"},
            status=404
        )

    # Check bundle is a valid zip file
    if not zipfile.is_zipfile(bundle_full):
        return JsonResponse(
            {"success": False, "error": f"Invalid bundle file (not a zip): {bundle_path}"},
            status=400
        )

    # Check output doesn't already exist
    if output_full.exists():
        return JsonResponse(
            {"success": False, "error": f"Output directory already exists: {output_path}"},
            status=400
        )

    # Extract the bundle
    try:
        output_full.mkdir(parents=True, exist_ok=True)

        with zipfile.ZipFile(bundle_full, 'r') as zip_ref:
            # Security: check for path traversal in zip
            for name in zip_ref.namelist():
                if name.startswith('/') or '..' in name:
                    return JsonResponse(
                        {"success": False, "error": "Invalid paths in bundle archive"},
                        status=400
                    )

            zip_ref.extractall(output_full)

        logger.info(
            f"Extracted bundle: {bundle_path} -> {output_path} "
            f"(project: {project.slug}, user: {request.user.username})"
        )

        return JsonResponse({
            "success": True,
            "bundle_path": bundle_path,
            "output_path": output_path,
        })
    except zipfile.BadZipFile as e:
        logger.error(f"Invalid zip file: {e}")
        return JsonResponse(
            {"success": False, "error": f"Invalid bundle archive: {str(e)}"},
            status=400
        )
    except OSError as e:
        logger.error(f"Failed to extract bundle: {e}")
        # Clean up partial extraction
        if output_full.exists():
            import shutil
            shutil.rmtree(output_full, ignore_errors=True)
        return JsonResponse(
            {"success": False, "error": f"Failed to extract bundle: {str(e)}"},
            status=500
        )


# EOF
