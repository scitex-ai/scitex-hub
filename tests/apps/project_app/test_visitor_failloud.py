#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Visitor fail-loud UX tests (card hub-visitor-ux-allapps).

Covers the operator-confirmed 2026-07-07 spec:
- canonical session-role model (anonymous | readonly_visitor | visitor | user)
- readonly downgrade sets the one-shot explanation flag and the next
  rendered page shows the banner
- write attempts by readonly visitors get the structured 403
  ({"reason": "readonly-visitor", ...})
- pool occupancy is exposed to templates for the Read-Only badge

Real Django test DB via django.test.TestCase — no mocks.
One assertion per test (STX-TQ007), AAA markers (STX-TQ002).
"""

import json

from django.contrib.auth.models import AnonymousUser, User
from django.core.cache import cache
from django.test import TestCase

from apps.infra.project_app.services.visitor_pool import (
    ROLE_ANONYMOUS,
    ROLE_READONLY_VISITOR,
    ROLE_USER,
    ROLE_VISITOR,
    SESSION_KEY_READONLY_NOTICE,
    get_user_role,
)

BROWSER_UA = "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) Safari/605.1"


class SessionRoleModelTest(TestCase):
    """get_user_role maps every account shape to exactly one role."""

    def test_anonymous_user_maps_to_anonymous_role(self):
        # Arrange
        user = AnonymousUser()
        # Act
        role = get_user_role(user)
        # Assert
        assert role == ROLE_ANONYMOUS

    def test_readonly_visitor_maps_to_readonly_role(self):
        # Arrange
        user = User.objects.create_user(username="readonly-visitor")
        # Act
        role = get_user_role(user)
        # Assert
        assert role == ROLE_READONLY_VISITOR

    def test_pool_visitor_maps_to_visitor_role(self):
        # Arrange
        user = User.objects.create_user(username="visitor-003")
        # Act
        role = get_user_role(user)
        # Assert
        assert role == ROLE_VISITOR

    def test_registered_account_maps_to_user_role(self):
        # Arrange
        user = User.objects.create_user(username="alice")
        # Act
        role = get_user_role(user)
        # Assert
        assert role == ROLE_USER


class ReadonlyDowngradeExplanationTest(TestCase):
    """Pool-full downgrade explains itself on the next rendered page."""

    @classmethod
    def setUpTestData(cls):
        # Only the shared readonly-visitor exists — no visitor-NNN pool
        # users, so VisitorPool.allocate_visitor() cannot allocate a slot
        # and VisitorAutoLoginMiddleware falls back to readonly-visitor.
        User.objects.create_user(
            username="readonly-visitor",
            password="TestPass123!",  # pragma: allowlist secret
        )

    def test_downgrade_logs_session_in_as_readonly_visitor(self):
        # Arrange — anonymous browser request with an exhausted pool
        # Act
        resp = self.client.get("/", HTTP_USER_AGENT=BROWSER_UA)
        # Assert
        assert resp.wsgi_request.user.username == "readonly-visitor"

    def test_downgraded_page_renders_failloud_banner(self):
        # Arrange — anonymous browser request with an exhausted pool
        # Act — the downgrade request itself is the next rendered page
        resp = self.client.get("/", HTTP_USER_AGENT=BROWSER_UA)
        # Assert
        assert b"readonly-visitor-banner" in resp.content

    def test_downgraded_page_explains_pool_full_reason(self):
        # Arrange — anonymous browser request with an exhausted pool
        # Act
        resp = self.client.get("/", HTTP_USER_AGENT=BROWSER_UA)
        # Assert
        assert b"Visitor pool is full" in resp.content

    def test_explanation_flag_is_one_shot(self):
        # Arrange — first request consumes the downgrade notice
        self.client.get("/", HTTP_USER_AGENT=BROWSER_UA)
        # Act — second page load must not repeat the banner
        resp = self.client.get("/", HTTP_USER_AGENT=BROWSER_UA)
        # Assert
        assert b"readonly-visitor-banner" not in resp.content

    def test_downgrade_sets_readonly_session_marker(self):
        # Arrange — anonymous browser request with an exhausted pool
        # Act
        self.client.get("/", HTTP_USER_AGENT=BROWSER_UA)
        # Assert
        assert self.client.session.get("is_readonly_visitor") is True


class ReadonlyStructuredWriteRejectionTest(TestCase):
    """Write attempts by readonly visitors get the structured 403."""

    @classmethod
    def setUpTestData(cls):
        cls.readonly_visitor = User.objects.create_user(
            username="readonly-visitor",
            password="TestPass123!",  # pragma: allowlist secret
        )

    def _post_save_file(self):
        self.client.force_login(self.readonly_visitor)
        return self.client.post(
            "/api/workspace/save-file/",
            data=json.dumps({"project_id": 1, "path": "a.txt", "content": "x"}),
            content_type="application/json",
        )

    def test_write_rejection_returns_403(self):
        # Arrange
        # Act
        resp = self._post_save_file()
        # Assert
        assert resp.status_code == 403

    def test_write_rejection_carries_readonly_reason(self):
        # Arrange
        # Act
        resp = self._post_save_file()
        # Assert
        assert resp.json()["reason"] == "readonly-visitor"

    def test_write_rejection_offers_signup_login_retry_actions(self):
        # Arrange
        # Act
        resp = self._post_save_file()
        # Assert
        assert resp.json()["actions"] == ["signup", "login", "retry-later"]


class PoolOccupancyContextTest(TestCase):
    """Pool occupancy is exposed next to the Read-Only badge."""

    @classmethod
    def setUpTestData(cls):
        cls.readonly_visitor = User.objects.create_user(
            username="readonly-visitor",
            password="TestPass123!",  # pragma: allowlist secret
        )

    def setUp(self):
        # The occupancy value is cached for 60s — start each test clean.
        cache.clear()

    def test_readonly_page_context_has_pool_status(self):
        # Arrange
        self.client.force_login(self.readonly_visitor)
        # Act
        resp = self.client.get("/")
        # Assert
        assert resp.context["visitor_pool_status"] is not None

    def test_pool_status_reports_configured_total(self):
        # Arrange
        from apps.infra.project_app.services.visitor_pool import VisitorPool

        self.client.force_login(self.readonly_visitor)
        # Act
        resp = self.client.get("/")
        # Assert
        assert resp.context["visitor_pool_status"]["total"] == VisitorPool.POOL_SIZE

    def test_pool_status_reports_allocated_count(self):
        # Arrange — no allocations exist in this test DB
        self.client.force_login(self.readonly_visitor)
        # Act
        resp = self.client.get("/")
        # Assert
        assert resp.context["visitor_pool_status"]["allocated"] == 0

    def test_readonly_header_shows_visitor_slots_text(self):
        # Arrange
        self.client.force_login(self.readonly_visitor)
        # Act
        resp = self.client.get("/")
        # Assert
        assert b"visitor slots" in resp.content

    def test_regular_user_page_has_no_pool_status(self):
        # Arrange
        regular = User.objects.create_user(
            username="carol",
            password="TestPass123!",  # pragma: allowlist secret
        )
        self.client.force_login(regular)
        # Act
        resp = self.client.get("/")
        # Assert
        assert resp.context["visitor_pool_status"] is None


class SessionRoleExposedToFrontendTest(TestCase):
    """The canonical role is exposed to templates/TS via body data attr."""

    def test_readonly_visitor_body_carries_session_role(self):
        # Arrange
        readonly = User.objects.create_user(
            username="readonly-visitor",
            password="TestPass123!",  # pragma: allowlist secret
        )
        self.client.force_login(readonly)
        # Act
        resp = self.client.get("/")
        # Assert
        assert b'data-session-role="readonly_visitor"' in resp.content

    def test_pool_visitor_body_carries_session_role(self):
        # Arrange
        visitor = User.objects.create_user(
            username="visitor-002",
            password="TestPass123!",  # pragma: allowlist secret
        )
        self.client.force_login(visitor)
        # Act
        resp = self.client.get("/")
        # Assert
        assert b'data-session-role="visitor"' in resp.content

    def test_registered_user_body_carries_session_role(self):
        # Arrange
        user = User.objects.create_user(
            username="dave",
            password="TestPass123!",  # pragma: allowlist secret
        )
        self.client.force_login(user)
        # Act
        resp = self.client.get("/")
        # Assert
        assert b'data-session-role="user"' in resp.content


if __name__ == "__main__":
    import os

    import pytest

    pytest.main([os.path.abspath(__file__)])

# EOF
