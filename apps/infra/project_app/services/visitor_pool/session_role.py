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
#: Its value is a downgrade-reason code (see READONLY_REASON_* below).
SESSION_KEY_READONLY_NOTICE = "readonly_visitor_notice"

#: Session key recording WHY allocation refused a writable slot.
#: Written by PoolAllocator.allocate_visitor at allocation time and kept
#: for the whole readonly session (banner is one-shot; the header
#: popover/dropdown keep explaining the persistent state truthfully).
SESSION_KEY_READONLY_REASON = "visitor_readonly_reason"

#: Structured downgrade-reason codes (recorded at allocation time).
#: ``pool_full``    — every slot is busy serving another visitor.
#: ``no_ready_slot``— free slots exist and are being wiped + verified
#:                    right now (the post-rebuild boot fail-safe). This
#:                    one DOES clear on its own, which is why its copy may
#:                    say "retry in a few minutes".
#: ``needs_operator``— free slots exist but are QUARANTINED or missing.
#:                    These do NOT clear on their own: a quarantined slot
#:                    is released only by `manage.py
#:                    reconcile_visitor_slots --repair-only`, and a Celery
#:                    outage means the re-clean nobody is running. Telling
#:                    the user to retry would be telling them to do the one
#:                    thing that cannot work.
#: ``unknown``      — the session carries no recorded reason (e.g. a
#:                    legacy session from before this release).
READONLY_REASON_POOL_FULL = "pool_full"
READONLY_REASON_NO_READY_SLOT = "no_ready_slot"
READONLY_REASON_NEEDS_OPERATOR = "needs_operator"
READONLY_REASON_UNKNOWN = "unknown"

#: Reason code → truthful user-facing explanation. NO silent fallback to
#: a specific claim: an unrecognized code gets the generic-but-true copy,
#: never the wrong specific one.
_READONLY_REASON_DETAILS = {
    READONLY_REASON_POOL_FULL: (
        "All visitor slots are in use — you are browsing read-only."
    ),
    READONLY_REASON_NO_READY_SLOT: (
        "Visitor slots are being prepared — you are browsing read-only. "
        "Retry in a few minutes for a writable slot."
    ),
    # No "retry in a few minutes" here, deliberately: a quarantined slot is
    # released by an operator command and by nothing else, so retrying is
    # the one action guaranteed not to help. Measured 2026-09-05 — all four
    # slots sat quarantined for 2h45m while the UI invited the operator to
    # keep waiting.
    READONLY_REASON_NEEDS_OPERATOR: (
        "Writable visitor slots are temporarily unavailable and need an "
        "administrator — you are browsing read-only."
    ),
}
_READONLY_REASON_DETAIL_GENERIC = (
    "No writable visitor slot is available right now — "
    "you are browsing read-only."
)


#: Pool-capacity causes (pool_health.CAUSE_*) that an operator must clear.
#: Kept as bare strings so session_role stays importable from lightweight
#: contexts — pool_health imports models transitively.
#:
#: DELIBERATELY ONLY ``quarantined``. ``unprovisioned`` (no slot rows at all)
#: also needs an operator by REPAIR_BY_CAUSE's own reckoning — it wants
#: `create_visitor_pool` — so on the merits it arguably belongs here too.
#: It is NOT here because test_visitor_failloud.py:179 deliberately asserts
#: ``no_ready_slot`` for an empty pool, and quietly overturning that
#: assertion as a side effect of a quarantine fix would be changing product
#: behaviour nobody asked me to change. Whether an unprovisioned pool should
#: tell a visitor to "retry in a few minutes" is a real question and it
#: deserves its own decision, not a smuggled one.
_CAUSES_NEEDING_OPERATOR = frozenset({"quarantined"})


def readonly_reason_for_capacity_cause(cause: str | None) -> str:
    """Downgrade-reason for a pool_health capacity cause.

    Split out of the allocator branch so the RULE is a named thing with its
    own tests, rather than an `if` nobody can exercise without a database.

    The distinction that matters is whether the condition CLEARS ITSELF:
    a resetting slot does, in seconds; a quarantined or missing one does
    not, and is released only by `manage.py reconcile_visitor_slots
    --repair-only`. Telling a user to retry in the second case is telling
    them to do the one thing that cannot work.
    """
    if cause in _CAUSES_NEEDING_OPERATOR:
        return READONLY_REASON_NEEDS_OPERATOR
    return READONLY_REASON_NO_READY_SLOT


def readonly_reason_detail(reason: str | None) -> str:
    """Truthful copy for a downgrade-reason code (generic when unknown)."""
    return _READONLY_REASON_DETAILS.get(reason or "", _READONLY_REASON_DETAIL_GENERIC)


def get_readonly_reason(session) -> str:
    """The recorded downgrade-reason code for this session (or unknown)."""
    return session.get(SESSION_KEY_READONLY_REASON, READONLY_REASON_UNKNOWN)


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


def readonly_write_rejection(
    action: str = "make changes", request=None
) -> JsonResponse:
    """Structured 403 for a write attempted by a readonly visitor.

    The shared frontend fetch layer (static/shared/ts/utils/
    readonly-visitor-guard.ts) matches ``reason == "readonly-visitor"``
    and renders a toast with Sign up / Log in / retry-later actions.
    Never use this to block page rendering — reads always succeed.

    Pass ``request`` so ``detail`` explains the ACTUAL downgrade reason
    recorded at allocation time (pool full vs slots being prepared);
    without it the detail stays truthfully generic.
    """
    downgrade_reason = READONLY_REASON_UNKNOWN
    if request is not None and hasattr(request, "session"):
        downgrade_reason = get_readonly_reason(request.session)
    return JsonResponse(
        {
            "error": f"Read-only mode — sign up or log in to {action}.",
            "reason": READONLY_REJECTION_REASON,
            "downgrade_reason": downgrade_reason,
            "detail": readonly_reason_detail(downgrade_reason),
            "actions": ["signup", "login", "retry-later"],
            "signup_url": "/auth/signup/",
            "login_url": "/auth/login/",
        },
        status=403,
    )


# EOF
