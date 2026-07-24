#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Guest-mode launcher tests (card hub-visitor-ux-allapps).

Operator-confirmed 2026-07-07: visitor sessions at / must get the app
launcher in guest mode (tiles + prominent Sign in / Sign up CTA) instead
of bouncing to the marketing landing page; TRUE anonymous keeps landing.

All tests use the real Django test DB via django.test.TestCase — no mocks
(same conventions as test_launcher.py). One assertion per test (STX-TQ007).
"""

from django.contrib.auth.models import User
from django.test import TestCase

from apps.infra.project_app.services.visitor_pool.pool_manager import PoolAllocator


class GuestModeLauncherTest(TestCase):
    """Visitor sessions at / get the launcher, not the landing redirect."""

    @classmethod
    def setUpTestData(cls):
        cls.pool_visitor = User.objects.create_user(
            username="visitor-001",
            password="TestPass123!",  # pragma: allowlist secret
        )
        cls.readonly_visitor = User.objects.create_user(
            username="readonly-visitor",
            password="TestPass123!",  # pragma: allowlist secret
        )
        cls.regular_user = User.objects.create_user(
            username="regular-user",
            password="TestPass123!",  # pragma: allowlist secret
        )

    def test_pool_visitor_at_root_gets_200_launcher(self):
        # Arrange
        self.client.force_login(self.pool_visitor)
        # Act
        resp = self.client.get("/")
        # Assert
        assert resp.status_code == 200

    def test_pool_visitor_launcher_is_guest_mode(self):
        # Arrange
        self.client.force_login(self.pool_visitor)
        # Act
        resp = self.client.get("/")
        # Assert
        assert resp.context["is_guest_launcher"] is True

    def test_readonly_visitor_at_root_gets_200_launcher(self):
        # Arrange
        self.client.force_login(self.readonly_visitor)
        # Act
        resp = self.client.get("/")
        # Assert
        assert resp.status_code == 200

    def test_readonly_visitor_launcher_is_guest_mode(self):
        # Arrange
        self.client.force_login(self.readonly_visitor)
        # Act
        resp = self.client.get("/")
        # Assert
        assert resp.context["is_guest_launcher"] is True

    def test_guest_launcher_renders_cta_region(self):
        # Arrange
        self.client.force_login(self.readonly_visitor)
        # Act
        resp = self.client.get("/")
        # Assert
        assert b"launcher-guest-cta" in resp.content

    def test_guest_launcher_cta_carries_inline_banner_marker(self):
        # Arrange
        self.client.force_login(self.readonly_visitor)
        # Act
        resp = self.client.get("/")
        # Assert
        assert b"data-readonly-inline-banner" in resp.content

    def test_guest_launcher_cta_links_to_signup(self):
        # Arrange
        self.client.force_login(self.readonly_visitor)
        # Act
        resp = self.client.get("/")
        # Assert
        assert b"/auth/signup/" in resp.content

    def test_guest_launcher_cta_links_to_login(self):
        # Arrange
        self.client.force_login(self.readonly_visitor)
        # Act
        resp = self.client.get("/")
        # Assert
        assert b"/auth/login/" in resp.content

    def test_guest_launcher_keeps_tiles_in_context(self):
        # Arrange
        self.client.force_login(self.readonly_visitor)
        # Act
        resp = self.client.get("/")
        # Assert
        assert len(resp.context["tiles"]) > 0

    def test_guest_launcher_renders_app_grid(self):
        # Arrange
        self.client.force_login(self.readonly_visitor)
        # Act
        resp = self.client.get("/")
        # Assert
        assert b"launcher-grid" in resp.content

    def test_anonymous_at_root_gets_redirect(self):
        # Arrange — no login, no visitor session (test client UA is not a
        # browser, so VisitorAutoLoginMiddleware skips allocation)
        # Act
        resp = self.client.get("/")
        # Assert
        assert resp.status_code == 302

    def test_anonymous_at_root_redirects_to_landing(self):
        # Arrange — no login, no visitor session
        # Act
        resp = self.client.get("/")
        # Assert
        assert resp.url == "/landing/"

    def test_regular_user_launcher_is_not_guest_mode(self):
        # Arrange
        self.client.force_login(self.regular_user)
        # Act
        resp = self.client.get("/")
        # Assert
        assert resp.context["is_guest_launcher"] is False

    def test_regular_user_launcher_has_no_guest_cta(self):
        # Arrange
        self.client.force_login(self.regular_user)
        # Act
        resp = self.client.get("/")
        # Assert
        assert b"launcher-guest-cta" not in resp.content


class VisitorBannerCopyTest(TestCase):
    """Writable-visitor banner: identity + honest activity-based lifetime.

    Operator report (Telegram 1301, card hub-visitor-banner-identity-and-
    lifetime): "You have a full workspace for this session" said neither
    WHO the session is nor how long it lasts. Post-#380 a visitor session
    is not a fixed hour — heartbeats extend it while the user is active,
    and the idle reaper reclaims it after
    PoolAllocator.IDLE_TIMEOUT_MINUTES of inactivity. The banner must name
    the visitor (same slice as the header's "Visitor #NNN" badge) and
    quote the enforced constant, never hardcoded prose. The readonly
    branch's copy stays as-is.

    Copy shortened to a two-liner on the operator's mobile review
    (Telegram 1400, card hub-mobile-launcher-ux-polish) — identity,
    constant-quoted lifetime, and signup CTA all survive the cut.
    """

    @classmethod
    def setUpTestData(cls):
        cls.pool_visitor = User.objects.create_user(
            username="visitor-001",
            password="TestPass123!",  # pragma: allowlist secret
        )
        cls.readonly_visitor = User.objects.create_user(
            username="readonly-visitor",
            password="TestPass123!",  # pragma: allowlist secret
        )

    def test_visitor_banner_names_the_visitor(self):
        # Arrange
        self.client.force_login(self.pool_visitor)
        # Act
        resp = self.client.get("/")
        # Assert
        assert b"Visitor #001" in resp.content

    def test_visitor_banner_quotes_idle_timeout_constant(self):
        # Arrange
        self.client.force_login(self.pool_visitor)
        # Act
        resp = self.client.get("/")
        # Assert
        assert (
            f"~{PoolAllocator.IDLE_TIMEOUT_MINUTES} min idle".encode()
            in resp.content
        )

    def test_visitor_launcher_context_exposes_idle_timeout(self):
        # Arrange
        self.client.force_login(self.pool_visitor)
        # Act
        resp = self.client.get("/")
        # Assert
        assert (
            resp.context["visitor_idle_timeout_minutes"]
            == PoolAllocator.IDLE_TIMEOUT_MINUTES
        )

    def test_visitor_banner_marks_workspace_temporary(self):
        # Arrange
        self.client.force_login(self.pool_visitor)
        # Act
        resp = self.client.get("/")
        # Assert
        assert b"temporary workspace" in resp.content

    def test_visitor_banner_drops_fixed_session_claim(self):
        # Arrange
        self.client.force_login(self.pool_visitor)
        # Act
        resp = self.client.get("/")
        # Assert
        assert b"full workspace for this session" not in resp.content

    def test_visitor_banner_keeps_signup_cta(self):
        # Arrange
        self.client.force_login(self.pool_visitor)
        # Act
        resp = self.client.get("/")
        # Assert
        assert b"sign up to keep your work" in resp.content

    def test_readonly_banner_copy_unchanged(self):
        # Arrange
        self.client.force_login(self.readonly_visitor)
        # Act
        resp = self.client.get("/")
        # Assert
        assert b"browsing read-only" in resp.content

    def test_readonly_banner_makes_no_idle_timeout_claim(self):
        # Arrange
        self.client.force_login(self.readonly_visitor)
        # Act
        resp = self.client.get("/")
        # Assert
        assert b"min idle" not in resp.content


if __name__ == "__main__":
    import os

    import pytest

    pytest.main([os.path.abspath(__file__)])

# EOF
