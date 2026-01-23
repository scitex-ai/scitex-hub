#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Timestamp: "2025-11-29 (auto-generated)"
# File: /home/ywatanabe/proj/scitex-cloud/apps/project_app/views/repository/api/scitex.py
# ----------------------------------------
"""
SciTeX Structure Initialization API

This module contains API endpoints for SciTeX-related operations.
"""

from __future__ import annotations
import logging

from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

from ....models import Project

logger = logging.getLogger(__name__)


@require_http_methods(["POST"])
@login_required
def api_initialize_scitex_structure(request, username, slug):
    """
    API endpoint to initialize SciTeX structure in a project.

    Works for both local and remote projects.
    Copies template files from templates/research-master/scitex/ to the project.
    Non-destructive: Won't override existing files.

    Returns:
        {
            "success": true,
            "stats": {
                "files_created": 42,
                "files_skipped": 5,
                "bytes_transferred": 123456
            }
        }
    """
    user = get_object_or_404(User, username=username)
    project = get_object_or_404(Project, slug=slug, owner=user)

    # Check permissions (owner or collaborator only)
    if not (
        request.user == project.owner
        or project.collaborators.filter(id=request.user.id).exists()
    ):
        return JsonResponse({"success": False, "error": "Permission denied"}, status=403)

    try:
        # Use ProjectServiceManager for unified local/remote handling
        from apps.project_app.services.project_service_manager import ProjectServiceManager

        service_manager = ProjectServiceManager(project)
        success, stats, error = service_manager.initialize_scitex_structure()

        if not success:
            logger.error(f"Failed to initialize SciTeX structure for {username}/{slug}: {error}")
            return JsonResponse({
                "success": False,
                "error": error or "Failed to initialize SciTeX structure"
            }, status=500)

        logger.info(
            f"SciTeX structure initialized: {username}/{slug} - "
            f"{stats['files_created']} files created, {stats['files_skipped']} skipped"
        )

        return JsonResponse({
            "success": True,
            "message": "SciTeX structure initialized successfully",
            "stats": stats,
            "project_type": project.project_type,
        })

    except Exception as e:
        logger.error(f"Error initializing SciTeX structure for {username}/{slug}: {e}", exc_info=True)
        return JsonResponse({
            "success": False,
            "error": str(e)
        }, status=500)


# EOF
