#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: /home/ywatanabe/proj/scitex-cloud/apps/writer_app/views/editor/api/metadata/sections.py
"""Section configuration view endpoints."""

from __future__ import annotations
import logging
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from .section_scanner import _scan_project_sections

logger = logging.getLogger(__name__)


@require_http_methods(["GET"])
def sections_config_view(request, project_id=None):
    """Return hierarchical sections configuration dynamically from filesystem.

    Scans the actual project directory to find available sections,
    excluding symlinks and system files.

    Args:
        request: HTTP request
        project_id: (optional) Project ID from URL path

    Query params:
        - project_id: (optional) Project ID to load sections from (fallback)

    Returns:
        JSON with hierarchical section structure based on actual files
    """
    try:
        from .....services import WriterService
        from apps.project_app.models import Project

        # Get project - try from URL param, query param, session, or user's default
        if not project_id:
            project_id = request.GET.get("project_id")
        if not project_id and request.user.is_authenticated:
            project_id = request.session.get("current_project_id")
            if not project_id:
                # Get user's first project
                project = Project.objects.filter(owner=request.user).first()
                if project:
                    project_id = project.id

        if not project_id:
            # Return static config as fallback
            from .....configs.sections_config import SECTION_HIERARCHY

            return JsonResponse(
                {
                    "success": True,
                    "hierarchy": SECTION_HIERARCHY,
                    "message": "Using static configuration (no project found)",
                }
            )

        # Get Writer service
        user_id = request.user.id if request.user.is_authenticated else None
        writer_service = WriterService(int(project_id), user_id)

        # Build hierarchy from actual filesystem
        hierarchy = _scan_project_sections(writer_service.writer_dir)

        return JsonResponse({"success": True, "hierarchy": hierarchy})

    except Exception as e:
        logger.error(f"Error getting sections config: {e}", exc_info=True)
        # Return static config as fallback
        from .....configs.sections_config import SECTION_HIERARCHY

        return JsonResponse(
            {
                "success": True,
                "hierarchy": SECTION_HIERARCHY,
                "message": f"Using static configuration (error: {str(e)})",
            }
        )


# EOF
