#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Site-wide default-deny write guard for the shared readonly-visitor role.

Security fix (card ``hub-visitor-slot-isolation-audit``): the write-guard
introduced in #308 (``is_readonly_visitor`` / ``readonly_write_rejection``)
was opt-in and per-view — a view had to remember to call it. That
allowlist-of-protected-views model already missed the highest-value
target once: the "New Project" flow (``/new/`` and the legacy
``<username>/api/create/``) had NO guard at all, and a readonly-visitor
session used exactly that gap to create a project ("Plaque", found live
in prod 2026-07-08) that was then visible to every OTHER
concurrently-browsing anonymous visitor — because every anonymous
readonly session resolves to the literal same shared ``readonly-visitor``
Django ``User`` row. Auditing every view function in the app for this one
missing decorator is also how the gap was missed in the first place;
grepping afterwards found the same unguarded pattern on project delete,
edit, issue creation, PR actions, and collaboration/member management —
i.e. this was systemic, not an isolated oversight.

This middleware flips the failure mode from fail-open to fail-safe:
"zero write permission" becomes the DEFAULT for ``readonly_visitor``
sessions instead of something each view must opt into. Any non-safe HTTP
method (POST/PUT/PATCH/DELETE) from a readonly-visitor session is
rejected with the canonical structured 403 (see
``services.visitor_pool.readonly_write_rejection``) UNLESS the request
path is on the small, explicit allowlist below — the conversion funnel
itself (auth: signup/login/logout/password-reset) plus framework/utility
surfaces that carry no user-owned state. These mirror the ``skip_paths``
already used by the sibling ``VisitorAutoLoginMiddleware`` /
``VisitorExpirationMiddleware`` in ``middleware.py``, so the "safe without
visitor machinery" path list stays in one conceptual place across all
three middlewares.

Per-view guards (``file_save.py``, ``todo_app`` middleware) are left in
place as defense in depth and for their richer, action-specific error
copy ("save files", "edit the todo board"); this middleware is the
safety net that stops the NEXT missed endpoint from becoming another
incident — the same bug class that produced the "Plaque" leak once
already.

Must run AFTER ``VisitorAutoLoginMiddleware`` (``request.user`` needs to
be resolved to the final session role before ``is_readonly_visitor`` can
answer correctly) — see ``MIDDLEWARE`` order in
``config/settings/settings_shared.py``.
"""

from __future__ import annotations

import logging

from asgiref.sync import iscoroutinefunction, markcoroutinefunction, sync_to_async

logger = logging.getLogger(__name__)

_SAFE_METHODS = ("GET", "HEAD", "OPTIONS")

# Paths a readonly-visitor session must still be able to POST to: the
# conversion funnel (signup/login/logout/password-reset lives entirely
# under /auth/, including allauth social login at /auth/social/) plus
# framework/utility surfaces that carry no user-owned state. Blocking
# any of these would trap a readonly-visitor session rather than let it
# convert — the one write path this role explicitly MUST keep.
ALLOWLIST_PREFIXES = (
    "/auth/",
    "/admin/",
    "/static/",
    "/media/",
    "/healthz/",
    "/__debug__/",
    "/__reload__/",
)


def _is_allowlisted(path: str) -> bool:
    return any(path.startswith(prefix) for prefix in ALLOWLIST_PREFIXES)


class ReadonlyVisitorWriteGuardMiddleware:
    """Default-deny: readonly-visitor writes are rejected everywhere
    except the explicit allowlist above.

    Scoped ONLY to the shared ``readonly_visitor`` role — pool visitors
    (``visitor-NNN``, isolated writable 1h slots) and registered users
    are never touched by this middleware; writing within your own
    isolated slot is the entire point of the pool.
    """

    sync_capable = True
    async_capable = True

    def __init__(self, get_response):
        self.get_response = get_response
        if iscoroutinefunction(get_response):
            markcoroutinefunction(self)

    def __call__(self, request):
        if iscoroutinefunction(self.get_response):
            return self._acall(request)
        rejection = self._sync_body(request)
        if rejection is not None:
            return rejection
        return self.get_response(request)

    async def _acall(self, request):
        rejection = await sync_to_async(self._sync_body, thread_sensitive=True)(
            request
        )
        if rejection is not None:
            return rejection
        return await self.get_response(request)

    def _sync_body(self, request):
        if request.method in _SAFE_METHODS:
            return None

        if _is_allowlisted(request.path):
            return None

        # Local import: avoid a module-level dependency cycle between
        # middleware and the visitor_pool services package.
        from apps.infra.project_app.services.visitor_pool import (
            is_readonly_visitor,
            readonly_write_rejection,
        )

        if not is_readonly_visitor(request):
            return None

        logger.warning(
            "[ReadonlyVisitorWriteGuard] Blocked %s %s from the shared "
            "readonly-visitor session (no view-level guard reached it "
            "first) — see card hub-visitor-slot-isolation-audit",
            request.method,
            request.path,
        )
        return readonly_write_rejection("make changes", request=request)


# EOF
