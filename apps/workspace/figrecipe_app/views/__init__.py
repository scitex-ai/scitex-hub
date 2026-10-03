"""FigRecipe app views — thin wrapper for workspace mount."""

import logging
from pathlib import Path

from django.shortcuts import redirect, render
from django.urls import reverse

from apps.infra.project_app.services.project_scope import project_for_scope_app

logger = logging.getLogger(__name__)


def _selected_project_root(project):
    """Resolve this already-authorized selected project without a fallback."""
    if project is None:
        return None
    try:
        return Path(project.get_local_path()).resolve()
    except Exception as exc:
        logger.warning("[figrecipe] selected project root is unavailable: %s", exc)
        return None


def _resolve_figrecipe_working_dir(request):
    """Bind FigRecipe APIs to the same authorized selection as its editor."""
    user = getattr(request, "user", None)
    if user is None or not user.is_authenticated:
        return None
    return _selected_project_root(project_for_scope_app(request))


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
        "stx_mount_prefix": reverse("figrecipe_app:figrecipe_editor").rstrip("/"),
    }


    # Project-scope pilot: ?project=owner/slug wins, else the last visited project.
    current_project = project_for_scope_app(request)
    context["working_dir"] = str(_selected_project_root(current_project) or "")
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
        "stx_mount_prefix": reverse("figrecipe_app:figrecipe_editor").rstrip("/"),
        "current_project": current_project,
        "working_dir": str(_selected_project_root(current_project) or ""),
    }
    if not current_project:
        context["needs_project_creation"] = True
    return context
