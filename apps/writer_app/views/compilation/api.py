"""API endpoints for compilation operations."""

from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from ...decorators import writer_auth_required, writer_project_access_required
from ...services import CompilerService
import json
import logging

logger = logging.getLogger(__name__)


@writer_auth_required
@require_http_methods(["POST"])
def compilation_api(request):
    """Start a compilation job.

    POST body:
        {
            "project_id": <project_id>,
            "doc_type": "manuscript" | "supplementary" | "revision"
        }
    """
    try:
        data = json.loads(request.body)
        project_id = data.get("project_id")
        doc_type = data.get("doc_type", "manuscript")

        if not project_id:
            return JsonResponse(
                {"success": False, "error": "project_id required"}, status=400
            )

        # Verify project access
        from apps.project_app.models import Project
        try:
            project = Project.objects.get(id=project_id)
        except Project.DoesNotExist:
            return JsonResponse(
                {"success": False, "error": "Project not found"}, status=404
            )

        # Check project access for visitors
        if hasattr(request, 'is_visitor') and request.is_visitor:
            from apps.project_app.services.visitor_pool import VisitorPool
            visitor_project_id = request.session.get(VisitorPool.SESSION_KEY_PROJECT_ID)
            if project.id != visitor_project_id:
                return JsonResponse(
                    {"success": False, "error": "Visitors can only compile their default project"},
                    status=403
                )
        else:
            # Authenticated user must own the project
            if project.owner != request.effective_user:
                return JsonResponse(
                    {"success": False, "error": "You don't have access to this project"},
                    status=403
                )

        compilation_service = CompilerService(project_id, request.effective_user.id)
        result = compilation_service.compile(doc_type)

        return JsonResponse(result)

    except Exception as e:
        logger.error(f"Compilation error: {e}", exc_info=True)
        return JsonResponse({"success": False, "error": str(e)}, status=500)


@writer_auth_required
@require_http_methods(["GET"])
def status_api(request):
    """Get compilation job status.

    Query params:
        - job_id: Compilation job ID
    """
    try:
        job_id = request.GET.get("job_id")

        if not job_id:
            return JsonResponse(
                {"success": False, "error": "job_id required"}, status=400
            )

        compilation_service = CompilerService(None, request.effective_user.id)
        status = compilation_service.get_status(job_id)

        return JsonResponse({"success": True, "status": status})

    except Exception as e:
        logger.error(f"Status check error: {e}", exc_info=True)
        return JsonResponse({"success": False, "error": str(e)}, status=500)
