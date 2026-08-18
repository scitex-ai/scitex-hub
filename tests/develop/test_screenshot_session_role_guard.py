#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Positive control for the product-screenshot honesty gate.

WHY THIS FILE IS SEPARATE FROM THE CAPTURE. The capture itself lives
under ``tests/e2e/`` and is skipped by ``tests/conftest.py`` in every run
that does not pass ``--browser`` — i.e. in the ordinary pytest matrix,
which is the gate that runs on every PR. A guard that only executes
inside a 30-minute browser job, and only when a live server happens to
be up, is a guard nobody watches. These cases are pure functions over a
string, so they run in the normal matrix on every commit.

WHAT IT PROVES. That ``assert_pooled_visitor`` actually RAISES for the
states that would produce wrong or unpublishable screenshots — above all
``readonly_visitor``, the shared-fallback state production was measured
in on 2026-08-16 and the state a CI run with a broken visitor pool lands
in. A guard never observed failing is not a guard (#613 on this board);
the ``readonly_visitor`` cases below are that observation, pinned.
"""

from __future__ import annotations

import pytest

from tests.e2e.playwright.session_role_check import (
    READ_SESSION_ROLE_JS,
    REQUIRED_ROLE,
    ROLE_ANONYMOUS,
    ROLE_READONLY_VISITOR,
    ROLE_USER,
    ROLE_VISITOR,
    SESSION_ROLE_ATTR,
    NotAPooledVisitorError,
    assert_pooled_visitor,
    diagnose_session_role,
)

# A page label in the same shape the capture passes, so the assertions
# below check the message a human would actually read in CI.
WHERE = "Writer (/apps/writer/)"


def rejection_message(role: str, where: str = WHERE) -> str:
    """Run the guard and hand back the failure text it raised.

    Not a test: a shared arrange step. Re-raises ``AssertionError`` if
    the guard did NOT reject, so this helper can never silently turn a
    missing rejection into an empty string.
    """
    try:
        assert_pooled_visitor(role, where)
    except NotAPooledVisitorError as exc:
        return str(exc)
    raise AssertionError(
        "assert_pooled_visitor accepted %r — the guard is not guarding" % role
    )


class TestPooledVisitorGateAccepts:
    def test_a_pooled_visitor_slot_is_accepted(self):
        # Arrange
        role = ROLE_VISITOR
        accepted = None
        # Act
        accepted = assert_pooled_visitor(role, WHERE)
        # Assert — returns None (no exception) for the one allowed role.
        assert accepted is None

    def test_required_role_is_the_pooled_visitor_role(self):
        # Arrange
        expected = ROLE_VISITOR
        # Act
        actual = REQUIRED_ROLE
        # Assert
        assert actual == expected


class TestReadonlyVisitorFallbackIsRejected:
    """THE case. A pool with no verified-clean slot serves the shared
    readonly-visitor, and it renders perfectly — so the capture's other
    two failure conditions (HTTP >= 400, blank body) both PASS on it."""

    def test_readonly_visitor_role_raises(self):
        # Arrange
        role = ROLE_READONLY_VISITOR
        # Act
        rejects = pytest.raises(NotAPooledVisitorError)
        # Assert
        with rejects:
            assert_pooled_visitor(role, WHERE)

    def test_readonly_visitor_message_names_the_page(self):
        # Arrange
        role = ROLE_READONLY_VISITOR
        # Act
        message = rejection_message(role)
        # Assert
        assert WHERE in message

    def test_readonly_visitor_message_names_the_role_it_got(self):
        # Arrange
        role = ROLE_READONLY_VISITOR
        # Act
        message = rejection_message(role)
        # Assert
        assert ROLE_READONLY_VISITOR in message

    def test_readonly_visitor_message_names_the_repair_command(self):
        # Arrange
        role = ROLE_READONLY_VISITOR
        # Act
        message = rejection_message(role)
        # Assert — the fix is the pool, never relaxing the check.
        assert "reconcile_visitor_slots" in message


class TestOtherNonVisitorRolesAreRejected:
    def test_anonymous_session_raises(self):
        # Arrange
        role = ROLE_ANONYMOUS
        # Act
        rejects = pytest.raises(NotAPooledVisitorError)
        # Assert
        with rejects:
            assert_pooled_visitor(role, "Projects (/apps/home/)")

    def test_anonymous_message_says_no_slot_was_allocated(self):
        # Arrange
        role = ROLE_ANONYMOUS
        # Act
        message = rejection_message(role, "Projects (/apps/home/)")
        # Assert
        assert "ANONYMOUS" in message

    def test_registered_account_raises(self):
        # Arrange
        role = ROLE_USER
        # Act
        rejects = pytest.raises(NotAPooledVisitorError)
        # Assert — a logged-in account's data must never reach a
        # downloadable artifact.
        with rejects:
            assert_pooled_visitor(role, "Chat (/chat/)")

    def test_registered_account_message_states_the_privacy_stake(self):
        # Arrange
        role = ROLE_USER
        # Act
        message = rejection_message(role, "Chat (/chat/)")
        # Assert
        assert "REGISTERED ACCOUNT" in message

    def test_missing_attribute_raises(self):
        # Arrange
        role = ""
        # Act
        rejects = pytest.raises(NotAPooledVisitorError)
        # Assert — absence is not consent.
        with rejects:
            assert_pooled_visitor(role, "Docs (/apps/docs/)")

    def test_missing_attribute_message_names_the_attribute(self):
        # Arrange
        role = ""
        # Act
        message = rejection_message(role, "Docs (/apps/docs/)")
        # Assert
        assert SESSION_ROLE_ATTR in message

    def test_unrecognised_role_raises(self):
        # Arrange
        role = "superuser_visitor"
        # Act
        rejects = pytest.raises(NotAPooledVisitorError)
        # Assert
        with rejects:
            assert_pooled_visitor(role, "Cards (/apps/cards/)")

    def test_unrecognised_role_message_does_not_guess(self):
        # Arrange
        role = "superuser_visitor"
        # Act
        message = rejection_message(role, "Cards (/apps/cards/)")
        # Assert — no confident wrong explanation for an unknown value.
        assert "does not recognise" in message


class TestGateWiring:
    def test_attribute_matches_the_one_global_base_renders(self):
        # Arrange — pinned against the real HTML by
        # tests/apps/project_app/test_visitor_failloud.py:388-412.
        expected = "data-session-role"
        # Act
        actual = SESSION_ROLE_ATTR
        # Assert
        assert actual == expected

    def test_the_js_reads_that_attribute(self):
        # Arrange
        attribute = SESSION_ROLE_ATTR
        # Act
        js = READ_SESSION_ROLE_JS
        # Assert
        assert attribute in js

    def test_the_js_reads_it_from_the_body_element(self):
        # Arrange
        element = "document.body"
        # Act
        js = READ_SESSION_ROLE_JS
        # Assert
        assert element in js

    def test_every_rejected_role_gets_its_own_diagnosis(self):
        # Arrange
        roles = [ROLE_READONLY_VISITOR, ROLE_ANONYMOUS, ROLE_USER, ""]
        # Act
        diagnoses = [diagnose_session_role(role) for role in roles]
        # Assert — four roles, four distinct explanations.
        assert len(set(diagnoses)) == len(roles)

    def test_no_diagnosis_is_a_stub(self):
        # Arrange
        roles = [ROLE_READONLY_VISITOR, ROLE_ANONYMOUS, ROLE_USER, ""]
        too_short = 40
        # Act
        thin = [r for r in roles if len(diagnose_session_role(r)) < too_short]
        # Assert
        assert thin == []


if __name__ == "__main__":
    import os

    pytest.main([os.path.abspath(__file__)])

# EOF
