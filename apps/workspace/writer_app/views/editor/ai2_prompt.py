#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: /home/ywatanabe/proj/scitex-hub/apps/writer_app/views/editor/ai2_prompt.py

"""API endpoint for generating AI2 Asta prompts.

Thin wrapper delegating to scitex.writer.prompts.generate_asta().
Django should import from scitex (the main interface), not directly from scitex_writer.
"""

import json
import logging
from pathlib import Path

from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

from apps.infra.project_app.models import Project

from .auth_utils import api_login_optional, get_user_for_request

logger = logging.getLogger(__name__)


def _get_writer_project_path(project, user, is_visitor):
    """Get writer project path for user."""
    if is_visitor:
        from apps.infra.project_app.services.project_filesystem import (
            get_project_filesystem_manager,
        )

        manager = get_project_filesystem_manager(user)
        visitor_dir = manager.get_project_root_path(project)
        if not visitor_dir:
            return None
        return visitor_dir / "scitex" / "writer"
    return Path(project.git_clone_path) / "scitex" / "writer"


@api_login_optional
@require_http_methods(["POST"])
def generate_asta_view(request, project_id):
    """Generate AI2 Asta prompt from manuscript files.

    Delegates to scitex.writer.prompts.generate_asta().
    """
    try:
        project = Project.objects.get(id=project_id)

        user, is_visitor = get_user_for_request(request, project_id)
        if not user:
            return JsonResponse(
                {"success": False, "error": "Invalid session"}, status=403
            )

        data = json.loads(request.body) if request.body else {}
        search_type = data.get("search_type", "related")

        project_path = _get_writer_project_path(project, user, is_visitor)
        if not project_path:
            return JsonResponse(
                {"success": False, "error": "Project path not found"}, status=404
            )

        if not project_path.exists():
            return JsonResponse(
                {
                    "success": False,
                    "error": f"Writer project not found at {project_path}",
                },
                status=404,
            )

        # Delegate to scitex.writer (single source of truth)
        # Import at runtime to avoid import-time issues with module re-exports
        from scitex.writer import prompts as sw_prompts

        result = sw_prompts.generate_asta(project_path, search_type)
        status_code = 200 if result.get("success") else 400
        return JsonResponse(result, status=status_code)

    except Project.DoesNotExist:
        return JsonResponse(
            {"success": False, "error": "Project not found"}, status=404
        )
    except Exception as e:
        logger.error(f"Error generating AI2 prompt: {e}", exc_info=True)
        return JsonResponse({"success": False, "error": str(e)}, status=500)


# EOF
