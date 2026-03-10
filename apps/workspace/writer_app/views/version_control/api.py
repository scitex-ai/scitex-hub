"""API endpoints for version control operations."""

from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from ...services import VersionControlService
import json
import logging

logger = logging.getLogger(__name__)


@login_required
@require_http_methods(["GET"])
def history_api(request):
    """Get manuscript version history.

    Query params:
        - project_id: Project ID
        - limit: Number of commits to return (default: 50)
    """
    try:
        project_id = request.GET.get("project_id")
        limit = int(request.GET.get("limit", 50))

        if not project_id:
            return JsonResponse(
                {"success": False, "error": "project_id required"}, status=400
            )

        vc_service = VersionControlService(project_id, request.user.id)
        history = vc_service.get_history(limit=limit)

        return JsonResponse({"success": True, "history": history})

    except Exception as e:
        logger.error(f"Error getting history: {e}", exc_info=True)
        return JsonResponse({"success": False, "error": str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
def create_version_api(request):
    """Create a new version/commit.

    POST body:
        {
            "project_id": <project_id>,
            "message": <commit_message>
        }
    """
    try:
        data = json.loads(request.body)
        project_id = data.get("project_id")
        message = data.get("message")

        if not all([project_id, message]):
            return JsonResponse(
                {"success": False, "error": "project_id and message required"},
                status=400,
            )

        vc_service = VersionControlService(project_id, request.user.id)
        result = vc_service.create_version(message)

        return JsonResponse(result)

    except Exception as e:
        logger.error(f"Error creating version: {e}", exc_info=True)
        return JsonResponse({"success": False, "error": str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
def rollback_api(request):
    """Rollback to a previous version.

    POST body:
        {
            "project_id": <project_id>,
            "commit_hash": <commit_hash>
        }
    """
    try:
        data = json.loads(request.body)
        project_id = data.get("project_id")
        commit_hash = data.get("commit_hash")

        if not all([project_id, commit_hash]):
            return JsonResponse(
                {"success": False, "error": "project_id and commit_hash required"},
                status=400,
            )

        vc_service = VersionControlService(project_id, request.user.id)
        result = vc_service.rollback(commit_hash)

        return JsonResponse(result)

    except Exception as e:
        logger.error(f"Error rolling back: {e}", exc_info=True)
        return JsonResponse({"success": False, "error": str(e)}, status=500)
