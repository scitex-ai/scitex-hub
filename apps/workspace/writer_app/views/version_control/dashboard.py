"""Version control dashboard view."""

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from ...services import WriterService
from apps.infra.project_app.services import get_current_project
import logging

logger = logging.getLogger(__name__)


@login_required
def version_control_index(request):
    """Version control dashboard.

    Shows:
    - Git commit history
    - Branches
    - Repository status
    - Diff viewer
    """
    current_project = get_current_project(request, user=request.user)

    context = {
        "project": current_project,
        "commits": [],
        "branches": [],
        "status": None,
        "current_branch": "main",
    }

    if current_project:
        try:
            writer_service = WriterService(current_project.id, request.user.id)
            git = writer_service.git_service

            commits = git.get_commit_history(max_count=20)
            for commit in commits:
                commit["date"] = commit["date"].isoformat()
            context["commits"] = commits

            branches = git.get_branches()
            context["branches"] = branches

            status = git.get_status()
            context["status"] = status
            context["current_branch"] = status.get("branch", "main")
        except Exception as e:
            logger.error(f"Error loading version control data: {e}")

    return render(request, "writer_app/version_control/index.html", context)
