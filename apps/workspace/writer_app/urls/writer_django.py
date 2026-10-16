#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: apps/workspace/writer_app/urls/writer_django.py
"""Mount `scitex_writer._django` as the canonical writer UI, BEHIND HUB'S AUTH.

CUTOVER + OPERATOR ROUTE RULE (CCT 2763/2764) + RED START (CCT 2806, binding):
``/apps/writer/`` serves the WRITER LEAF plugin and only the leaf. The plain
hub-side routes went dark first (404) and the plain route is relit ONLY by
the working leaf through the wrapper below — no app earns its route back
without one. The pre-cutover hub-native surface (feature pages + the v2
SITE-3 wrapper paths) lives in ``legacy.py`` and is served ONLY at
``/apps/writer/old-direct/`` in dev (mount + gate in ``config/urls.py``),
never in production, and old-direct is deleted outright once v1 parity
closes. Scholar #1074 / FigRecipe #1075 template. No ``/v2/``-style alias is
added (CCT 2795 lesson): the leaf is mounted ONCE at the root; resolve() by
path is what matters.

Mirrors the `figrecipe_app/urls/figrecipe.py` SITE pattern:
- `editor_page`, `viewer_page` and `api_dispatch` come from the writer package
- a small wrapper (WorkingDirScopedView) injects `working_dir` from the
  authenticated user's current project

WHY THE SITE-3 WRAPPER STAYS ON THE DEFAULT PATH (kept with reasons)
--------------------------------------------------------------------
Scholar's cutover wrapper is login-only (scholar has no filesystem inputs)
and FigRecipe's is login-only on the default because the 0.36 leaf jails
every path channel itself (`prepare_request` + manifest `mount_policy`
figrecipe#456, proven before the handover). NEITHER holds for writer yet:

* The leaf STILL reads `working_dir` from the request
  (`scitex_writer/_django/views.py`: ``request.GET.get("working_dir")``,
  still present on writer develop at the cutover). A login-only default
  would re-open SITE 1 of card sec-working-dir-passthrough-family
  (caller-supplied absolute path straight to `get_or_create_project` —
  the exact hole this module closed).
* The leaf's jail declaration (`mount_policy {login_required,
  touches_files, jail}`) is brand new (writer #438, unreleased at the
  cutover) and unproven from hub's side. Thinning the hub guard on the
  strength of an unshipped declaration would be trust, not verification —
  the FigRecipe thinning is likewise a SAC-manager call, not this move.

So the default wraps the leaf's `?working_dir=`-reading routes
(`editor`, `viewer`, `api`) in the SAME WorkingDirScopedView + login +
Origin-check stack that served the v2 paths before — byte-identical
behaviour, only the mount prefix moved (see `v2_urlpatterns` below).

TWO TREATMENTS, KEYED BY LEAF ROUTE NAME (not by position)
----------------------------------------------------------
Routes the leaf authorizes itself (`api/project/<id>/section/...`,
`api/project/<id>/manuscript-status/`) carry the leaf's own
`@project_boundary(project_from_url=True)`: SDK host project authority +
CSRF, 401 for anonymous, 503 when the host capability is absent. Hub MUST
NOT inject `working_dir` for them — the URL `project_id` is the selector,
and overwriting it with the current-project dir (or failing closed when no
current project resolves) would corrupt cross-project access the leaf just
authorized. Those routes get hub `login_required` ONLY (defence in depth;
the leaf 401s anonymous itself) and keep the leaf's csrf decision.

Every other KNOWN leaf route reads `?working_dir=` and gets the full
SITE-3 stack. A leaf route hub does not know is OMITTED (logged at ERROR),
not mounted login-only: mounting an unknown `?working_dir=` reader without
injection would silently re-open SITE 1, while omitting fails closed (404)
and the known-set test below fails loudly in CI. This deliberately differs
from scholar/figrecipe (which refuse the whole urlconf): the writer leaf is
mid-migration and the hub floor trails PyPI, so a leaf addition must darken
one path, never 500 the whole site (the #687 lesson).

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

import logging

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import redirect
from django.urls import URLPattern, URLResolver, include, path

logger = logging.getLogger(__name__)

# WHY THIS IMPORT IS GUARDED — a MEASURED outage, not a hypothetical.
#
# This module is imported by writer_app/urls/__init__.py, which
# config/urls.py imports to build the ROOT urlconf. A module-scope ImportError
# here therefore does not disable writer — it takes down EVERY URL hub
# serves, including the landing page. Scholar measured exactly this on
# 2026-08-23 (#687): an editable-install skew between scitex-scholar and
# scitex-app 500'd the whole site minutes after merge.
#
# NOT A SILENT FALLBACK (CCT 2768, binding). The failure is logged at ERROR
# with the exception and the routes are omitted, so /apps/writer/* 404s
# fail-closed while the dev-only /apps/writer/old-direct/ hub-native
# reference is unaffected (its v2 paths are leaf-backed and go dark too —
# see v2_urlpatterns — but the hub-native feature surface still serves).
# Hub already uses exactly this shape for optional plugin mounts
# (config/urls.py: "Only mounted when the package is importable"). The user
# path is NEVER relit with hub-side views — no app earns its route back
# without a working leaf plugin (RED START, CCT 2806).
try:
    import scitex_writer._django.urls as _leaf_urls
    from scitex_writer._django.views import api_dispatch as _raw_api_dispatch
    from scitex_writer._django.views import editor_page as _raw_editor_page
    from scitex_writer._django.views import viewer_page as _raw_viewer_page
except Exception as exc:  # noqa: BLE001 - any import-time failure must be caught
    _leaf_urls = None
    _raw_api_dispatch = None
    _raw_editor_page = None
    _raw_viewer_page = None
    _LEAF_IMPORT_ERROR = exc
else:
    _LEAF_IMPORT_ERROR = None

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


_SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS", "TRACE"})


def _is_cross_origin_write(request):
    # Browsers always send Origin on a cross-site POST; a missing header means
    # a non-browser client, which cannot ride the victim's session anyway.
    if request.method in _SAFE_METHODS:
        return False
    origin = request.headers.get("Origin")
    if origin is None:
        return False
    same = f"{request.scheme}://{request.get_host()}"
    return origin != same and origin not in settings.CSRF_TRUSTED_ORIGINS


@login_required
def api_dispatch(request, endpoint):
    if _is_cross_origin_write(request):
        return JsonResponse({"error": "Cross-origin request refused"}, status=403)
    return _api_view(request, endpoint)


# The writer's bundled frontend sends no CSRF token, so the leaf marks
# api_dispatch csrf_exempt; follow the leaf's decision (functools.wraps and
# login_required do not carry it) and rely on the Origin check above instead.
api_dispatch.csrf_exempt = getattr(_raw_api_dispatch, "csrf_exempt", False)


class ImproperlyGatedURLConf(RuntimeError):
    """The upstream urlconf has a shape this module cannot authenticate."""


# Leaf routes that read `?working_dir=`: hub injects it server-side (SITE-3).
# Every other KNOWN leaf route authorizes itself via the leaf's own
# `@project_boundary` (SDK host capability) and gets login_required only.
_SITE3_VIEW_BY_LEAF_NAME = {
    "editor": editor_page,
    "viewer": viewer_page,
    "api": api_dispatch,
}

# The complete leaf route-name set this module knows how to serve, by
# treatment. A leaf route outside this set is OMITTED (fail-closed, logged);
# `test_writer_route_flip_parity` pins the set so an upstream addition fails
# loudly in CI instead of silently changing treatment. Derived from the leaf:
# 2.43.6 ships {editor, viewer, api}; 2.43.9 adds {api_section,
# api_manuscript_status} (writer #438) AND the v2_* twins
# {writer_v2_editor, writer_v2_viewer, writer_v2_api,
# writer_v2_api_section, writer_v2_api_manuscript_status} — same callbacks,
# same paths, leaf-namespace aliases the leaf itself publishes. The twins get
# the SAME treatment as their primaries (SITE-3 for the ?working_dir=
# readers, login-only for the leaf-authorized pair) so both spellings behave
# identically; omission would darken one spelling while the other serves.
_V2_TWIN_SITE3 = {
    "writer_v2_editor": "editor",
    "writer_v2_viewer": "viewer",
    "writer_v2_api": "api",
}
_V2_TWIN_AUTHORIZED = {
    "writer_v2_api_section": "api_section",
    "writer_v2_api_manuscript_status": "api_manuscript_status",
}
_KNOWN_LEAF_ROUTE_NAMES = frozenset(
    set(_SITE3_VIEW_BY_LEAF_NAME)
    | {"api_section", "api_manuscript_status"}
    | set(_V2_TWIN_SITE3)
    | set(_V2_TWIN_AUTHORIZED)
)


def _leaf_view_for(entry: URLPattern):
    """Return the hub-served callback for one leaf URLPattern, or None to omit.

    SITE-3 routes are rebound to this module's injection views (same function
    objects that served the v2 paths — byte-identical behaviour); leaf-
    authorized routes are login-wrapped in place with the leaf's csrf
    decision preserved.
    """
    if entry.name in _SITE3_VIEW_BY_LEAF_NAME:
        return _SITE3_VIEW_BY_LEAF_NAME[entry.name]
    if entry.name in _V2_TWIN_SITE3:
        # v2_* twin of a SITE-3 primary: same injection views, never the raw
        # leaf callback (which would read caller-supplied ?working_dir=).
        return _SITE3_VIEW_BY_LEAF_NAME[_V2_TWIN_SITE3[entry.name]]
    if entry.name in _KNOWN_LEAF_ROUTE_NAMES:
        callback = login_required(entry.callback)
        # Preserve the leaf's csrf decision (functools.wraps/login_required
        # do not carry csrf_exempt; the leaf's project_boundary sets its own
        # csrf_protect, and an exempt leaf view must stay exempt here or its
        # own frontend POSTs 403).
        callback.csrf_exempt = getattr(entry.callback, "csrf_exempt", False)
        return callback
    logger.error(
        "[writer_app] omitting unknown writer leaf route %r (name=%r): "
        "no treatment is defined for it, so it is NOT mounted. Classify it "
        "in _KNOWN_LEAF_ROUTE_NAMES (SITE-3 injection vs leaf-authorized) "
        "before it can serve.",
        str(entry.pattern),
        entry.name,
    )
    return None


def _build_leaf_patterns():
    """Assemble the cutover default from the installed leaf's own urlconf."""
    gated = []
    for entry in _leaf_urls.urlpatterns:
        if isinstance(entry, URLResolver):
            raise ImproperlyGatedURLConf(
                "scitex_writer._django.urls now nests an include(); "
                "decorating the resolver would leave the routes inside it "
                "UNAUTHENTICATED. Gate them explicitly before mounting."
            )
        if not isinstance(entry, URLPattern):
            raise ImproperlyGatedURLConf(
                f"unexpected urlconf entry {entry!r} ({type(entry).__name__}); "
                "refusing to mount something this module cannot gate."
            )
        callback = _leaf_view_for(entry)
        if callback is None:
            continue  # unknown route: fail-closed per-route (see module docstring)
        gated.append(
            URLPattern(
                entry.pattern,
                callback,
                entry.default_args,
                entry.name,
            )
        )
    return gated


if _LEAF_IMPORT_ERROR is not None:
    logger.error(
        "scitex-writer's Django app could not be imported, so /apps/writer/ "
        "is NOT mounted. The dev-only "
        "/apps/writer/old-direct/ hub-native reference is unaffected "
        "(its leaf-backed v2 paths go dark with the leaf — fail-closed, no "
        "silent fallback). Cause: %r. Check "
        "that the installed scitex-writer and its own dependencies agree — "
        "note that editable installs from bind-mounted working trees ignore "
        "hub's pyproject floors entirely.",
        _LEAF_IMPORT_ERROR,
    )
    urlpatterns = []
    # The v2 paths ARE the SITE-3 views over leaf views: with no leaf there
    # is nothing behind them. [] (fail-closed), never hub-native content.
    v2_urlpatterns = []
else:
    # One gated copy, mounted once: the cutover default at "" (=
    # /apps/writer/). No alias mount (CCT 2795 lesson): the leaf's names
    # travel inside the single mount, so reverse() stays unambiguous under
    # the one writer-leaf namespace.
    assert _leaf_urls is not None  # else-branch: the import above succeeded
    urlpatterns = [
        path(
            "",
            include((_build_leaf_patterns(), "writer"), namespace="writer-leaf"),
        ),
    ]
    # CUTOVER: the pre-cutover v2 paths (editor-v2/, viewer-v2/,
    # v2/<endpoint>) served ONLY at /apps/writer/old-direct/ in dev now
    # (assembled into the mount by urls/legacy.py), never on the user path.
    v2_urlpatterns = [
        path("editor-v2/", editor_page, name="writer_v2_editor"),
        path("viewer-v2/", viewer_page, name="writer_v2_viewer"),
        path("v2/<path:endpoint>", api_dispatch, name="writer_v2_api"),
    ]
