"""
Code Workspace API Views - File operations for the simple editor.
"""

import json
import logging
from pathlib import Path

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

from apps.infra.project_app.models import Project
from apps.infra.project_app.services.git_service import git_commit_and_push
from apps.infra.project_app.services.git_status import get_file_diff, get_git_status

logger = logging.getLogger(__name__)


@require_http_methods(["GET"])
def api_get_git_status(request):
    """Get git status for all files in the project."""
    project_id = request.GET.get("project_id")

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
        statuses = get_git_status(Path(project.git_clone_path))

        # Convert to JSON-serializable format
        status_dict = {}
        for path, status_obj in statuses.items():
            status_dict[path] = {
                "status": status_obj.status,
                "staged": status_obj.staged,
            }

        return JsonResponse({"success": True, "statuses": status_dict})

    except Exception as e:
        logger.error(f"Error getting git status: {e}", exc_info=True)
        return JsonResponse({"error": str(e)}, status=500)


@require_http_methods(["GET"])
def api_get_file_diff(request, file_path):
    """Get line-level diff for a specific file."""
    project_id = request.GET.get("project_id")

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
        diffs = get_file_diff(Path(project.git_clone_path), file_path)

        # Convert to JSON-serializable format
        diff_list = []
        for diff in diffs:
            diff_list.append({"line": diff.line_number, "status": diff.status})

        return JsonResponse({"success": True, "diffs": diff_list, "path": file_path})

    except Exception as e:
        logger.error(f"Error getting file diff for {file_path}: {e}", exc_info=True)
        return JsonResponse({"error": str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
def api_git_commit(request):
    """Commit changes to git."""
    try:
        data = json.loads(request.body)
        project_id = data.get("project_id")
        message = data.get("message", "")
        push = data.get("push", True)

        if not project_id or not message:
            return JsonResponse(
                {"error": "project_id and message required"}, status=400
            )

        project = Project.objects.select_related("owner").get(id=project_id)

        # Write access: owner or collaborator with write/admin permission_level
        if not project.can_edit(request.user):
            return JsonResponse({"error": "Unauthorized"}, status=403)

        # Commit all changes
        success, output = git_commit_and_push(
            project_dir=Path(project.git_clone_path),
            message=message,
            files=None,  # Commit all changes
            branch="develop",
            push=push,
        )

        if success:
            return JsonResponse(
                {
                    "success": True,
                    "message": output,
                }
            )
        else:
            return JsonResponse(
                {
                    "success": False,
                    "error": output,
                },
                status=400,
            )

    except Exception as e:
        logger.error(f"Error committing changes: {e}", exc_info=True)
        return JsonResponse({"error": str(e)}, status=500)


# EOF
