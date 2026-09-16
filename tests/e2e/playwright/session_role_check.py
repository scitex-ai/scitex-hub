#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Validate that browser E2E fixtures use the synthetic registered account."""

from __future__ import annotations

AUTHENTICATED_WARMUP_ROUTE = "/apps/my-projects/"
SESSION_ROLE_ATTR = "data-session-role"
READ_SESSION_ROLE_JS = (
    "() => (document.body && document.body.getAttribute('%s')) || ''"
    % SESSION_ROLE_ATTR
)
ROLE_ANONYMOUS = "anonymous"
ROLE_USER = "user"
REQUIRED_ROLE = ROLE_USER

_DIAGNOSIS = {
    ROLE_ANONYMOUS: (
        "an anonymous session. The login did not establish a registered-user "
        "session, or the browser dropped it before this request."
    ),
    "": (
        "a page with no %s attribute. The response may be an error page, bare "
        "redirect target, or template that bypasses global_base.html."
        % SESSION_ROLE_ATTR
    ),
}
_DIAGNOSIS_UNKNOWN = (
    "an unrecognised role. The rendered shell and E2E role contract disagree."
)


class NotAnAuthenticatedUserError(AssertionError):
    """The E2E session was not the synthetic registered account."""


def is_authenticated_user_role(role: str) -> bool:
    """True only for a registered account."""
    return role == ROLE_USER


def diagnose_session_role(role: str) -> str:
    """Plain-language explanation of a non-user role."""
    return _DIAGNOSIS.get(role, _DIAGNOSIS_UNKNOWN)


def authenticated_user_role_failure(role: str, where: str) -> str:
    """Failure text for a context that must be a registered user."""
    return (
        f"{where} has session role {role!r}; this fixture requires a "
        f"registered user ({SESSION_ROLE_ATTR}={ROLE_USER!r}). "
        f"meaning: {diagnose_session_role(role)}"
    )


def wrong_role_message(role: str, where: str) -> str:
    """Backward-compatible name for authenticated-user diagnostics."""
    return authenticated_user_role_failure(role, where)


def assert_authenticated_user(role: str, where: str) -> None:
    """Fail unless the rendered role is the registered synthetic account."""
    if is_authenticated_user_role(role):
        return
    raise NotAnAuthenticatedUserError(authenticated_user_role_failure(role, where))
