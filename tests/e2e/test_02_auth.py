#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Authentication Tests

Test login/logout flows.
Requires a test user to exist in the database.

Priority: HIGH
Run time: < 30 seconds
"""

import pytest
import re


class TestLogin:
    """Test user login functionality."""

    def test_login_page_loads(self, api_client):
        """Login page loads successfully."""
        resp = api_client.get("/auth/login/")
        assert resp.status_code == 200
        assert "csrfmiddlewaretoken" in resp.text

    def test_login_with_invalid_credentials(self, api_client):
        """Login fails with invalid credentials."""
        # Get CSRF token
        resp = api_client.get("/auth/login/")
        csrf_match = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', resp.text)

        if not csrf_match:
            pytest.skip("Cannot extract CSRF token")

        csrf_token = csrf_match.group(1)

        # Try login with bad credentials
        resp = api_client.post(
            "/auth/login/",
            data={
                "csrfmiddlewaretoken": csrf_token,
                "login": "nonexistent_user_12345",
                "password": "wrongpassword",
            },
            headers={"Referer": api_client.base_url + "/auth/login/"},
            allow_redirects=False,
        )

        # Should not redirect to dashboard (login failed)
        # Either stays on login page (200) or shows error
        assert resp.status_code in [200, 302]
        if resp.status_code == 302:
            # If redirect, should be back to login, not to dashboard
            location = resp.headers.get("Location", "")
            assert "login" in location.lower() or not any(x in location for x in ["/dashboard", "/files/"])

    def test_login_with_valid_credentials(self, authenticated_session, base_url):
        """Login succeeds with valid credentials."""
        # authenticated_session fixture handles login
        # Just verify we can access authenticated content
        resp = authenticated_session.get(f"{base_url}/")
        assert resp.status_code == 200


class TestLogout:
    """Test user logout functionality."""

    def test_logout_redirects(self, authenticated_session, base_url):
        """Logout redirects to appropriate page."""
        resp = authenticated_session.get(f"{base_url}/auth/logout/", allow_redirects=False)
        # Should redirect (302) or show logout confirmation
        assert resp.status_code in [200, 302]


class TestSessionSecurity:
    """Test session security features."""

    def test_protected_page_requires_auth(self, api_client):
        """Protected pages require authentication."""
        resp = api_client.get("/new/", allow_redirects=False)
        # Should redirect to login
        assert resp.status_code in [302, 403]
        if resp.status_code == 302:
            location = resp.headers.get("Location", "")
            assert "login" in location.lower()

    def test_csrf_protection_active(self, api_client):
        """CSRF protection is active on forms."""
        resp = api_client.get("/auth/login/")
        assert resp.status_code == 200
        # Check for CSRF token in form
        assert "csrfmiddlewaretoken" in resp.text
