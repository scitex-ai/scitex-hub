"""Vis app URLs - figrecipe editor integration.

Delegates to figrecipe._django with project-context injection.
"""

from __future__ import annotations

from django.urls import path
from figrecipe._django.views import api_dispatch as _raw_api_dispatch
from figrecipe._django.views import editor_page


def _inject_project_context(request):
    """Inject working_dir from user's current project into GET params."""
    from apps.infra.project_app.services.project_utils import get_current_project

    if not request.user.is_authenticated:
        return
    if request.GET.get("working_dir"):
        return

    project = get_current_project(request, user=request.user)
    if project:
        mutable_get = request.GET.copy()
        mutable_get["working_dir"] = str(project.get_local_path())
        request.GET = mutable_get


def api_dispatch_with_context(request, endpoint):
    """Wrap figrecipe._django.views.api_dispatch with project context."""
    _inject_project_context(request)
    return _raw_api_dispatch(request, endpoint)


urlpatterns = [
    path("figrecipe/", editor_page, name="figrecipe_editor"),
    path("figrecipe/<path:endpoint>", api_dispatch_with_context, name="figrecipe_api"),
]


# EOF
