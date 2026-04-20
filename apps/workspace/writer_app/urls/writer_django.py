"""Thin wrapper that consumes `scitex_writer._django` as the canonical writer.

Mirrors the `figrecipe_app/urls/figrecipe.py` pattern:
- `editor_page` and `api_dispatch` come from the writer package
- a small wrapper injects `working_dir` from the authenticated user's
  current project

This is the entry point for scitex-cloud#146 — the gradual cut-over from
the legacy in-repo writer UI to the shared `_django` implementation.

Lives alongside (not replacing) the old `writer_app/urls/editor.py` so the
switch can be flipped per-environment without destabilising production.
"""

from __future__ import annotations

import logging

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.urls import path
from scitex_writer._django.views import api_dispatch as _raw_api_dispatch
from scitex_writer._django.views import editor_page as _raw_editor_page
from scitex_writer._django.views import viewer_page as _raw_viewer_page

logger = logging.getLogger(__name__)


def _inject_project_context(request) -> None:
    """Ensure request.GET carries working_dir from the user's current project."""
    if not request.user.is_authenticated:
        return
    if request.GET.get("working_dir"):
        return
    try:
        from apps.infra.project_app.services.project_utils import (
            get_current_project,
        )
    except Exception:
        return

    project = get_current_project(request, user=request.user)
    if not project:
        return

    try:
        working_dir = str(project.get_local_path())
    except Exception as exc:
        logger.warning("[writer.v2] project.get_local_path() failed: %s", exc)
        return

    mutable = request.GET.copy()
    mutable["working_dir"] = working_dir
    request.GET = mutable


@login_required
def editor_page(request):
    _inject_project_context(request)
    return _raw_editor_page(request)


@login_required
def viewer_page(request):
    _inject_project_context(request)
    return _raw_viewer_page(request)


@login_required
def api_dispatch(request, endpoint):
    _inject_project_context(request)
    if not request.GET.get("working_dir"):
        return JsonResponse(
            {"error": "No working_dir resolved for the current user"},
            status=400,
        )
    return _raw_api_dispatch(request, endpoint)


urlpatterns = [
    path("editor-v2/", editor_page, name="writer_v2_editor"),
    path("viewer-v2/", viewer_page, name="writer_v2_viewer"),
    path("v2/<path:endpoint>", api_dispatch, name="writer_v2_api"),
]
