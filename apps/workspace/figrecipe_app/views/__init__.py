"""FigRecipe app views — thin wrapper for workspace mount."""

import logging

from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from apps.infra.project_app.services.project_utils import get_current_project

logger = logging.getLogger(__name__)


def figure_editor(request, figrecipe_embedded=False):
    """Main figure editor — mounts figrecipe React editor.

    If visitor pool is exhausted, redirect to visitor-pool-full page.
    """
    if not request.user.is_authenticated:
        user_agent = request.META.get("HTTP_USER_AGENT", "")
        is_browser = any(
            browser in user_agent
            for browser in ["Mozilla", "Chrome", "Safari", "Firefox", "Edge", "Opera"]
        )
        if is_browser:
            return redirect("public_app:visitor_pool_full")
        return render(
            request,
            "figrecipe_app/editor.html",
            {"is_visitor": True, "figrecipe_embedded": figrecipe_embedded},
        )

    context = {
        "module_name": "FigRecipe",
        "module_icon": "fa-chart-line",
        "is_workspace_page": True,
        "figrecipe_embedded": figrecipe_embedded,
    }

    if request.user.username.startswith("visitor-"):
        context["is_demo"] = True
        context["visitor_username"] = request.user.username

    current_project = get_current_project(request, user=request.user)
    if current_project:
        context["current_project"] = current_project
        context["project"] = current_project
    else:
        context["needs_project_creation"] = True

    return render(request, "figrecipe_app/editor.html", context)
