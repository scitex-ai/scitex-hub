"""FigRecipe app views — thin wrapper for workspace mount."""

import logging

from django.shortcuts import redirect, render

from apps.infra.project_app.services.project_scope import project_for_scope_app

logger = logging.getLogger(__name__)


def figure_editor(request, figrecipe_embedded=False):
    """Main figure editor — mounts figrecipe React editor.

    Requires an authenticated account.
    """
    if not request.user.is_authenticated:
        return redirect("auth_app:signup")

    context = {
        "module_name": "FigRecipe",
        "module_icon": "fa-chart-line",
        "is_workspace_page": True,
        "figrecipe_embedded": figrecipe_embedded,
        # Generic app editor context (used by shared/app_editor.html)
        "app_slug": "figrecipe",
        "app_label": "FigRecipe",
        "app_mount_css": "figrecipe_app/css/figrecipe-mount.css",
        "bridge_entry_name": "figrecipe_app/figrecipe-bridge-init",
    }


    # Project-scope pilot: ?project=owner/slug wins, else the last visited project.
    current_project = project_for_scope_app(request)
    if current_project:
        context["current_project"] = current_project
        context["project"] = current_project
    else:
        context["needs_project_creation"] = True

    return render(request, "figrecipe_app/editor.html", context)


def build_figrecipe_context(request, current_project=None):
    """Context builder for workspace content endpoint (partial rendering)."""
    context = {
        "app_slug": "figrecipe",
        "app_label": "FigRecipe",
        "app_mount_css": "figrecipe_app/css/figrecipe-mount.css",
        "bridge_entry_name": "figrecipe_app/figrecipe-bridge-init",
        "current_project": current_project,
    }
    if not current_project:
        context["needs_project_creation"] = True
    return context
