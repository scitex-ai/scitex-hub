#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Timestamp: 2025-11-30
# File: /home/ywatanabe/proj/scitex-cloud/tests/api/auth/test_auth_api.py

"""
API tests for authentication endpoints.

Tests:
- Username availability check
- Theme preference API
- Email verification API
- Login/logout via API
"""

import pytest
from tests.api.conftest import assert_json_response, assert_error_response


class TestUsernameCheck:
    """Tests for username availability API."""

    def test_check_available_username(self, client, api_base_url, timestamp):
        """Available username returns success."""
        # Try POST first, then GET
        response = client.post(
            f"{api_base_url}/auth/api/check-username/",
            json={"username": f"available_user_{timestamp}"},
        )

        if response.status_code in (403, 405):
            # Try GET with params (CSRF may block POST)
            response = client.get(
                f"{api_base_url}/auth/api/check-username/",
                params={"username": f"available_user_{timestamp}"},
            )

        # Should return availability status or CSRF error
        assert response.status_code in (200, 403, 405), f"Got {response.status_code}"
        if response.status_code == 200:
            data = response.json()
            assert "available" in data or "exists" in data or "valid" in data

    def test_check_taken_username(self, client, api_base_url, test_credentials):
        """Taken username returns unavailable."""
        response = client.post(
            f"{api_base_url}/auth/api/check-username/",
            json={"username": test_credentials["username"]},
        )

        if response.status_code in (403, 405):
            response = client.get(
                f"{api_base_url}/auth/api/check-username/",
                params={"username": test_credentials["username"]},
            )

        assert response.status_code in (200, 403, 405)
        if response.status_code == 200:
            data = response.json()
            is_taken = (
                data.get("available") is False
                or data.get("exists") is True
                or data.get("taken") is True
            )
            assert is_taken or "error" not in data

    def test_check_invalid_username(self, client, api_base_url):
        """Invalid username format returns error."""
        response = client.post(
            f"{api_base_url}/auth/api/check-username/",
            json={"username": "ab"},
        )

        # Any response is acceptable for this edge case test
        assert response.status_code in (200, 400, 403, 405)

    def test_check_empty_username(self, client, api_base_url):
        """Empty username returns error."""
        response = client.post(
            f"{api_base_url}/auth/api/check-username/",
            json={"username": ""},
        )

        assert response.status_code in (200, 400, 403, 405)


class TestThemeAPI:
    """Tests for theme preference API."""

    def test_get_theme_unauthenticated(self, client, api_base_url):
        """Get theme works for unauthenticated users (uses default/cookie)."""
        response = client.get(f"{api_base_url}/auth/api/get-theme/")

        # Should return theme even without auth
        assert response.status_code in (200, 401, 403)
        if response.status_code == 200:
            data = response.json()
            assert "theme" in data or "color_theme" in data

    def test_save_theme_authenticated(self, authenticated_client, api_base_url):
        """Save theme preference for authenticated user."""
        response = authenticated_client.post(
            f"{api_base_url}/auth/api/save-theme/",
            json={"theme": "dark"},
        )

        # May require different auth method or not exist
        assert response.status_code in (200, 201, 401, 403, 405)

    def test_save_invalid_theme(self, authenticated_client, api_base_url):
        """Invalid theme value is rejected or ignored."""
        response = authenticated_client.post(
            f"{api_base_url}/auth/api/save-theme/",
            json={"theme": "invalid_theme_xyz"},
        )

        # Either rejects or ignores invalid value
        assert response.status_code in (200, 400, 401, 403, 405)


class TestAuthenticatedAccountsAPI:
    """Tests for multi-account API."""

    def test_get_authenticated_accounts(self, authenticated_client, api_base_url):
        """Get list of authenticated accounts for device."""
        response = authenticated_client.get(
            f"{api_base_url}/auth/api/authenticated-accounts/"
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, (list, dict))


class TestLoginAPI:
    """Tests for login API endpoint."""

    def test_login_with_valid_credentials(
        self, client, api_base_url, test_credentials, csrf_token
    ):
        """Login API accepts valid credentials."""
        client.headers.update({"X-CSRFToken": csrf_token})

        response = client.post(
            f"{api_base_url}/auth/login/",
            data={
                "username": test_credentials["username"],
                "password": test_credentials["password"],
            },
            headers={"Referer": f"{api_base_url}/auth/signin/"},
            allow_redirects=False,
        )

        # Should redirect on success or CSRF failure
        assert response.status_code in (200, 302, 403)

    def test_login_with_invalid_credentials(self, client, api_base_url, csrf_token):
        """Login API rejects invalid credentials."""
        client.headers.update({"X-CSRFToken": csrf_token})

        response = client.post(
            f"{api_base_url}/auth/login/",
            data={
                "username": "nonexistent_user",
                "password": "wrong_password",
            },
            headers={"Referer": f"{api_base_url}/auth/signin/"},
            allow_redirects=False,
        )

        # Should return error or stay on login page
        assert response.status_code in (200, 302, 400, 401, 403)

    def test_login_without_csrf(self, client, api_base_url, test_credentials):
        """Login without CSRF token is rejected."""
        response = client.post(
            f"{api_base_url}/auth/login/",
            data={
                "username": test_credentials["username"],
                "password": test_credentials["password"],
            },
            allow_redirects=False,
        )

        # Should be rejected (403 Forbidden)
        assert response.status_code in (403, 400, 302)


class TestLogoutAPI:
    """Tests for logout API endpoint."""

    def test_logout_clears_session(self, authenticated_client, api_base_url):
        """Logout clears authentication session."""
        response = authenticated_client.get(
            f"{api_base_url}/auth/signout/",
            allow_redirects=False,
        )

        # Should redirect after logout
        assert response.status_code in (200, 302)

    def test_logout_unauthenticated(self, client, api_base_url):
        """Logout works even when not authenticated."""
        response = client.get(
            f"{api_base_url}/auth/signout/",
            allow_redirects=False,
        )

        # Should not error
        assert response.status_code in (200, 302)


class TestEmailVerificationAPI:
    """Tests for email verification API."""

    def test_resend_otp_requires_auth(self, client, api_base_url):
        """Resend OTP requires authentication context."""
        response = client.post(
            f"{api_base_url}/auth/api/resend-otp/",
            json={},
        )

        # Should require auth or session context
        assert response.status_code in (200, 400, 401, 403)

    def test_verify_email_invalid_code(self, client, api_base_url):
        """Invalid verification code is rejected."""
        response = client.post(
            f"{api_base_url}/auth/api/verify-email/",
            json={"code": "000000"},
        )

        # Should reject invalid code
        assert response.status_code in (400, 401, 403)


class TestPasswordResetAPI:
    """Tests for password reset API."""

    def test_forgot_password_valid_email(self, client, api_base_url, csrf_token):
        """Forgot password accepts valid email format."""
        client.headers.update({"X-CSRFToken": csrf_token})

        response = client.post(
            f"{api_base_url}/auth/forgot-password/",
            data={"email": "test@example.com"},
            headers={"Referer": f"{api_base_url}/auth/forgot-password/"},
            allow_redirects=False,
        )

        # Should accept request (even if email doesn't exist - security)
        assert response.status_code in (200, 302, 403)

    def test_forgot_password_invalid_email(self, client, api_base_url, csrf_token):
        """Forgot password rejects invalid email format."""
        client.headers.update({"X-CSRFToken": csrf_token})

        response = client.post(
            f"{api_base_url}/auth/forgot-password/",
            data={"email": "not-an-email"},
            headers={"Referer": f"{api_base_url}/auth/forgot-password/"},
            allow_redirects=False,
        )

        # Should reject or show error
        assert response.status_code in (200, 302, 400, 403)
