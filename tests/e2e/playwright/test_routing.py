#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Routing Tests

Verify route behavior:
- Visitor (unauthenticated) routes redirect to landing
- Authenticated routes reach the hub/dashboard
"""

import pytest


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
        desktop_page.wait_for_load_state("networkidle")
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
        visitor_desktop_page.wait_for_load_state("networkidle")
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
        visitor_desktop_page.wait_for_load_state("networkidle")
        url = visitor_desktop_page.url

        # Should not be redirected to login
        assert (
            "/auth/login" not in url
        ), f"Authenticated user redirected to login from {path}: {url}"
        # Should get a successful response
        assert resp.status in (200, 304), f"App route {path} returned {resp.status}"
