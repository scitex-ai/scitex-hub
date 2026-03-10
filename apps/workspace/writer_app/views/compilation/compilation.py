"""Compilation status and history views."""

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from ...services import CompilerService
from apps.infra.project_app.services import get_current_project
import logging

logger = logging.getLogger(__name__)


@login_required
def compilation_view(request):
    """Compilation history and status index.

    Shows:
    - Recent compilation jobs
    - Job status (pending, running, completed, failed)
    - Compilation logs
    - PDF download links
    """
    current_project = get_current_project(request, user=request.user)

    context = {
        "project": current_project,
        "compilations": [],
    }

    if current_project:
        try:
            compilation_service = CompilerService(current_project.id, request.user.id)
            compilations = compilation_service.get_history()
            context["compilations"] = compilations
        except Exception as e:
            logger.error(f"Error loading compilation history: {e}")

    return render(request, "writer_app/compilation/compilation_view.html", context)
