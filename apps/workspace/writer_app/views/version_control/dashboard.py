"""Version control index view."""

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from ...services import VersionControlService
from apps.infra.project_app.services import get_current_project
import logging

logger = logging.getLogger(__name__)


@login_required
def version_control_index(request):
    """Version control index.

    Shows:
    - Git commit history
    - Branches
    - Version tags
    - Diff viewer
    - Rollback options
    """
    current_project = get_current_project(request, user=request.user)

    context = {
        "project": current_project,
        "commits": [],
        "branches": [],
    }

    if current_project:
        try:
            vc_service = VersionControlService(current_project.id, request.user.id)
            commits = vc_service.get_history()
            branches = vc_service.get_branches()

            context["commits"] = commits
            context["branches"] = branches
        except Exception as e:
            logger.error(f"Error loading version control data: {e}")

    return render(request, "writer_app/version_control/index.html", context)
