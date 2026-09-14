"""Thin wrapper that consumes `scitex_writer._django` as the canonical writer.

Mirrors the `figrecipe_app/urls/figrecipe.py` pattern:
- `editor_page`, `viewer_page` and `api_dispatch` come from the writer package
- a small wrapper (WorkingDirScopedView) injects `working_dir` from the
  authenticated user's current project

This is the entry point for scitex-hub#146 — the gradual cut-over from
the legacy in-repo writer UI to the shared `_django` implementation.

SECURITY (card sec-working-dir-passthrough-family, SITE 1)
----------------------------------------------------------
`working_dir` is derived EXCLUSIVELY from the authenticated user's current
project and OVERWRITES any caller-supplied value. It used to early-return
when the caller already supplied `?working_dir=`, which passed an
attacker-chosen absolute path straight through to
`scitex_writer._django.services.get_or_create_project` — no ownership and
no containment check downstream, so it read (and, via
`ensure_scholar_library_link`, WROTE a symlink into) ANY existing host
directory. Now the caller value is discarded and the request fails closed
when no project resolves.
"""

from __future__ import annotations

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import redirect
from django.urls import path
from scitex_writer._django.views import api_dispatch as _raw_api_dispatch
from scitex_writer._django.views import editor_page as _raw_editor_page
from scitex_writer._django.views import viewer_page as _raw_viewer_page

from apps.infra.project_app.services.working_dir_resolver import (
    WorkingDirScopedView,
)


def _no_project_json(request):
    return JsonResponse(
        {
            "error": (
                "No active project resolved for your account — the writer "
                "operates on your project workspace. Create or open a "
                "project first."
            ),
            "hint": "/new/",
        },
        status=404,
    )


def _no_project_redirect(request):
    return redirect("/new/")


_editor_view = WorkingDirScopedView(_raw_editor_page, on_missing=_no_project_redirect)
_viewer_view = WorkingDirScopedView(_raw_viewer_page, on_missing=_no_project_redirect)
_api_view = WorkingDirScopedView(_raw_api_dispatch, on_missing=_no_project_json)


@login_required
def editor_page(request):
    # Stamp the app-scope marker the leaf bundle's mountProjectSelectorByScope
    # reads (d8528de contract). This bridge calls the raw leaf editor_page (not
    # scitex-app's scitex_editor_page host view), so the marker is not injected
    # upstream — this is the one place the hub applies the shared contract.
    # (Writer's leaf consumer is a separate Writer-owned follow-up; the marker
    # is correct to emit regardless — user/absent scope would be a no-op.)
    response = _editor_view(request)
    from apps.infra.workspace_app.scope_meta import inject_scope_meta
    return inject_scope_meta(response, "writer")


@login_required
def viewer_page(request):
    response = _viewer_view(request)
    from apps.infra.workspace_app.scope_meta import inject_scope_meta
    return inject_scope_meta(response, "writer")


@login_required
def api_dispatch(request, endpoint):
    return _api_view(request, endpoint)


urlpatterns = [
    path("editor-v2/", editor_page, name="writer_v2_editor"),
    path("viewer-v2/", viewer_page, name="writer_v2_viewer"),
    path("v2/<path:endpoint>", api_dispatch, name="writer_v2_api"),
]
