"""
Code Workspace API Views - File operations for the simple editor.
"""

import json
import logging
import subprocess
from pathlib import Path

from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from apps.project_app.models import Project
from apps.project_app.services.git_status import get_git_status, get_file_diff
from apps.project_app.services.git_service import git_commit_and_push

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
                "staged": status_obj.staged
            }

        return JsonResponse({
            "success": True,
            "statuses": status_dict
        })

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
            diff_list.append({
                "line": diff.line_number,
                "status": diff.status
            })

        return JsonResponse({
            "success": True,
            "diffs": diff_list,
            "path": file_path
        })

    except Exception as e:
        logger.error(f"Error getting file diff for {file_path}: {e}", exc_info=True)
        return JsonResponse({"error": str(e)}, status=500)


@require_http_methods(["POST"])
def api_git_commit(request):
    """Commit changes to git."""
    try:
        data = json.loads(request.body)
        project_id = data.get("project_id")
        message = data.get("message", "")
        push = data.get("push", True)

        if not project_id or not message:
            return JsonResponse({"error": "project_id and message required"}, status=400)

        project = Project.objects.select_related("owner").get(id=project_id)

        # Check permissions (allow authenticated users and visitors with allocated project)
        if request.user.is_authenticated:
            has_access = (
                request.user == project.owner
                or request.user in project.collaborators.all()
            )
        else:
            # For visitor users, check if this is their allocated visitor project
            visitor_project_id = request.session.get("visitor_project_id")
            has_access = (visitor_project_id and project.id == visitor_project_id)

        if not has_access:
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
            return JsonResponse({
                "success": True,
                "message": output,
            })
        else:
            return JsonResponse({
                "success": False,
                "error": output,
            }, status=400)

    except Exception as e:
        logger.error(f"Error committing changes: {e}", exc_info=True)
        return JsonResponse({"error": str(e)}, status=500)
# EOF
