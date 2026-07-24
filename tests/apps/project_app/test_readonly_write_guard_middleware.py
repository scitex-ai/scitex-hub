#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for ReadonlyVisitorWriteGuardMiddleware (card hub-visitor-slot-isolation-audit).

Default-deny safety net: a readonly-visitor write is rejected on ANY
endpoint by default, not only the ones a view opted into. #308's
per-view guard already missed project creation once in prod (the
"Plaque" leak) — this middleware is the fail-safe that stops the next
missed endpoint from repeating it.

Real Django test DB via django.test.TestCase — no mocks.
One assertion per test (STX-TQ007), AAA markers (STX-TQ002).
"""

from django.contrib.auth.models import User
from django.test import TestCase


def _is_readonly_guard_403(resp) -> bool:
    """True iff the response is THIS guard's structured rejection."""
    if resp.status_code != 403:
        return False
    if not resp.get("Content-Type", "").startswith("application/json"):
        return False
    return resp.json().get("reason") == "readonly-visitor"


class ProjectCreateDefaultDenyTest(TestCase):
    """The exact endpoint that already leaked is now rejected by default."""

    @classmethod
    def setUpTestData(cls):
        cls.readonly_visitor = User.objects.create_user(
            username="readonly-visitor",
            password="TestPass123!",  # pragma: allowlist secret
        )

    def test_project_create_post_rejected_for_readonly_visitor(self):
        # Arrange
        self.client.force_login(self.readonly_visitor)
        # Act
        resp = self.client.post("/new/", data={"name": "should-not-be-created"})
        # Assert
        assert resp.status_code == 403

    def test_project_create_rejection_carries_readonly_reason(self):
        # Arrange
        self.client.force_login(self.readonly_visitor)
        # Act
        resp = self.client.post("/new/", data={"name": "should-not-be-created"})
        # Assert
        assert resp.json()["reason"] == "readonly-visitor"

    def test_legacy_api_create_post_rejected_for_readonly_visitor(self):
        # Arrange — the second unguarded creation route from the audit
        self.client.force_login(self.readonly_visitor)
        # Act
        resp = self.client.post(
            "/readonly-visitor/api/create/",
            data={"name": "should-not-be-created"},
        )
        # Assert
        assert resp.status_code == 403

    def test_project_create_get_is_not_rejected(self):
        # Arrange — safe methods stay read-only, never no-access
        self.client.force_login(self.readonly_visitor)
        # Act
        resp = self.client.get("/new/")
        # Assert
        assert resp.status_code != 403


class GuardScopeTest(TestCase):
    """The guard is scoped to the shared readonly-visitor role only."""

    def test_pool_visitor_write_is_not_blocked_by_this_guard(self):
        # Arrange — a pool visitor (visitor-NNN) owns a real writable slot
        visitor = User.objects.create_user(
            username="visitor-002",
            password="TestPass123!",  # pragma: allowlist secret
        )
        self.client.force_login(visitor)
        # Act
        resp = self.client.post("/new/", data={"name": "visitor-owned-project"})
        # Assert — whatever the view itself decides, it isn't this guard's 403
        assert not _is_readonly_guard_403(resp)

    def test_registered_user_write_is_not_blocked_by_this_guard(self):
        # Arrange
        user = User.objects.create_user(
            username="alice",
            password="TestPass123!",  # pragma: allowlist secret
        )
        self.client.force_login(user)
        # Act
        resp = self.client.post("/new/", data={"name": "alices-project"})
        # Assert
        assert not _is_readonly_guard_403(resp)

    def test_anonymous_post_is_not_blocked_by_this_guard(self):
        # Arrange — no session user at all (bots, curl): other layers
        # (login_required) own this case; the guard must not misfire.
        # Act
        resp = self.client.post("/new/", data={"name": "x"})
        # Assert
        assert not _is_readonly_guard_403(resp)


class ConversionFunnelAllowlistTest(TestCase):
    """The auth conversion funnel stays writable for readonly-visitors."""

    @classmethod
    def setUpTestData(cls):
        cls.readonly_visitor = User.objects.create_user(
            username="readonly-visitor",
            password="TestPass123!",  # pragma: allowlist secret
        )

    def test_logout_post_is_not_blocked(self):
        # Arrange — blocking /auth/ would trap the session in readonly
        self.client.force_login(self.readonly_visitor)
        # Act
        resp = self.client.post("/auth/logout/")
        # Assert
        assert not _is_readonly_guard_403(resp)

    def test_signup_post_is_not_blocked(self):
        # Arrange — signup IS the conversion path out of readonly mode
        self.client.force_login(self.readonly_visitor)
        # Act
        resp = self.client.post("/auth/signup/", data={})
        # Assert
        assert not _is_readonly_guard_403(resp)


if __name__ == "__main__":
    import os

    import pytest

    pytest.main([os.path.abspath(__file__)])

# EOF
