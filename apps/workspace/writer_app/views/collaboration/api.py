"""API endpoints for collaboration operations."""

from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from ...services import CollaborationService
import json
import logging

logger = logging.getLogger(__name__)


@login_required
@require_http_methods(["POST"])
def join_api(request):
    """Join a collaboration session.

    POST body:
        {
            "project_id": <project_id>
        }
    """
    try:
        data = json.loads(request.body)
        project_id = data.get("project_id")

        if not project_id:
            return JsonResponse(
                {"success": False, "error": "project_id required"}, status=400
            )

        collab_service = CollaborationService(project_id, request.user.id)
        result = collab_service.join_session()

        return JsonResponse(result)

    except Exception as e:
        logger.error(f"Error joining session: {e}", exc_info=True)
        return JsonResponse({"success": False, "error": str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
def leave_api(request):
    """Leave a collaboration session.

    POST body:
        {
            "project_id": <project_id>
        }
    """
    try:
        data = json.loads(request.body)
        project_id = data.get("project_id")

        if not project_id:
            return JsonResponse(
                {"success": False, "error": "project_id required"}, status=400
            )

        collab_service = CollaborationService(project_id, request.user.id)
        result = collab_service.leave_session()

        return JsonResponse(result)

    except Exception as e:
        logger.error(f"Error leaving session: {e}", exc_info=True)
        return JsonResponse({"success": False, "error": str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
def lock_section_api(request):
    """Lock a section for exclusive editing.

    POST body:
        {
            "project_id": <project_id>,
            "section_name": <section_name>
        }
    """
    try:
        data = json.loads(request.body)
        project_id = data.get("project_id")
        section_name = data.get("section_name")

        if not all([project_id, section_name]):
            return JsonResponse(
                {"success": False, "error": "project_id and section_name required"},
                status=400,
            )

        collab_service = CollaborationService(project_id, request.user.id)
        result = collab_service.lock_section(section_name)

        return JsonResponse(result)

    except Exception as e:
        logger.error(f"Error locking section: {e}", exc_info=True)
        return JsonResponse({"success": False, "error": str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
def unlock_section_api(request):
    """Unlock a section.

    POST body:
        {
            "project_id": <project_id>,
            "section_name": <section_name>
        }
    """
    try:
        data = json.loads(request.body)
        project_id = data.get("project_id")
        section_name = data.get("section_name")

        if not all([project_id, section_name]):
            return JsonResponse(
                {"success": False, "error": "project_id and section_name required"},
                status=400,
            )

        collab_service = CollaborationService(project_id, request.user.id)
        result = collab_service.unlock_section(section_name)

        return JsonResponse(result)

    except Exception as e:
        logger.error(f"Error unlocking section: {e}", exc_info=True)
        return JsonResponse({"success": False, "error": str(e)}, status=500)
