#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""URL dispatcher for published user-apps mounted under ``/apps/u/<module>/``.

F0+F1 (lead msg 5b5fbbce / operator-A pick): published user-apps need to
expose their own URL routes for cases like the M4 ReReviewBadge that
mounts ``scitex_live_paper.mount(resolver=...)`` from inside the user-
published ``scitex_live_paper_hub_app/urls.py``. The existing
``apps_app/urls.py`` is server-owned (catch-all on ``<str:module_name>/``)
so user-apps can't hang off it; this file is the orthogonal
URL-include dispatcher.

Flow per request to ``/apps/u/<module_name>/<sub_path>``:

  1. ``config/urls.py`` includes this module under
     ``path("apps/u/<str:module_name>/", include("apps.workspace.apps_app.urls_user_apps"))``.
  2. ``user_app_dispatch`` resolves ``module_name`` against the
     ``apps.workspace.apps_app.services.app_loader._URL_PATTERNS_CACHE``
     populated when ``load_single_app`` activated the app.
  3. The dispatcher rewrites the URL by stripping the
     ``/apps/u/<module_name>/`` prefix + dispatches into the user-app's
     own ``urlpatterns`` (loaded via ``entry_points["scitex_hub.apps"]``
     → ``<HUB_APP_NAME>.urls:urlpatterns``).
  4. Bundle / paper / project resolution happens inside the user-app's
     view callable (per the journal ``build_hub_resolver`` + live-paper
     ``mount`` contract).

Per the live-paper ``mount(resolver=...)`` exception-hierarchy contract
agreed in proj-scitex-hub msg b450c456:

  - ``BundleNotFound``        → 404
  - ``BundleAccessDenied``    → 403
  - ``BundleResolverError``   → 500
  - any other Exception       → 500 + log (no silent swallow, no leak)

The translation layer is small (one ``try / except``) and lives here
rather than each user-app re-implementing the same try-blocks.

Tests live at ``tests/custom/apps/apps_app/test_urls_user_apps.py``
+ exercise the real Django ``Client`` against a fixture user-app —
no mocks per STX-NM.
"""

from __future__ import annotations

import logging

from django.http import Http404, HttpRequest, HttpResponse, JsonResponse
from django.urls import URLResolver, path, re_path
from django.urls.resolvers import RegexPattern

# scitex-live-paper exception hierarchy — kept LAZY (top-level
# try/except + None fallback) because the package is not yet on PyPI
# and is therefore NOT declarable as a hard runtime dep in
# scitex-hub's pyproject.toml. PR #292 promoted this to a hard
# top-level import on the assumption that live-paper PR #47 had
# landed and the dep would be added — but the dep was never added,
# so every CI run (and any hub install without live-paper on the
# PYTHONPATH) broke Django startup at config/urls.py import time.
#
# Restoring the lazy guard. The dispatch logic below ``and`` checks
# `is not None` before isinstance(), so when live-paper IS installed
# the user-app exception-hierarchy translation works exactly as it
# did under #292; when it ISN'T installed, an unmapped exception just
# flows through the generic 500-with-logged-trace path (no live-paper
# user-app would be running anyway in that case).
#
# REVERT this back to a hard import (and drop the None checks below)
# once scitex-live-paper is published to PyPI AND declared as a
# scitex-hub runtime dep in pyproject.toml.
logger = logging.getLogger(__name__)

try:
    from scitex_live_paper import (
        BundleAccessDenied,
        BundleNotFound,
        BundleResolverError,
    )
except (
    Exception
) as _live_paper_import_err:  # noqa: BLE001 — STX-EH001: catch runtime-init too
    logger.debug(
        "[urls_user_apps] scitex_live_paper import failed (%s) — "
        "exception-hierarchy translation will skip via None checks",
        _live_paper_import_err,
    )
    BundleNotFound = None  # type: ignore[assignment]
    BundleAccessDenied = None  # type: ignore[assignment]
    BundleResolverError = None  # type: ignore[assignment]


def _dispatch(
    request: HttpRequest, module_name: str, sub_path: str = ""
) -> HttpResponse:
    """Look up ``module_name``'s urlpatterns + dispatch ``sub_path``."""
    from .services.app_loader import _URL_PATTERNS_CACHE

    patterns = _URL_PATTERNS_CACHE.get(module_name)
    if patterns is None:
        logger.info(
            "[urls_user_apps] No urlpatterns cached for '%s' — app not "
            "activated or never declared scitex_hub.apps entry-point",
            module_name,
        )
        raise Http404(
            f"user-app '{module_name}' is not active (no URL routes registered)"
        )

    # Build a one-shot URLResolver over the user-app's urlpatterns + try
    # to match the sub_path. Django's resolver consumes the leading "/"
    # internally; sub_path here is post-``<module_name>/`` (no leading
    # slash) so we restore it for the resolver.
    pseudo_resolver = URLResolver(
        RegexPattern(r"^"),
        patterns,
    )
    try:
        match = pseudo_resolver.resolve("/" + sub_path)
    except Exception:
        logger.info(
            "[urls_user_apps] No match for %r in %r patterns",
            "/" + sub_path,
            module_name,
        )
        raise Http404("no route in user-app")

    return _invoke(match.func, request, match.args, match.kwargs, module_name)


def _invoke(view, request, args, kwargs, module_name: str) -> HttpResponse:
    """Call the user-app view; translate live-paper exception hierarchy.

    SECURITY: never re-raises with a body — always returns a JsonResponse
    with a fixed-shape error payload. Stack-trace details live in the
    server logs only (logger.exception), never in the HTTP response, so
    a misbehaving user-app can't be probed for internals via crafted
    requests. Per CodeQL py/stack-trace-exposure fix on PR #290 v2.
    """
    # Resolver-side exception hierarchy per the contract pin
    # (live-paper PR #47). Lazy-imported at module top (None fallback
    # when scitex-live-paper isn't installed); the isinstance() checks
    # below short-circuit safely via the `is not None` guard so hub
    # boots clean without live-paper.
    try:
        return view(request, *args, **kwargs)
    except Exception as exc:  # noqa: BLE001 - mapped to a real HTTP surface
        if BundleNotFound is not None and isinstance(exc, BundleNotFound):
            return JsonResponse({"error": "not found", "kind": "not_found"}, status=404)
        if BundleAccessDenied is not None and isinstance(exc, BundleAccessDenied):
            return JsonResponse({"error": "forbidden", "kind": "forbidden"}, status=403)
        if BundleResolverError is not None and isinstance(exc, BundleResolverError):
            logger.exception(
                "[urls_user_apps] resolver error from user-app %r", module_name
            )
            return JsonResponse(
                {"error": "resolver error", "kind": "resolver_error"}, status=500
            )

        # Unmapped exception — log full trace server-side + return a
        # generic 500 to the caller (no body leak). Trace stays in
        # observability layer only.
        logger.exception(
            "[urls_user_apps] unmapped exception from user-app %r view",
            module_name,
        )
        return JsonResponse({"error": "internal error", "kind": "internal"}, status=500)


urlpatterns = [
    # Bare /apps/u/<module_name>/ -> sub_path = ""
    path("", _dispatch, {"sub_path": ""}, name="user_app_root"),
    # /apps/u/<module_name>/anything/here/...
    re_path(r"^(?P<sub_path>.+)$", _dispatch, name="user_app_path"),
]


# EOF
