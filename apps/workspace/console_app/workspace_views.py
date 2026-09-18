"""
Code Workspace Views - Simple file editor with project tree.

Provides IDE-like interface for editing and running scripts.
Gets project from header dropdown (like Scholar/Writer).
"""

import logging

from django.shortcuts import redirect, render

from apps.infra.project_app.models import Project
from apps.infra.project_app.services import get_current_project

logger = logging.getLogger(__name__)


def code_workspace(request):
    """
    Main code workspace view - IDE interface.

    URL: /code/ (replaces index redirect)
    Gets project from header dropdown via get_current_project()

    Requires an authenticated account.
    """
    context = {
        "is_workspace_page": True,
        "module_name": "Code",
        "module_icon": "fa-code",
    }

    if not request.user.is_authenticated:
        return redirect("auth_app:signup")

    # Get current project from header dropdown
    current_project = get_current_project(request, user=request.user)

    if current_project:
        # Check if user can edit this project (owner or write/admin collaborator)
        if not current_project.can_edit(request.user):
            logger.info(
                "[Code] User %s cannot edit project %s, falling back to an owned project",
                request.user.username,
                current_project.slug,
            )
            current_project = Project.objects.filter(owner=request.user).first()
            if not current_project:
                context["needs_project_creation"] = True

        if current_project:
            context["current_project"] = current_project
            context["project"] = current_project
    else:
        context["needs_project_creation"] = True

    return render(request, "console_app/workspace.html", context)
