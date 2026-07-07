#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Canonical session-role model (card hub-visitor-ux-allapps, msg 598).

Three roles + anonymous, distinguished consistently in backend AND frontend:

- ``readonly_visitor`` — the shared readonly-visitor account (unlimited
  touring, zero writes; pool-full / allocation-failure fallback).
- ``visitor``          — a writable pool slot (visitor-NNN, 1h lifetime).
- ``user``             — a registered account.
- ``anonymous``        — no session user at all.

This module is the ONLY place that maps usernames to roles — dispatch,
middleware, context processors, and views must use these helpers instead
of scattering ``username.startswith("visitor-")`` checks.

The 1h-expiry / signup-migration machinery is intentionally NOT here
(separate phases); this is the role model only.

Structured write-rejection (fail-loud UX): readonly visitors can VIEW
everything; only WRITE attempts are rejected — with a machine-readable
403 payload the shared frontend layer turns into an actionable toast
(Sign up / Log in / retry later).
"""

from __future__ import annotations

from django.http import JsonResponse

ROLE_ANONYMOUS = "anonymous"
ROLE_READONLY_VISITOR = "readonly_visitor"
ROLE_VISITOR = "visitor"
ROLE_USER = "user"

#: ``reason`` value carried by every structured readonly-write 403.
READONLY_REJECTION_REASON = "readonly-visitor"

#: Session key set when a session is downgraded to readonly-visitor,
#: consumed (popped) by the context processor to fail-loud exactly once.
SESSION_KEY_READONLY_NOTICE = "readonly_visitor_notice"


def get_user_role(user) -> str:
    """Map a Django user object to its canonical session role."""
    # Local import: visitor_pool.py imports models at module level and
    # session_role must stay importable from lightweight contexts.
    from .visitor_pool import VisitorPool

    if user is None or not user.is_authenticated:
        return ROLE_ANONYMOUS
    if user.username == VisitorPool.READONLY_VISITOR_USERNAME:
        return ROLE_READONLY_VISITOR
    if user.username.startswith(VisitorPool.VISITOR_USER_PREFIX):
        return ROLE_VISITOR
    return ROLE_USER


def get_session_role(request) -> str:
    """Canonical role for this request's session (see module docstring)."""
    return get_user_role(getattr(request, "user", None))


def is_visitor_session(request) -> bool:
    """True for both visitor roles (pool slot or shared readonly)."""
    return get_session_role(request) in (ROLE_VISITOR, ROLE_READONLY_VISITOR)


def is_readonly_visitor(request) -> bool:
    """True only for the shared readonly-visitor session."""
    return get_session_role(request) == ROLE_READONLY_VISITOR


def readonly_write_rejection(action: str = "make changes") -> JsonResponse:
    """Structured 403 for a write attempted by a readonly visitor.

    The shared frontend fetch layer (static/shared/ts/utils/
    readonly-visitor-guard.ts) matches ``reason == "readonly-visitor"``
    and renders a toast with Sign up / Log in / retry-later actions.
    Never use this to block page rendering — reads always succeed.
    """
    return JsonResponse(
        {
            "error": f"Read-only mode — sign up or log in to {action}.",
            "reason": READONLY_REJECTION_REASON,
            "detail": "Visitor pool is full — you are browsing read-only.",
            "actions": ["signup", "login", "retry-later"],
            "signup_url": "/auth/signup/",
            "login_url": "/auth/login/",
        },
        status=403,
    )


# EOF
