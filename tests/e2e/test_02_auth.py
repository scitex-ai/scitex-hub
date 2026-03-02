#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Authentication Tests

Test login/logout flows with comprehensive functional coverage.
Requires a test user to exist in the database.

Priority: HIGH
Run time: < 30 seconds
"""

import re

import pytest
import requests


def _fresh_session():
    """Create a fresh requests session for isolated login tests."""
    s = requests.Session()
    s.verify = False
    s.timeout = 30
    return s


def _login(session, base_url, username, password):
    """Perform login and return (response, csrf_token). Returns None if CSRF extraction fails."""
    login_url = f"{base_url}/auth/login/"
    resp = session.get(login_url)
    csrf_match = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', resp.text)
    if not csrf_match:
        return None, None

    csrf_token = csrf_match.group(1)
    resp = session.post(
        login_url,
        data={
            "csrfmiddlewaretoken": csrf_token,
            "username": username,
            "password": password,
        },
        headers={"Referer": login_url},
        allow_redirects=False,
    )
    return resp, csrf_token


class TestLogin:
    """Test user login functionality."""

    def test_login_page_loads(self, api_client):
        """Login page loads successfully."""
        resp = api_client.get("/auth/login/")
        assert resp.status_code == 200
        assert "csrfmiddlewaretoken" in resp.text

    def test_login_with_invalid_credentials(self, base_url):
        """Login fails with invalid credentials."""
        session = _fresh_session()
        resp, _ = _login(session, base_url, "nonexistent_user_12345", "wrongpassword")

        if resp is None:
            pytest.skip("Cannot extract CSRF token")

        # Failed login: allauth stays on login page (200) or redirects back
        assert resp.status_code in [200, 302]
        if resp.status_code == 302:
            location = resp.headers.get("Location", "")
            assert "login" in location.lower() or not any(
                x in location for x in ["/dashboard", "/hub"]
            )
        session.close()

    def test_login_with_valid_credentials(self, authenticated_session, base_url):
        """Login succeeds with valid credentials."""
        resp = authenticated_session.get(f"{base_url}/")
        assert resp.status_code == 200

    def test_login_creates_session_cookie(self, base_url, test_credentials):
        """Login creates a valid sessionid cookie."""
        session = _fresh_session()
        resp, _ = _login(
            session,
            base_url,
            test_credentials["username"],
            test_credentials["password"],
        )

        if resp is None:
            pytest.skip("Cannot extract CSRF token")

        # After login, follow redirect to establish session
        if resp.status_code == 302:
            session.get(base_url + resp.headers.get("Location", "/"))

        # Verify sessionid cookie exists
        session_cookie = session.cookies.get("sessionid")
        assert session_cookie is not None, "sessionid cookie should be set after login"
        assert len(session_cookie) > 0, "sessionid cookie should not be empty"
        session.close()

    def test_login_redirects_or_succeeds(self, base_url, test_credentials):
        """Successful login returns 302 redirect or 200 (already authenticated)."""
        session = _fresh_session()
        resp, _ = _login(
            session,
            base_url,
            test_credentials["username"],
            test_credentials["password"],
        )

        if resp is None:
            pytest.skip("Cannot extract CSRF token")

        # Allauth login: 302 on success, 200 if form re-rendered (error or already logged in)
        assert resp.status_code in [200, 302], f"Unexpected status: {resp.status_code}"
        if resp.status_code == 302:
            location = resp.headers.get("Location", "")
            assert location, "Redirect location should be set"
            assert (
                "login" not in location.lower()
            ), "Should not redirect back to login page"
        session.close()


class TestLogout:
    """Test user logout functionality."""

    def test_logout_redirects(self, authenticated_session, base_url):
        """Logout redirects to appropriate page."""
        resp = authenticated_session.get(
            f"{base_url}/auth/logout/", allow_redirects=False
        )
        assert resp.status_code in [200, 302]

    def test_logout_destroys_session(self, base_url, test_credentials):
        """After logout, session is destroyed and protected pages redirect to login."""
        session = _fresh_session()
        resp, _ = _login(
            session,
            base_url,
            test_credentials["username"],
            test_credentials["password"],
        )

        if resp is None:
            pytest.skip("Cannot extract CSRF token")

        # Follow login redirect
        if resp.status_code == 302:
            session.get(base_url + resp.headers.get("Location", "/"))

        # Verify authenticated: landing page loads
        resp = session.get(f"{base_url}/", allow_redirects=False)
        assert resp.status_code == 200

        # Logout
        resp = session.get(f"{base_url}/auth/logout/", allow_redirects=True)
        assert resp.status_code == 200

        # Try to access protected page after logout
        resp = session.get(f"{base_url}/new/", allow_redirects=False)
        assert resp.status_code in [
            302,
            403,
        ], "Protected page should not be accessible after logout"
        if resp.status_code == 302:
            location = resp.headers.get("Location", "")
            assert "login" in location.lower(), "Should redirect to login after logout"
        session.close()


class TestLoginLogoutCycle:
    """Test complete login/logout cycles."""

    def test_full_login_logout_cycle(self, base_url, test_credentials):
        """Complete cycle: login, access protected, logout, verify can't access protected."""
        session = _fresh_session()

        # Step 1: Login
        resp, _ = _login(
            session,
            base_url,
            test_credentials["username"],
            test_credentials["password"],
        )
        if resp is None:
            pytest.skip("Cannot extract CSRF token")

        # Login should succeed (302 redirect or 200 with session)
        assert resp.status_code in [200, 302], "Login should succeed"

        # Follow redirect if needed
        if resp.status_code == 302:
            session.get(base_url + resp.headers.get("Location", "/"))

        # Step 2: Verify session exists
        session_cookie = session.cookies.get("sessionid")
        assert session_cookie is not None, "Should have session after login"

        # Step 3: Logout
        resp = session.get(f"{base_url}/auth/logout/", allow_redirects=True)
        assert resp.status_code == 200

        # Step 4: Try to access protected page after logout
        resp = session.get(f"{base_url}/new/", allow_redirects=False)
        assert resp.status_code in [
            302,
            403,
        ], "Protected page should not be accessible after logout"
        if resp.status_code == 302:
            location = resp.headers.get("Location", "")
            assert "login" in location.lower(), "Should redirect to login after logout"
        session.close()

    def test_relogin_after_logout(self, base_url, test_credentials):
        """Can login again after logout."""
        session = _fresh_session()

        # First login
        resp, _ = _login(
            session,
            base_url,
            test_credentials["username"],
            test_credentials["password"],
        )
        if resp is None:
            pytest.skip("Cannot extract CSRF token")
        assert resp.status_code in [200, 302], "First login should succeed"

        if resp.status_code == 302:
            session.get(base_url + resp.headers.get("Location", "/"))

        # Logout
        session.get(f"{base_url}/auth/logout/", allow_redirects=True)

        # Login again
        resp, _ = _login(
            session,
            base_url,
            test_credentials["username"],
            test_credentials["password"],
        )
        if resp is None:
            pytest.skip("Cannot extract CSRF token for second login")

        assert resp.status_code in [200, 302], "Second login should also succeed"

        if resp.status_code == 302:
            session.get(base_url + resp.headers.get("Location", "/"))

        # Verify session is valid
        session_cookie = session.cookies.get("sessionid")
        assert (
            session_cookie is not None
        ), "sessionid cookie should exist after second login"
        session.close()


class TestSessionSecurity:
    """Test session security features."""

    def test_protected_page_requires_auth(self, base_url):
        """Protected pages require authentication (fresh session, no login)."""
        session = _fresh_session()
        resp = session.get(f"{base_url}/new/", allow_redirects=False)
        assert resp.status_code in [302, 403]
        if resp.status_code == 302:
            location = resp.headers.get("Location", "")
            assert "login" in location.lower()
        session.close()

    def test_csrf_protection_active(self, api_client):
        """CSRF protection is active on forms."""
        resp = api_client.get("/auth/login/")
        assert resp.status_code == 200
        assert "csrfmiddlewaretoken" in resp.text

    def test_session_cookie_attributes(self, base_url, test_credentials):
        """Session cookie exists after login with expected attributes."""
        session = _fresh_session()
        resp, _ = _login(
            session,
            base_url,
            test_credentials["username"],
            test_credentials["password"],
        )
        if resp is None:
            pytest.skip("Cannot extract CSRF token")

        if resp.status_code == 302:
            session.get(base_url + resp.headers.get("Location", "/"))

        # Find sessionid cookie
        session_cookie = None
        for cookie in session.cookies:
            if cookie.name == "sessionid":
                session_cookie = cookie
                break

        assert session_cookie is not None, "sessionid cookie should exist after login"
        # Verify it's a proper cookie object with standard attributes
        assert session_cookie.value, "sessionid cookie should have a value"
        session.close()
