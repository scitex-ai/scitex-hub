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


if __name__ == "__main__":
    import os

    import pytest

    pytest.main([os.path.abspath(__file__)])

# EOF
