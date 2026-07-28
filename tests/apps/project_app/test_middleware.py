#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for apps/infra/project_app/middleware.py — VisitorAutoLoginMiddleware
skip-list, and the first-time-visitor → marketing-landing routing it enables.

Card hub-landing-page-for-logged-out-visitors-20260727 (routing fix):

A first-time BROWSER visitor must reach the EXISTING marketing landing
(/landing/) ANONYMOUSLY. Before this fix, VisitorAutoLoginMiddleware
auto-allocated a visitor slot (or the shared readonly-visitor) for a browser
GET "/", which made the session is_authenticated so root_dispatch served the
app launcher instead of the marketing landing — and burned a scarce pool slot
just to VIEW a marketing page.

The fix EXACT-skips "/" and "/landing/" in the auto-login middleware (never a
startswith prefix — "/" is a prefix of every URL). A visitor still gets a slot
the instant they CHOOSE to enter the workspace via the hero CTA (/apps/home/),
which is NOT skip-listed.

A session that HAS entered the workspace is ROLE_VISITOR / ROLE_READONLY_VISITOR
and must STAY in the workspace launcher (guest mode) — bouncing it to marketing
on every Home ("/") click is the breakage card hub-visitor-ux-allapps
(operator-confirmed 2026-07-07) forbids. That guest-mode behaviour is asserted
here and in tests/apps/apps_app/test_launcher_guest_mode.py.

No mocks — real Django test DB + RequestFactory / test client (same
conventions as test_launcher_guest_mode.py). One assertion per test
(STX-TQ007).
"""

from importlib import import_module

from django.conf import settings
from django.contrib.auth.models import AnonymousUser, User
from django.test import RequestFactory, TestCase

from apps.infra.project_app.middleware import VisitorAutoLoginMiddleware
from apps.infra.project_app.models import VisitorAllocation

# A real browser User-Agent — VisitorAutoLoginMiddleware only auto-logs-in
# browser requests (curl/wget/empty-UA are skipped as non-browser).
BROWSER_UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)

_SessionStore = import_module(settings.SESSION_ENGINE).SessionStore


def _noop_get_response(request):  # pragma: no cover - never invoked here
    return None


class VisitorAutoLoginExactSkipTest(TestCase):
    """`_sync_body` must NOT auto-login on "/" or "/landing/", but MUST still
    auto-login on a real workspace-entry path (the hero CTA target)."""

    @classmethod
    def setUpTestData(cls):
        # Only the shared readonly account exists (no writable slots). This is
        # exactly what turned a browser hitting a non-skipped path into a
        # logged-in readonly-visitor — the mechanism we assert "/" no longer
        # triggers, and that /apps/home/ still does.
        cls.readonly_visitor = User.objects.create_user(
            username="readonly-visitor",
            password="TestPass123!",  # pragma: allowlist secret
        )

    def _run(self, path):
        request = RequestFactory().get(path, HTTP_USER_AGENT=BROWSER_UA)
        request.user = AnonymousUser()
        request.session = _SessionStore()
        VisitorAutoLoginMiddleware(_noop_get_response)._sync_body(request)
        return request

    def test_root_browser_stays_anonymous(self):
        # Arrange: a first-time browser GET of the bare root
        # Act
        request = self._run("/")
        # Assert — "/" is exact-skipped, so no auto-login happened
        assert request.user.is_authenticated is False

    def test_landing_browser_stays_anonymous(self):
        # Arrange: a first-time browser GET of the marketing landing
        # Act
        request = self._run("/landing/")
        # Assert
        assert request.user.is_authenticated is False

    def test_root_browser_burns_no_visitor_slot(self):
        # Arrange: a first-time browser GET of the bare root
        # Act
        self._run("/")
        # Assert — merely viewing "/" allocates nothing (pool is near full)
        assert VisitorAllocation.objects.count() == 0

    def test_root_browser_sets_no_readonly_flag(self):
        # Arrange: a first-time browser GET of the bare root
        # Act
        request = self._run("/")
        # Assert
        assert request.session.get("is_readonly_visitor") is None

    def test_workspace_entry_path_still_auto_logs_in(self):
        # Arrange: a browser that DELIBERATELY enters via the hero CTA target
        # Act — /apps/home/ is deliberately NOT skip-listed, so a visitor who
        # chooses to enter still gets logged in (readonly fallback here, since
        # the writable pool is empty).
        request = self._run("/apps/home/")
        # Assert
        assert request.user.is_authenticated is True


class FirstTimeBrowserRoutingTest(TestCase):
    """End-to-end: a first-time browser GET "/" reaches the marketing landing
    (302 → /landing/), not the launcher, and allocates no slot."""

    @classmethod
    def setUpTestData(cls):
        cls.readonly_visitor = User.objects.create_user(
            username="readonly-visitor",
            password="TestPass123!",  # pragma: allowlist secret
        )

    def test_browser_root_redirects(self):
        # Arrange: a first-time browser (no session)
        # Act
        resp = self.client.get("/", HTTP_USER_AGENT=BROWSER_UA)
        # Assert — anonymous → redirect (pre-fix this was 200, the launcher)
        assert resp.status_code == 302

    def test_browser_root_redirect_target_is_landing(self):
        # Arrange: a first-time browser (no session)
        # Act
        resp = self.client.get("/", HTTP_USER_AGENT=BROWSER_UA)
        # Assert
        assert resp.url == "/landing/"

    def test_browser_root_does_not_authenticate(self):
        # Arrange: a first-time browser (no session)
        # Act
        self.client.get("/", HTTP_USER_AGENT=BROWSER_UA)
        # Assert — session carries no auth: the visitor stayed anonymous
        assert "_auth_user_id" not in self.client.session

    def test_browser_root_allocates_no_slot(self):
        # Arrange: a first-time browser (no session)
        # Act
        self.client.get("/", HTTP_USER_AGENT=BROWSER_UA)
        # Assert
        assert VisitorAllocation.objects.count() == 0

    def test_browser_landing_renders_for_anonymous(self):
        # Arrange: a first-time browser (no session)
        # Act
        resp = self.client.get("/landing/", HTTP_USER_AGENT=BROWSER_UA)
        # Assert
        assert resp.status_code == 200

    def test_browser_landing_does_not_authenticate(self):
        # Arrange: a first-time browser (no session)
        # Act
        self.client.get("/landing/", HTTP_USER_AGENT=BROWSER_UA)
        # Assert
        assert "_auth_user_id" not in self.client.session


class WorkspaceVisitorNotBouncedTest(TestCase):
    """A visitor who HAS entered the workspace (holds a slot / is signed in as
    a visitor role) must stay in the launcher at "/", NOT bounce to landing.

    Guards against the literal-but-wrong reading "visitor → landing": the
    sidebar/dock "Home" links to "/", so that reading would eject an active
    guest on every Home click (card hub-visitor-ux-allapps)."""

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

    def test_pool_visitor_at_root_stays_in_workspace(self):
        # Arrange
        self.client.force_login(self.pool_visitor)
        # Act
        resp = self.client.get("/")
        # Assert — launcher renders (200), not a redirect to /landing/
        assert resp.status_code == 200

    def test_readonly_visitor_at_root_stays_in_workspace(self):
        # Arrange
        self.client.force_login(self.readonly_visitor)
        # Act
        resp = self.client.get("/")
        # Assert
        assert resp.status_code == 200


if __name__ == "__main__":
    import os

    import pytest

    pytest.main([os.path.abspath(__file__)])

# EOF
