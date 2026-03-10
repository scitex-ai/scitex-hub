"""Workspace API - Save file content (shared across all modules)."""

import json
import logging

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

from apps.infra.project_app.models import Project

logger = logging.getLogger(__name__)


@login_required
@require_http_methods(["POST"])
def api_save_file(request):
    """Save file content (supports both local and remote projects)."""
    try:
        # Block read-only visitors immediately
        if request.user.username == "readonly-visitor":
            return JsonResponse(
                {"error": "Read-only mode — sign up for full access"},
                status=403,
            )

        data = json.loads(request.body)
        project_id = data.get("project_id")
        file_path = data.get("path")
        content = data.get("content")

        if not project_id or not file_path or content is None:
            return JsonResponse({"error": "Missing required fields"}, status=400)

        project = Project.objects.select_related("owner").get(id=project_id)

        if not project.can_edit(request.user):
            return JsonResponse({"error": "Unauthorized"}, status=403)

        from apps.infra.project_app.services.project_service_manager import (
            ProjectServiceManager,
        )

        service_manager = ProjectServiceManager(project)
        project_path = service_manager.get_project_path()

        file_full_path = project_path / file_path

        # Security check: prevent path traversal
        if not str(file_full_path.resolve()).startswith(str(project_path.resolve())):
            return JsonResponse({"error": "Invalid file path"}, status=400)

        file_full_path.parent.mkdir(parents=True, exist_ok=True)

        with open(file_full_path, "w", encoding="utf-8") as f:
            f.write(content)

        return JsonResponse(
            {
                "success": True,
                "message": "File saved successfully",
                "path": file_path,
                "project_type": project.project_type,
            }
        )

    except Exception as e:
        logger.error(f"Error saving file: {e}", exc_info=True)
        return JsonResponse({"error": str(e)}, status=500)


# EOF
