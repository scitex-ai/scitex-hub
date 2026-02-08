#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: /home/ywatanabe/proj/scitex-cloud/apps/writer_app/views/editor/api/metadata/bibliography.py
"""Bibliography regeneration API endpoints."""

from __future__ import annotations

import logging

from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

from ...auth_utils import api_login_optional

logger = logging.getLogger(__name__)


@api_login_optional
@require_http_methods(["POST"])
def regenerate_bibliography_api(request, project_id):
    """Manually regenerate bibliography_all.bib by merging all .bib files.

    This is an opt-in operation that actually parses and merges BibTeX files.
    Call this when user wants to refresh bibliography or after adding new .bib files.

    Note: @api_login_optional already validates auth and project access.

    Returns:
        JSON with merge statistics
    """
    try:
        from pathlib import Path

        from apps.project_app.models import Project
        from apps.project_app.services.bibliography_manager import (
            regenerate_bibliography,
        )

        # @api_login_optional already validated access; just look up project
        project = Project.objects.get(id=project_id)

        if not project.git_clone_path:
            return JsonResponse(
                {"success": False, "error": "Project has no git repository"}, status=400
            )

        # Regenerate bibliography
        project_path = Path(project.git_clone_path)
        results = regenerate_bibliography(project_path, project.name)

        if results["success"]:
            scholar_count = results["scholar_count"]
            duplicates_removed = results.get("duplicates_removed", 0)
            logger.info(
                f"[Bibliography] Regenerated for {project.name}: "
                f"scholar={scholar_count}, duplicates_removed={duplicates_removed}"
            )

            return JsonResponse(
                {
                    "success": True,
                    "message": f"Bibliography regenerated with {scholar_count} papers",
                    "scholar_count": scholar_count,
                    "duplicates_removed": duplicates_removed,
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
