#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for the authenticated-test-user role validation used by the E2E
mobile fixtures (tests/e2e/playwright/conftest.py).

The mobile fixtures authenticate as an EXPLICIT registered test user (not a
pooled visitor) and must only hand a page to a test once the context is
provably a registered user. This pins the role predicate and its failure
text so a future fixture change cannot silently accept an anonymous /
readonly / pooled session -- a logged-out page still returns 200, so only an
explicit role check can catch it.

Browser-free and pure: no Playwright fixtures, so this runs in the ordinary
pytest matrix, not just the E2E job.
"""

import pytest

from tests.e2e.playwright.session_role_check import (
    ROLE_ANONYMOUS,
    ROLE_READONLY_VISITOR,
    ROLE_USER,
    ROLE_VISITOR,
    authenticated_user_role_failure,
    is_authenticated_user_role,
)


class TestIsAuthenticatedUserRole:
    def test_accepts_registered_user_role(self):
        assert is_authenticated_user_role(ROLE_USER) is True

    def test_rejects_anonymous_role(self):
        # The exact role the failing mobile contexts reported.
        assert is_authenticated_user_role(ROLE_ANONYMOUS) is False

    def test_rejects_missing_role_attribute(self):
        # "" means the page has no data-session-role at all -- cannot vouch.
        assert is_authenticated_user_role("") is False

    def test_rejects_readonly_visitor_role(self):
        # A readonly fallback is NOT a registered user; running against it
        # would be the same vacuous-pass defect.
        assert is_authenticated_user_role(ROLE_READONLY_VISITOR) is False

    def test_rejects_pooled_visitor_role(self):
        # The mobile fixtures log in as a real account, not a pooled slot.
        assert is_authenticated_user_role(ROLE_VISITOR) is False

    def test_rejects_unrecognised_role(self):
        assert is_authenticated_user_role("something-new") is False


class TestAuthenticatedUserRoleFailure:
    def test_message_names_expected_and_observed_roles(self):
        msg = authenticated_user_role_failure(ROLE_ANONYMOUS, "the MOBILE context")
        assert "the MOBILE context" in msg
        assert f"role {ROLE_ANONYMOUS!r}" in msg
        assert f"{ROLE_USER!r}" in msg

    def test_message_explains_anonymous_role(self):
        msg = authenticated_user_role_failure(ROLE_ANONYMOUS, "ctx")
        # Reuses the role-meaning table: anonymous has its own diagnosis.
        assert "ANONYMOUS" in msg.upper()

    def test_message_flags_a_missing_attribute(self):
        msg = authenticated_user_role_failure("", "ctx")
        assert "data-session-role" in msg

    def test_message_names_unknown_role_honestly(self):
        msg = authenticated_user_role_failure("mystery-role", "ctx")
        # An unrecognised role gets "we do not know what this is", not a
        # borrowed diagnosis.
        assert "mystery-role" in msg
        assert "not recognise" in msg


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
