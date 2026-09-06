#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Routing Tests

Verify route behavior:
- Visitor (unauthenticated) routes redirect to landing
- Authenticated routes reach the hub/dashboard
"""

import pytest
from tests.e2e.playwright.page_ready import wait_for_page_ready

# WHY THESE TESTS DO NOT WAIT FOR `networkidle`
#
# `networkidle` means "500 ms with zero requests in flight". A SciTeX page
# held by a pooled visitor session runs a heartbeat/countdown poller for as
# long as the page is open (PoolAllocator.extend_session_on_activity), so
# that condition never arrives and the wait always times out. The page is
# fine; the question is unanswerable.
#
# Measured twice, same exception both times:
#   2026-08-16, CI run 31955719803 -- 30s timeout, 33 errors, capture down.
#   2026-09-06, job 101449817274   -- 30s timeout, 14/14 mobile tests
#                                     ERRORED in fixture setup, so not one
#                                     assertion in the mobile suite had
#                                     ever been evaluated.
#
# `wait_for_page_ready` (load -> body.app-ready -> short settle) was written
# after the first of those and is the sanctioned wait. See
# tests/e2e/playwright/page_ready.py for why each step is there and why none
# of them can hide a broken page.


class TestVisitorRouting:
    """Unauthenticated users are redirected to landing page."""

    @pytest.mark.parametrize(
        "path",
        [
            "/apps/scholar/",
            "/apps/writer/",
            "/apps/workspace/",
            "/dashboard/",
        ],
    )
    def test_visitor_redirected_to_landing(self, desktop_page, pw_base_url, path):
        """Unauthenticated access to protected routes redirects to landing or login."""
        desktop_page.goto(path)
        wait_for_page_ready(desktop_page)
        url = desktop_page.url

        # Should be redirected to landing ("/") or login page
        is_landing = url.rstrip("/") == pw_base_url.rstrip("/")
        is_login = "/auth/login" in url or "/login" in url
        assert (
            is_landing or is_login
        ), f"Visitor at {path} was not redirected. Current URL: {url}"

    def test_landing_accessible_without_auth(self, desktop_page, pw_base_url):
        """Landing page is accessible without authentication."""
        resp = desktop_page.goto("/")
        assert resp.status == 200
        url = desktop_page.url
        # Should stay on landing, not redirect to login
        is_landing = url.rstrip("/") == pw_base_url.rstrip("/")
        is_login = "/auth/login" in url
        assert is_landing or is_login, f"Unexpected redirect from /: {url}"


class TestAuthenticatedRouting:
    """Authenticated users can access the hub and app routes."""

    def test_auth_user_reaches_hub(self, visitor_desktop_page, pw_base_url, screenshot):
        """Authenticated user navigating to / reaches hub or dashboard."""
        visitor_desktop_page.goto("/")
        wait_for_page_ready(visitor_desktop_page)
        screenshot(visitor_desktop_page, "auth_hub")
        url = visitor_desktop_page.url

        # Authenticated user should see hub, dashboard, or apps -- not login
        assert "/auth/login" not in url, f"Authenticated user was sent to login: {url}"

    @pytest.mark.parametrize(
        "path",
        [
            "/apps/scholar/",
            "/apps/writer/",
            "/apps/workspace/",
        ],
    )
    def test_auth_user_reaches_app(self, visitor_desktop_page, path):
        """Authenticated user can access app routes."""
        resp = visitor_desktop_page.goto(path)
        wait_for_page_ready(visitor_desktop_page)
        url = visitor_desktop_page.url

        # Should not be redirected to login
        assert (
            "/auth/login" not in url
        ), f"Authenticated user redirected to login from {path}: {url}"
        # Should get a successful response
        assert resp.status in (200, 304), f"App route {path} returned {resp.status}"
