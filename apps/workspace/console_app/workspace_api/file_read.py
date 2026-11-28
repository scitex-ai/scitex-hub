"""
Code Workspace API Views - File operations for the simple editor.
"""

import logging
from pathlib import Path

from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

from apps.infra.project_app.models import Project
from apps.infra.project_app.services.filesystem.permissions import (
    validate_path_in_project,
)
from apps.user_content import user_file_response

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
        # TRIP projects: on-demand SSH file access
        if (
            project.project_type == "remote"
            and hasattr(project, "remote_config")
            and project.remote_config.connection_mode == "trip"
        ):
            return _read_trip_file(project, file_path, raw, download)

        # Get project path (works for both local and remote projects)
        from apps.infra.project_app.services.project_service_manager import (
            ProjectServiceManager,
        )

        service_manager = ProjectServiceManager(project)
        project_path = service_manager.get_project_path()

        file_full_path = project_path / file_path

        # Security check
        # Component-wise containment, not a string prefix match.
        # CONTAINMENT ONLY -- this view has a public-visibility branch and no
        # @login_required, so a tenant-ownership check would break anonymous
        # browsing of public projects. OPEN QUESTION for the operator: this
        # view is currently UNROUTED (console urls/api.py redirects to
        # /api/workspace/file-content/) -- it may be better deleted than kept.
        if not validate_path_in_project(project_path, file_full_path):
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
                "project_type": project.project_type,  # Include project type info
            }
        )

    except UnicodeDecodeError:
        return JsonResponse({"error": "Binary file cannot be edited"}, status=400)
    except Exception as e:
        logger.error(f"Error reading file {file_path}: {e}", exc_info=True)
        return JsonResponse({"error": str(e)}, status=500)


def _serve_raw_file(file_path: Path, original_path: str, download: bool = False):
    """Serve a file as raw content (for images, PDFs, etc.)."""
    return user_file_response(open(file_path, "rb"), file_path.name, download=download)


def _read_trip_file(project, file_path, raw, download):
    """Read file from TRIP project via paramiko SFTP."""
    from apps.infra.project_app.services.trip_backend import get_trip_backend

    backend = get_trip_backend(project)

    if not backend.exists(file_path):
        return JsonResponse({"error": "File not found"}, status=404)

    if not backend.is_file(file_path):
        return JsonResponse({"error": "Not a file"}, status=400)

    if raw:
        return user_file_response(
            backend.read_file_bytes(file_path),
            file_path.rsplit("/", 1)[-1],
            download=download,
        )

    content = backend.read_file(file_path)
    return JsonResponse(
        {
            "success": True,
            "content": content,
            "path": file_path,
            "language": _detect_language(file_path),
            "project_type": "trip",
        }
    )


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
