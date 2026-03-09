"""API endpoints for arXiv submission operations."""

from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from ...services import ArxivService
import json
import logging

logger = logging.getLogger(__name__)


@login_required
@require_http_methods(["POST"])
def submit_api(request):
    """Submit manuscript to arXiv.

    POST body:
        {
            "project_id": <project_id>,
            "title": <title>,
            "abstract": <abstract>,
            "authors": <authors>,
            "category": <arxiv_category>,
            "comments": <optional_comments>
        }
    """
    try:
        data = json.loads(request.body)
        project_id = data.get("project_id")

        if not project_id:
            return JsonResponse(
                {"success": False, "error": "project_id required"}, status=400
            )

        arxiv_service = ArxivService(project_id, request.user.id)
        result = arxiv_service.submit(data)

        return JsonResponse(result)

    except Exception as e:
        logger.error(f"Submission error: {e}", exc_info=True)
        return JsonResponse({"success": False, "error": str(e)}, status=500)


@login_required
@require_http_methods(["GET"])
def status_check_api(request):
    """Check arXiv submission status.

    Query params:
        - submission_id: Submission ID
    """
    try:
        submission_id = request.GET.get("submission_id")

        if not submission_id:
            return JsonResponse(
                {"success": False, "error": "submission_id required"}, status=400
            )

        arxiv_service = ArxivService(None, request.user.id)
        status = arxiv_service.check_status(submission_id)

        return JsonResponse({"success": True, "status": status})

    except Exception as e:
        logger.error(f"Status check error: {e}", exc_info=True)
        return JsonResponse({"success": False, "error": str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
def validate_api(request):
    """Validate manuscript before submission.

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

        arxiv_service = ArxivService(project_id, request.user.id)
        validation_result = arxiv_service.validate()

        return JsonResponse(validation_result)

    except Exception as e:
        logger.error(f"Validation error: {e}", exc_info=True)
        return JsonResponse({"success": False, "error": str(e)}, status=500)
