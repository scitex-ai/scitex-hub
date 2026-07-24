"""
Code Workspace API Views - File operations for the simple editor.
"""

import json
import logging

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

from apps.infra.project_app.models import Project
from apps.infra.project_app.services.filesystem.permissions import (
    validate_path_in_project,
)

logger = logging.getLogger(__name__)


@login_required
@require_http_methods(["POST"])
def api_save_file(request):
    """Save file content (supports both local and remote projects)."""
    try:
        data = json.loads(request.body)
        project_id = data.get("project_id")
        file_path = data.get("path")
        content = data.get("content")

        if not project_id or not file_path or content is None:
            return JsonResponse({"error": "Missing required fields"}, status=400)

        project = Project.objects.select_related("owner").get(id=project_id)

        # Write access: owner or collaborator with write/admin permission_level
        if not project.can_edit(request.user):
            return JsonResponse({"error": "Unauthorized"}, status=403)

        # TRIP projects: on-demand SSH file access
        if (
            project.project_type == "remote"
            and hasattr(project, "remote_config")
            and project.remote_config.connection_mode == "trip"
        ):
            from apps.infra.project_app.services.trip_backend import get_trip_backend

            backend = get_trip_backend(project)
            backend.write_file(file_path, content)
            return JsonResponse(
                {
                    "success": True,
                    "message": "File saved successfully",
                    "path": file_path,
                    "project_type": "trip",
                }
            )

        # Get project path (works for both local and remote projects)
        from apps.infra.project_app.services.project_service_manager import (
            ProjectServiceManager,
        )

        service_manager = ProjectServiceManager(project)
        project_path = service_manager.get_project_path()

        file_full_path = project_path / file_path

        # Security check
        # Component-wise containment, not a string prefix match.
        if not validate_path_in_project(project_path, file_full_path):
            return JsonResponse({"error": "Invalid file path"}, status=400)

        file_full_path.parent.mkdir(parents=True, exist_ok=True)

        with open(file_full_path, "w", encoding="utf-8") as f:
            f.write(content)

        # Auto-commit disabled - users should commit manually when ready
        # Git tracks changes but doesn't auto-commit, so git gutter shows modifications

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
