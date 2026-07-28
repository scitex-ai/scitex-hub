#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tenancy + phase-1 read-only guard for the mounted scitex-todo board.

The upstream ``scitex_cards._django`` board resolves its task store through
a per-request ``?store=`` seam (``views._tasks_path_from_request``); with
no ``store`` param it falls back to the HOST store (``~/.scitex/todo/
tasks.yaml``) — correct standalone, a cross-tenant leak on the hub.

This middleware makes the mount multi-tenant while keeping Django thin
(zero board logic lives here — only path resolution + a method gate):

1. **Never trust the client** — an inbound ``?store=`` is discarded
   (logged), so no client-controlled path ever reaches the board's
   loader (path-traversal seam closed).
2. **Server-side store resolution** — the active project is resolved via
   the canonical ``get_current_project`` helper (which enforces
   ``can_view``), and the injected store is
   ``<workspace>/<project>/.scitex/todo/tasks.yaml`` — the file the
   existing three-way sync already maintains. The resolved path is
   validated to sit inside the owning workspace base before injection.
3. **Phase 1 is read-only** — every non-GET/HEAD/OPTIONS request under
   ``/todo/`` is rejected: readonly visitors get the structured #308
   write-rejection payload; everyone else gets an explicit
   ``todo-board-readonly-phase1`` 403 (no silent fallback — the board's
   own mutating handlers are POST-only, so this gate covers all of them,
   including the csrf_exempt ``api_dispatch`` catch-all and the
   ``hooks/*`` + ``dm/*`` + ``chat/*`` POST surfaces).

Runs LAST in the request phase (after Authentication + VisitorAutoLogin)
so ``request.user`` is final, and no-ops in one prefix check for every
non-``/todo/`` request.
"""

from __future__ import annotations

import logging
from importlib.util import find_spec
from pathlib import Path

from django.http import JsonResponse
from django.shortcuts import redirect

logger = logging.getLogger(__name__)

# Must track the mount in config/urls.py. The board moved from the bare /todo/
# to /apps/todo/ and then to /apps/cards/ (Cards rebrand); if these drift, the
# tenancy injection silently stops firing and the board would fall back to the
# HOST store — i.e. one user seeing another's tasks. Keep them in lockstep.
# The /apps/todo/ legacy path needs no entry here: urls.py 301-redirects it
# to /apps/cards/ before any board view runs.
_TODO_ROOT = "/apps/cards"
_TODO_PREFIX = "/apps/cards/"
_READ_METHODS = ("GET", "HEAD", "OPTIONS")

# The upstream board routes that render HTML pages a browser NAVIGATES to
# (board root, chat/DM page, legacy + board-v3 aliases); every other
# subpath is a JS data endpoint (timeline, fleet/*, dm/*, chat/<id>, the
# api_dispatch catch-all). Tracks scitex_cards._django.urls in lockstep,
# same contract as _TODO_PREFIX above.
# WHY path, not headers: the board's fetches send no JSON Accept header
# and non-browser clients omit Sec-Fetch-Mode — the path is the only
# discriminator present on every request.
_PAGE_PATHS = frozenset(
    {
        _TODO_ROOT,
        _TODO_PREFIX,
        _TODO_PREFIX + "chat",
        _TODO_PREFIX + "legacy",
        _TODO_PREFIX + "legacy/",
        _TODO_PREFIX + "board-v3",
        _TODO_PREFIX + "board-v3/",
    }
)

# Mirror of the guarded import in settings_shared.py / the URL guard in
# config/urls.py — when the package is absent the mount does not exist
# and this middleware must not intercept the path (it falls through to
# the GitHub-style username catch-all, same as /writer/).
_TODO_INSTALLED = (
    find_spec("scitex_cards") is not None or find_spec("scitex_todo") is not None
)


class TodoBoardTenancyMiddleware:
    """Scope every ``/todo/`` request to the requester's workspace store."""

    sync_capable = True

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path
        if not _TODO_INSTALLED or not (
            path == _TODO_ROOT or path.startswith(_TODO_PREFIX)
        ):
            return self.get_response(request)

        # --- Phase-1 write gate (read-only board) --------------------
        if request.method not in _READ_METHODS:
            return self._write_rejection(request)

        # --- Tenancy: server-side store resolution -------------------
        user = getattr(request, "user", None)
        if user is None or not user.is_authenticated:
            # VisitorAutoLoginMiddleware normally leaves no anonymous
            # sessions; if one still reaches us, page navigations go to
            # login, while data fetches get shaped 401 JSON — a redirect
            # would hand the login page's HTML to the board JS's JSON
            # parser (the board renders a signed-out panel from this
            # payload instead).
            if path in _PAGE_PATHS:
                return redirect(f"/auth/login/?next={path}")
            return JsonResponse(
                {
                    "error": "signed-out",
                    "login_url": f"/auth/login/?next={_TODO_PREFIX}",
                },
                status=401,
            )

        store = self._resolve_workspace_store(request)
        if store is None:
            return JsonResponse(
                {
                    "error": (
                        "No active project — the todo board shows your "
                        "project workspace store. Create or open a "
                        "project first."
                    ),
                    "hint": "/new/",
                },
                status=404,
            )

        if "store" in request.GET:
            logger.warning(
                "[todo-mount] discarding client-supplied ?store= from "
                "user %s (server-side tenancy only)",
                user.username,
            )
        params = request.GET.copy()
        params["store"] = str(store)
        request.GET = params

        return self.get_response(request)

    # -----------------------------------------------------------------
    @staticmethod
    def _resolve_workspace_store(request) -> Path | None:
        """Workspace tasks.yaml for the requester's active project.

        Returns ``None`` when no project resolves. The path is computed
        exclusively from server-side data (DB slug + settings BASE_DIR)
        and containment-validated against the owning workspace base.
        """
        from apps.infra.project_app.services.filesystem.paths import (
            get_org_base_path,
            get_user_base_path,
        )
        from apps.infra.project_app.services.project_utils import (
            get_current_project,
        )

        project = get_current_project(request, user=request.user)
        if project is None:
            return None

        if project.is_org_owned:
            base = get_org_base_path(project.org_owner)
        else:
            base = get_user_base_path(project.owner)

        store = base / project.slug / ".scitex" / "todo" / "tasks.yaml"

        # Belt-and-braces: the slug is a validated DB field, but the
        # injected path must provably stay inside the workspace base.
        if not store.resolve().is_relative_to(base.resolve()):
            logger.error(
                "[todo-mount] resolved store %s escapes workspace base "
                "%s — refusing",
                store,
                base,
            )
            return None
        return store

    @staticmethod
    def _write_rejection(request):
        """403 for any mutating request under /todo/ (phase 1)."""
        from apps.infra.project_app.services.visitor_pool import (
            is_readonly_visitor,
            readonly_write_rejection,
        )

        if is_readonly_visitor(request):
            # Structured #308 payload → the shared frontend guard turns
            # it into the Sign up / Log in toast.
            return readonly_write_rejection(
                "edit the todo board", request=request
            )
        return JsonResponse(
            {
                "error": (
                    "The todo board is read-only on the hub (phase 1). "
                    "Edit tasks via the scitex-todo CLI/MCP in your "
                    "workspace; hub-side editing arrives in a later "
                    "phase."
                ),
                "reason": "todo-board-readonly-phase1",
            },
            status=403,
        )


# EOF
