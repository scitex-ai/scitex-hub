"""
Workspace API Views - File content retrieval for the editor.
"""

import logging
import mimetypes
from pathlib import Path

from django.http import FileResponse, JsonResponse
from django.views.decorators.http import require_http_methods

from apps.project_app.models import Project

logger = logging.getLogger(__name__)


@require_http_methods(["GET"])
def api_get_file_content(request, file_path):
    """Get file content for editing (supports both local and remote projects).

    Query parameters:
    - project_id: Required. The project ID.
    - raw: Optional. If 'true', returns raw file content (for images, PDFs, etc.)
    - download: Optional. If 'true', adds Content-Disposition header for download.
    """
    project_id = request.GET.get("project_id")
    raw = request.GET.get("raw", "").lower() == "true"
    download = request.GET.get("download", "").lower() == "true"

    if not project_id:
        return JsonResponse({"error": "project_id required"}, status=400)

    try:
        project = Project.objects.select_related("owner").get(id=project_id)
    except Project.DoesNotExist:
        return JsonResponse({"error": "Project not found"}, status=404)

    # Check permissions
    if not (
        request.user == project.owner
        or request.user in project.collaborators.all()
        or project.visibility == "public"
    ):
        return JsonResponse({"error": "Unauthorized"}, status=403)

    try:
        # Get project path (works for both local and remote projects)
        from apps.project_app.services.project_service_manager import (
            ProjectServiceManager,
        )

        service_manager = ProjectServiceManager(project)
        project_path = service_manager.get_project_path()

        file_full_path = project_path / file_path

        # Security check
        if not str(file_full_path.resolve()).startswith(str(project_path.resolve())):
            return JsonResponse({"error": "Invalid file path"}, status=400)

        if not file_full_path.exists():
            return JsonResponse({"error": "File not found"}, status=404)

        if not file_full_path.is_file():
            return JsonResponse({"error": "Not a file"}, status=400)

        # Raw mode: return the file directly (for images, PDFs, etc.)
        if raw:
            return _serve_raw_file(file_full_path, file_path, download)

        # Text mode: return as JSON for Monaco editor
        with open(file_full_path, "r", encoding="utf-8") as f:
            content = f.read()

        return JsonResponse(
            {
                "success": True,
                "content": content,
                "path": file_path,
                "language": _detect_language(file_path),
                "project_type": project.project_type,
            }
        )

    except UnicodeDecodeError:
        return JsonResponse({"error": "Binary file cannot be edited"}, status=400)
    except Exception as e:
        logger.error(f"Error reading file {file_path}: {e}", exc_info=True)
        return JsonResponse({"error": str(e)}, status=500)


def _serve_raw_file(file_path: Path, original_path: str, download: bool = False):
    """Serve a file as raw content (for images, PDFs, etc.)."""
    content_type, _ = mimetypes.guess_type(str(file_path))
    if content_type is None:
        content_type = "application/octet-stream"

    response = FileResponse(
        open(file_path, "rb"),
        content_type=content_type,
    )

    filename = file_path.name
    if download:
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
    else:
        response["Content-Disposition"] = f'inline; filename="{filename}"'

    return response


def _detect_language(file_path):
    """Detect programming language from file extension."""
    ext = file_path.split(".")[-1].lower()
    language_map = {
        "py": "python",
        "js": "javascript",
        "ts": "typescript",
        "html": "html",
        "css": "css",
        "md": "markdown",
        "json": "json",
        "yaml": "yaml",
        "yml": "yaml",
    }
    return language_map.get(ext, "plaintext")


# EOF
