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
   The store is published on ``request.scitex_store``. It is ALSO still
   written into ``request.GET`` during the migration window — see the
   comment at the injection site. The query channel is deprecated: it
   makes our injected value indistinguishable from a hostile ``?store=``
   for anything downstream, which is why rule 1 has to exist at all.
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
import re
from importlib.util import find_spec
from pathlib import Path

from django.http import JsonResponse
from django.middleware.csrf import CsrfViewMiddleware
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

# The ONLY mutating routes open on the hub. Everything else under the mount
# keeps the phase-1 blanket rejection; this is an allowlist, never a
# blocklist, so a new upstream write route is closed until someone adds it
# here deliberately.
#
# WHY THESE THREE: the operator's acceptance test for phone parity is
# "send a DM with an attachment" — 「読み書き送信、すべてローカルのブラウザで
# できることと全く同一にしてください」. Send, react, upload is that test and
# nothing more. Deliberately EXCLUDED: the api_dispatch catch-all
# (<path:endpoint>), which would make every board mutation reachable in one
# line, and hooks/* which are machine-to-machine and have their own callers.
#
# `<str:peer>` in scitex_cards._django.urls matches a single non-empty
# segment (no "/"), so these patterns mirror the upstream routes exactly;
# they are anchored on both ends so a suffix cannot smuggle in another route.
# Tracks scitex_cards._django.urls:108-122 in lockstep, same contract as
# _TODO_PREFIX above.
_WRITABLE_PATHS = (
    re.compile(r"^/apps/cards/dm/thread/[^/]+$"),
    re.compile(r"^/apps/cards/dm/thread/[^/]+/reaction$"),
    re.compile(r"^/apps/cards/dm/upload$"),
)


def _is_writable_path(path: str) -> bool:
    """True only for the explicitly opened mutating routes."""
    return any(pattern.match(path) for pattern in _WRITABLE_PATHS)

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

        # --- Write gate, part 1: reject everything not opened ---------
        # ORDERING IS THE SAFETY PROPERTY HERE, so it is worth stating.
        # This half only ever REJECTS, which is why it is safe before
        # authentication. The half that ADMITS a write lives BELOW the auth
        # and tenancy blocks — see part 2. Putting an allowlist here instead
        # would admit the opened routes before anyone had been
        # authenticated or scoped to a store, which is the exact inversion
        # that makes an allowlist dangerous.
        is_write = request.method not in _READ_METHODS
        if is_write and not _is_writable_path(path):
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

        # PRIMARY CHANNEL — a request ATTRIBUTE, not the query string.
        #
        # Injecting tenancy via ?store= put a security-critical value in the
        # exact namespace the attacker controls, so downstream (upstream
        # scitex-cards) our injected store and a hostile ?store= are
        # byte-identical — indistinguishable by construction. That is why the
        # discard above has to exist at all: it papers over a channel we
        # should not be using. An attribute cannot be spoofed by a client,
        # so the upstream can accept it unconditionally and reject query/body.
        # Contract agreed with scitex-cards on card
        # sec-p0-fleet-dm-board-reachable-from-prod-django-20260728.
        request.scitex_store = store

        # LEGACY CHANNEL — deliberately still set, and NOT yet removed.
        # Removing it here before the upstream honours request.scitex_store
        # would drop tenancy injection entirely for a release window, and the
        # upstream then falls back to its ambient canonical store — one store
        # for ALL tenants. On prod today that store is empty (/app/.scitex is
        # an empty named volume) so it would merely look like "no data", which
        # is exactly what makes it dangerous: it is one mount away from being
        # a cross-tenant read, armed by configuration rather than prevented by
        # code. Alias first, then remove.
        # DELETE THIS BLOCK once scitex-cards ships attribute support — that
        # is the step that lets the upstream reject query/body outright.
        params = request.GET.copy()
        params["store"] = str(store)
        request.GET = params

        # --- Write gate, part 2: the opened routes, now authenticated ---
        # Reached ONLY by _is_writable_path routes, and only after the user
        # is authenticated (above) and the store is server-resolved (above).
        if is_write:
            rejection = self._reject_opened_write(request)
            if rejection is not None:
                return rejection

        return self.get_response(request)

    # -----------------------------------------------------------------
    @staticmethod
    def _reject_opened_write(request):
        """Guard an allowlisted write; ``None`` means let it through.

        Two checks the blanket phase-1 rejection used to make unnecessary,
        because nothing mutating ever got this far.

        1. READONLY VISITOR. Shared-pool visitors must not send DMs as
           themselves into someone else's store. Same structured #308
           payload the rest of the site uses, so the shared frontend guard
           renders the Sign up / Log in toast rather than a raw 403.

        2. CSRF — and this one is load-bearing, not ceremony. The upstream
           ``dm_thread_view`` is ``@csrf_exempt``
           (scitex_cards._django.handlers.dm), and the hub authenticates
           with a SESSION COOKIE. Cookie auth plus an exempt POST is a
           textbook cross-site request forgery: any page the operator
           visits could POST a DM as them, and the board would attribute it
           to them correctly because they really were authenticated. The
           mount's auth gate does NOT substitute for CSRF — it is precisely
           what makes the forgery succeed.

           So the exemption is re-armed here rather than accepted. Passing a
           plain callable (no ``csrf_exempt`` attribute) makes
           ``CsrfViewMiddleware.process_view`` enforce; ``CsrfViewMiddleware``
           sits at settings_shared.py:284, ahead of this middleware, so
           ``process_request`` has already populated the token and this call
           is a check rather than a re-parse. Returns ``None`` when the
           token is good.
        """
        from apps.infra.project_app.services.visitor_pool import (
            is_readonly_visitor,
            readonly_write_rejection,
        )

        if is_readonly_visitor(request):
            return readonly_write_rejection("send messages", request=request)

        csrf = CsrfViewMiddleware(lambda _req: None)
        reason = csrf.process_view(request, lambda *a, **kw: None, (), {})
        if reason is not None:
            logger.warning(
                "[todo-mount] CSRF rejection on opened write %s for user %s",
                request.path,
                getattr(getattr(request, "user", None), "username", "?"),
            )
            return reason

        return None

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
