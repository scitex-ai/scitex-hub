#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: /home/ywatanabe/proj/scitex-cloud/apps/writer_app/views/editor/api/metadata/bibliography.py
"""Bibliography regeneration API endpoints."""

from __future__ import annotations
import logging
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from ...auth_utils import api_login_optional, get_user_for_request

logger = logging.getLogger(__name__)


@api_login_optional
@require_http_methods(["POST"])
def regenerate_bibliography_api(request, project_id):
    """Manually regenerate bibliography_all.bib by merging all .bib files.

    This is an opt-in operation that actually parses and merges BibTeX files.
    Call this when user wants to refresh bibliography or after adding new .bib files.

    Returns:
        JSON with merge statistics
    """
    try:
        from apps.project_app.models import Project
        from pathlib import Path
        from apps.project_app.services.bibliography_manager import (
            regenerate_bibliography,
        )

        # Get project
        user = get_user_for_request(request)
        if user.is_authenticated:
            project = Project.objects.get(id=project_id, owner=user)
        else:
            return JsonResponse(
                {"success": False, "error": "Authentication required"}, status=401
            )

        if not project.git_clone_path:
            return JsonResponse(
                {"success": False, "error": "Project has no git repository"}, status=400
            )

        # Regenerate bibliography
        project_path = Path(project.git_clone_path)
        results = regenerate_bibliography(project_path, project.name)

        if results["success"]:
            logger.info(
                f"[Bibliography] Regenerated for {project.name}: "
                f"scholar={results['scholar_count']}, writer={results['writer_count']}, "
                f"total={results['total_count']}"
            )

            return JsonResponse(
                {
                    "success": True,
                    "message": f"Bibliography regenerated with {results['total_count']} papers",
                    "scholar_count": results["scholar_count"],
                    "writer_count": results["writer_count"],
                    "total_count": results["total_count"],
                }
            )
        else:
            return JsonResponse(
                {
                    "success": False,
                    "error": "Failed to regenerate bibliography",
                    "details": results["errors"],
                },
                status=500,
            )

    except Project.DoesNotExist:
        return JsonResponse(
            {"success": False, "error": "Project not found"}, status=404
        )
    except Exception as e:
        logger.error(f"[Bibliography] Error regenerating: {e}", exc_info=True)
        return JsonResponse({"success": False, "error": str(e)}, status=500)


# EOF
