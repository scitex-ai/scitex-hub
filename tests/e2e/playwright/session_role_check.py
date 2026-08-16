#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Did the capture photograph a POOLED VISITOR, or the fallback?

WHY THIS EXISTS. ``test_capture_screenshots.py`` claims, in its own
docstring, that "these run as the pooled visitor, not as a real account,
so nothing in the artifact can contain anybody's private project".
Until this module existed that claim was asserted by nothing. The two
failure conditions the capture DID have — HTTP >= 400 and a blank render
— cannot detect it, because the wrong session renders perfectly:

  * When the visitor pool has no verified-clean slot, allocation falls
    back to the SHARED ``readonly-visitor`` account
    (``visitor_pool/pool_manager.py`` -> ``READONLY_REASON_NO_READY_SLOT``).
    Every page still returns 200 and still renders text. The job goes
    green and the PNGs show a different product than the one claimed.
  * Measured on production 2026-08-16: 15 of 16 slots quarantined, the
    pool serving readonly-visitor only. The same broken-Gitea-credential
    root cause took out pool CREATION in CI on this very PR. So this is
    not a hypothetical — it is the state both environments were in on
    the day the capture job was written.

A guard that only fires on a state nobody has seen is a comment. This
one fires on the state we were actually in.

THE SIGNAL. ``templates/global_base.html`` renders
``<body data-session-role="...">`` from the canonical role model in
``apps/infra/project_app/services/visitor_pool/session_role.py``. That
attribute is already pinned against the REAL rendered HTML for all three
roles by ``tests/apps/project_app/test_visitor_failloud.py`` (lines
388-412), which runs in the ordinary pytest matrix — so if the attribute
or a role string is ever renamed, that suite breaks loudly rather than
this capture silently degrading to a vacuous check.

WHY THE ROLE STRINGS ARE LITERALS HERE. These tests drive a LIVE SERVER
over HTTP; the pytest process has no Django settings configured and must
not import application modules to get four constants. The duplication is
covered by the pinning test named above.
"""

from __future__ import annotations

#: Route used to acquire — and later to re-confirm — the pooled slot.
#: Must be one ``VisitorAutoLoginMiddleware`` allocates on: it deliberately
#: does NOT allocate on ``/``, ``/landing/``, ``/apps/tools/`` or
#: ``/auth/*`` for an unauthenticated request, because a first-time reader
#: must reach the marketing pages anonymously. ``/apps/home/`` is not in
#: that skip list, and is in the capture set anyway.
VISITOR_WARMUP_ROUTE = "/apps/home/"

#: The body attribute carrying the canonical session role.
SESSION_ROLE_ATTR = "data-session-role"

#: Read it from a Playwright page. ``''`` when the attribute is absent —
#: which is itself a failure (a page that does not extend global_base
#: cannot be vouched for), never a pass.
READ_SESSION_ROLE_JS = (
    "() => (document.body && document.body.getAttribute('%s')) || ''"
    % SESSION_ROLE_ATTR
)

ROLE_ANONYMOUS = "anonymous"
ROLE_READONLY_VISITOR = "readonly_visitor"
ROLE_VISITOR = "visitor"
ROLE_USER = "user"

#: The one role a screenshot artifact may be taken under: a writable
#: pool slot (visitor-NNN), whose workspace was wiped and verified clean
#: before it was handed out, and is wiped again after.
REQUIRED_ROLE = ROLE_VISITOR

#: Role -> what it means that we got THIS instead of a pooled visitor.
#: No generic fallback text: an unrecognised role gets its own honest
#: "we do not know what this is" line rather than the wrong specific one.
_DIAGNOSIS = {
    ROLE_READONLY_VISITOR: (
        "the SHARED readonly-visitor fallback. The pool handed out no "
        "writable slot, which means zero slots were verified clean "
        "(quarantined, mid-reset, or never reconciled). The pages render "
        "perfectly in this state, so the screenshots would look fine and "
        "show the wrong product. Fix the pool, do not relax this check: "
        "run `manage.py create_visitor_pool` then "
        "`manage.py reconcile_visitor_slots` and read their output."
    ),
    ROLE_ANONYMOUS: (
        "an ANONYMOUS session — no visitor slot was allocated at all. "
        "Either VisitorAutoLoginMiddleware skipped this path (it skips "
        "'/', '/landing/', '/apps/tools/' and '/auth/' for unauthenticated "
        "requests, which is why the capture warms up on a workspace route "
        "FIRST), or the session was dropped mid-run."
    ),
    ROLE_USER: (
        "a REGISTERED ACCOUNT. This is the privacy failure the capture "
        "exists to make impossible: the artifact is downloadable by "
        "anyone who can read the run, and a real account's projects, "
        "manuscripts and chat history must never be in it. Do not "
        "screenshot a logged-in account."
    ),
    "": (
        "a page with no %s attribute at all. Every page in the capture "
        "set extends templates/global_base.html, which always renders it, "
        "so an empty value means this response was not the page we think "
        "it was (an error page, a bare redirect target, or a template "
        "that bypasses the base)." % SESSION_ROLE_ATTR
    ),
}
_DIAGNOSIS_UNKNOWN = (
    "a role this check does not recognise. Either session_role.py grew a "
    "new role and this module was not updated, or the page rendered "
    "something unexpected into the attribute."
)


class NotAPooledVisitorError(AssertionError):
    """The captured session was not a writable pooled visitor slot."""


def diagnose_session_role(role: str) -> str:
    """Plain-language explanation of a non-pooled-visitor role."""
    return _DIAGNOSIS.get(role, _DIAGNOSIS_UNKNOWN)


def wrong_role_message(role: str, where: str) -> str:
    """The failure text for a session that is not a pooled visitor.

    Kept separate from the raising form so a plain ``assert`` can carry it
    (pytest's own failure output) without the test having to catch an
    exception. Both call sites go through this one string.
    """
    return (
        "%s was photographed as %r, not the pooled visitor this capture "
        "claims to run as.\n"
        "  expected %s=%r\n"
        "  got      %s=%r\n"
        "  meaning: %s"
        % (
            where,
            role,
            SESSION_ROLE_ATTR,
            REQUIRED_ROLE,
            SESSION_ROLE_ATTR,
            role,
            diagnose_session_role(role),
        )
    )


def assert_pooled_visitor(role: str, where: str) -> None:
    """Fail unless ``role`` is a writable pooled visitor slot.

    The raising form, for use where a bare ``assert`` cannot go — notably
    fixture setup, which must abort the run BEFORE any PNG is written.

    Args:
        role: the value read from ``body[data-session-role]``.
        where: a human label for what was being photographed, so the
            failure names the page rather than only the rule.

    Raises:
        NotAPooledVisitorError: for every other role, including the
            readonly-visitor fallback, anonymous, a registered account,
            a missing attribute and an unrecognised value. There is no
            "close enough" role — a screenshot taken under any of them
            misrepresents the product, leaks private data, or both.
    """
    if role == REQUIRED_ROLE:
        return
    raise NotAPooledVisitorError(wrong_role_message(role, where))


# EOF
