"""
Code Workspace Views - Simple file editor with project tree.

Provides IDE-like interface for editing and running scripts.
Gets project from header dropdown (like Scholar/Writer).
"""

import logging
from django.shortcuts import render, redirect
from django.http import HttpResponse
from apps.project_app.services import get_current_project
from apps.project_app.models import Project

logger = logging.getLogger(__name__)


def code_workspace(request):
    """
    Main code workspace view - IDE interface.

    URL: /code/ (replaces index redirect)
    Gets project from header dropdown via get_current_project()

    Visitor auto-login is handled by VisitorAutoLoginMiddleware.
    If visitor pool is exhausted, redirect to visitor-pool-full page.
    """
    context = {
        "is_visitor": not request.user.is_authenticated,
        "module_name": "Code",
        "module_icon": "fa-code",
    }

    # Check if user is not authenticated (visitor allocation may have failed)
    if not request.user.is_authenticated:
        # Check if this is a browser request (has typical browser User-Agent)
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        is_browser = any(
            browser in user_agent
            for browser in ['Mozilla', 'Chrome', 'Safari', 'Firefox', 'Edge', 'Opera']
        )

        if is_browser:
            # Browser request but not authenticated - visitor pool likely exhausted
            logger.info("[Code] Browser request not authenticated - redirecting to visitor-pool-full")
            return redirect('public_app:visitor_pool_full')

        # Non-browser request (API, bot, etc.) - just return the page
        return render(request, "console_app/workspace.html", context)

    if request.user.is_authenticated:
        # Mark as demo if visitor
        if request.user.username.startswith("visitor-"):
            context["is_demo"] = True
            context["visitor_username"] = request.user.username

        # Get current project from header dropdown
        current_project = get_current_project(request, user=request.user)

        if current_project:
            # Check if user can edit this project (owner or write/admin collaborator)
            if not current_project.can_edit(request.user):
                # User can view but not edit - fall back to their own projects
                logger.info(
                    f"[Code] User {request.user.username} cannot edit project {current_project.slug}, "
                    f"falling back to user's own projects"
                )
                current_project = Project.objects.filter(owner=request.user).first()
                if not current_project:
                    # User has no projects - show creation prompt
                    context["needs_project_creation"] = True

            if current_project:
                context["current_project"] = current_project
                context["project"] = current_project
        else:
            # User authenticated but no project selected
            context["needs_project_creation"] = True

    return render(request, "console_app/workspace.html", context)
