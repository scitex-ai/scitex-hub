#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Public, anonymous, READ-ONLY live-paper viewer (scitex-hub#146 Part B).

Gap this closes
----------------
``apps/workspace/writer_app/urls/writer_django.py`` wraps
``scitex_writer._django.views.{editor_page,viewer_page,api_dispatch}`` for
the authenticated ``/apps/writer/{editor,viewer}-v2/`` routes, but every one
of those views is ``@login_required`` unconditionally. There was therefore
no way to host a project's live-paper viewer (claims + DAG + manuscript,
``register_livepaper_demo``'s target) publicly, e.g. for
``scitex.ai/<owner>/<project>/live/`` grant-material demos — the exact case
``paper-scitex-clew`` needs.

Design
------
``/<username>/<slug>/live/`` and ``/<username>/<slug>/live/v2/<endpoint>``
sit next to the existing GitHub-style ``/<username>/<slug>/`` project pages
and reuse the SAME ``@project_access_required`` decorator those already use
(``apps/infra/project_app/decorators.py``): it 404s (not 403 — a private
project must not even be revealed to exist) unless
``project.visibility == "public"``, regardless of whether the caller is
authenticated. That default-deny check runs BEFORE any of this module's
code, so every view below can assume ``request.project`` is public.

``working_dir`` is resolved from the (already-authorised) ``request.project``
alone via the SAME ``WorkingDirScopedView`` the authenticated writer-v2
wrapper uses (``apps.infra.project_app.services.working_dir_resolver`` —
only the ``resolver`` collaborator differs: theirs reads
``request.user``'s current project, this one reads the slug-resolved
``request.project`` already set by the decorator). Reusing it means the
caller's own ``?working_dir=`` is discarded and overwritten, never merged,
by the exact code path already covered by
``tests/security/test_writer_v2_working_dir_override.py`` (card
``sec-working-dir-passthrough-family`` SITE 1) — trusting a client-supplied
absolute path here would turn a public, anonymous URL into an arbitrary
host-path read.

The API surface is GET-only. ``scitex_writer._django.views.api_dispatch``
already gates each handler by an allowed-methods table, but this route is
reachable by literally anyone with no session at all, so the write path is
also cut off at this boundary as defense in depth — it must stay true even
if a future HANDLERS entry in the upstream package is added carelessly.
"""

from __future__ import annotations

import logging
from importlib.util import find_spec

from django.http import Http404, JsonResponse

from ...decorators import project_access_required
from ...services.working_dir_resolver import WorkingDirScopedView

logger = logging.getLogger(__name__)


def _writer_installed() -> bool:
    """True when scitex-writer's ``_django`` app is importable.

    Mirrors the guarded import in ``writer_app/urls/__init__.py`` so this
    route 404s cleanly (instead of raising ImportError out of the urlconf)
    in an environment where scitex-writer is not installed.
    """
    try:
        return find_spec("scitex_writer._django") is not None
    except ModuleNotFoundError:
        return False


def _resolve_from_request_project(request):
    """``WorkingDirScopedView`` resolver: the slug-resolved ``request.project``.

    ``request.project`` is set by ``@project_access_required`` and has
    ALREADY been visibility-checked (public, or owned/staff — see module
    docstring) before this ever runs. Returns ``None`` (never raises) so
    the caller's ``WorkingDirScopedView(fail_closed=True)`` turns a missing
    or unresolvable path into its own explicit 404 rather than this
    function partially handling the failure.
    """
    project = getattr(request, "project", None)
    if project is None:  # pragma: no cover - decorator always sets this
        return None
    try:
        return project.get_local_path().resolve()
    except Exception:
        logger.warning(
            "[live_viewer] get_local_path() failed for project id=%s",
            getattr(project, "pk", "?"),
        )
        return None


def _on_missing_404(request):
    raise Http404("Project not found")


@project_access_required
def project_live_viewer(request, username, slug):
    """``/<username>/<slug>/live/`` — the public read-only paper viewer page."""
    if not _writer_installed():
        raise Http404("Live-paper viewer is not available")

    from scitex_writer._django.views import viewer_page as _raw_viewer_page

    view = WorkingDirScopedView(
        _raw_viewer_page,
        resolver=_resolve_from_request_project,
        on_missing=_on_missing_404,
    )
    return view(request)


@project_access_required
def project_live_viewer_api(request, username, slug, endpoint):
    """``/<username>/<slug>/live/v2/<endpoint>`` — GET-only data for the viewer."""
    if request.method != "GET":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    if not _writer_installed():
        raise Http404("Live-paper viewer is not available")

    from scitex_writer._django.views import api_dispatch as _raw_api_dispatch

    view = WorkingDirScopedView(
        _raw_api_dispatch,
        resolver=_resolve_from_request_project,
        on_missing=_on_missing_404,
    )
    return view(request, endpoint)


# EOF
