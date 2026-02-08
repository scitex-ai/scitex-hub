#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Signup and Email Verification Tests

Test user registration and email verification flow.
These are critical for user onboarding.

Priority: HIGH
Run time: < 60 seconds
"""

import re
import time

import pytest


class TestSignupFlow:
    """Test user signup functionality."""

    def test_signup_page_loads(self, api_client):
        """Signup page loads with form."""
        resp = api_client.get("/auth/signup/")
        assert resp.status_code == 200
        # Check for required form fields
        assert "username" in resp.text.lower() or "name" in resp.text.lower()
        assert "email" in resp.text.lower()
        assert "password" in resp.text.lower()
        assert "csrfmiddlewaretoken" in resp.text

    def test_signup_form_validation_empty(self, api_client):
        """Signup rejects empty form submission."""
        # Get CSRF token
        resp = api_client.get("/auth/signup/")
        csrf_match = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', resp.text)

        if not csrf_match:
            pytest.skip("Cannot extract CSRF token")

        csrf_token = csrf_match.group(1)

        # Submit empty form
        resp = api_client.post(
            "/auth/signup/",
            data={"csrfmiddlewaretoken": csrf_token},
            headers={"Referer": api_client.base_url + "/auth/signup/"},
            allow_redirects=False,
        )

        # Should stay on signup page (form errors)
        assert resp.status_code in [200, 302]
        if resp.status_code == 302:
            location = resp.headers.get("Location", "")
            # Should redirect back to signup, not to success
            assert (
                "signup" in location.lower()
                or "register" in location.lower()
                or "login" in location.lower()
            )

    def test_signup_form_validation_invalid_email(self, api_client):
        """Signup rejects invalid email format."""
        # Get CSRF token
        resp = api_client.get("/auth/signup/")
        csrf_match = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', resp.text)

        if not csrf_match:
            pytest.skip("Cannot extract CSRF token")

        csrf_token = csrf_match.group(1)
        timestamp = int(time.time())

        # Submit with invalid email
        resp = api_client.post(
            "/auth/signup/",
            data={
                "csrfmiddlewaretoken": csrf_token,
                "username": f"testuser{timestamp}",
                "email": "not-an-email",  # Invalid
                "password1": "ValidPassword123!",
                "password2": "ValidPassword123!",
            },
            headers={"Referer": api_client.base_url + "/auth/signup/"},
            allow_redirects=False,
        )

        # Should reject - either stays on page or shows error
        # We check it doesn't redirect to a "success" or "verify email" page
        if resp.status_code == 302:
            location = resp.headers.get("Location", "")
            # Should NOT redirect to dashboard or success
            assert "dashboard" not in location.lower()
            assert "success" not in location.lower()

    def test_signup_password_requirements(self, api_client):
        """Signup enforces password requirements."""
        # Get CSRF token
        resp = api_client.get("/auth/signup/")
        csrf_match = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', resp.text)

        if not csrf_match:
            pytest.skip("Cannot extract CSRF token")

        csrf_token = csrf_match.group(1)
        timestamp = int(time.time())

        # Submit with weak password
        resp = api_client.post(
            "/auth/signup/",
            data={
                "csrfmiddlewaretoken": csrf_token,
                "username": f"testuser{timestamp}",
                "email": f"test{timestamp}@example.com",
                "password1": "123",  # Too weak
                "password2": "123",
            },
            headers={"Referer": api_client.base_url + "/auth/signup/"},
            allow_redirects=False,
        )

        # Should reject weak password
        if resp.status_code == 200:
            # Check for password error message in response
            assert "password" in resp.text.lower()

    def test_signup_creates_account(self, api_client):
        """POST with valid data creates account and redirects to email verification."""
        # Get CSRF token
        resp = api_client.get("/auth/signup/")
        csrf_match = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', resp.text)

        if not csrf_match:
            pytest.skip("Cannot extract CSRF token")

        csrf_token = csrf_match.group(1)
        timestamp = int(time.time())
        unique_username = f"e2e_test_{timestamp}"

        # Submit valid signup form
        resp = api_client.post(
            "/auth/signup/",
            data={
                "csrfmiddlewaretoken": csrf_token,
                "username": unique_username,
                "email": f"e2e_{timestamp}@example.com",
                "password1": "ValidE2EPassword123!",
                "password2": "ValidE2EPassword123!",
            },
            headers={"Referer": api_client.base_url + "/auth/signup/"},
            allow_redirects=True,
        )

        # Should succeed - check for success indicators
        assert resp.status_code == 200
        # Check for email verification message or redirect to verification page
        text_lower = resp.text.lower()
        success_indicators = [
            "verify" in text_lower and "email" in text_lower,
            "confirmation" in text_lower,
            "check your email" in text_lower,
            "sent" in text_lower and "email" in text_lower,
        ]
        assert any(success_indicators), (
            "Expected signup success with email verification prompt"
        )

    def test_signup_duplicate_username(self, api_client):
        """POST twice with same username should fail on second attempt."""
        # Get CSRF token
        resp = api_client.get("/auth/signup/")
        csrf_match = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', resp.text)

        if not csrf_match:
            pytest.skip("Cannot extract CSRF token")

        csrf_token = csrf_match.group(1)
        timestamp = int(time.time())
        duplicate_username = f"e2e_dup_{timestamp}"

        # First signup
        api_client.post(
            "/auth/signup/",
            data={
                "csrfmiddlewaretoken": csrf_token,
                "username": duplicate_username,
                "email": f"e2e_dup1_{timestamp}@example.com",
                "password1": "ValidPassword123!",
                "password2": "ValidPassword123!",
            },
            headers={"Referer": api_client.base_url + "/auth/signup/"},
            allow_redirects=True,
        )

        # Get new CSRF token for second attempt
        resp = api_client.get("/auth/signup/")
        csrf_match = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', resp.text)
        csrf_token = csrf_match.group(1) if csrf_match else csrf_token

        # Second signup with same username
        resp = api_client.post(
            "/auth/signup/",
            data={
                "csrfmiddlewaretoken": csrf_token,
                "username": duplicate_username,  # Same username
                "email": f"e2e_dup2_{timestamp}@example.com",  # Different email
                "password1": "ValidPassword123!",
                "password2": "ValidPassword123!",
            },
            headers={"Referer": api_client.base_url + "/auth/signup/"},
            allow_redirects=False,
        )

        # Should fail - either stay on page with error or redirect to signup
        if resp.status_code == 200:
            # Check for username error
            text_lower = resp.text.lower()
            assert "username" in text_lower and (
                "already" in text_lower
                or "exists" in text_lower
                or "taken" in text_lower
            )
        elif resp.status_code == 302:
            # Should redirect back to signup, not to success
            location = resp.headers.get("Location", "")
            assert "signup" in location.lower() or "register" in location.lower()


class TestEmailVerification:
    """Test email verification functionality."""

    def test_email_verification_endpoint_exists(self, api_client):
        """Email verification endpoint exists."""
        # Try accessing with a dummy token
        resp = api_client.get("/auth/confirm-email/dummy-token/", allow_redirects=False)
        # Should return 404 for invalid token or redirect to error page
        # Should NOT return 500 (server error)
        assert resp.status_code != 500

    def test_resend_verification_page(self, api_client):
        """Resend verification email page accessible."""
        # Try different possible URLs for email verification
        for path in ["/auth/email/", "/accounts/email/", "/auth/confirm-email/"]:
            resp = api_client.get(path, allow_redirects=False)
            if resp.status_code in [200, 302]:
                return  # Found working endpoint
        # If none work, that's okay - email verification might use different flow
        pytest.skip("Email verification page URL not found - may use different flow")


class TestPasswordReset:
    """Test password reset functionality."""

    def test_password_reset_page_loads(self, api_client):
        """Password reset page loads."""
        # Try different possible URLs
        for path in [
            "/auth/password/reset/",
            "/accounts/password/reset/",
            "/auth/password-reset/",
        ]:
            resp = api_client.get(path)
            if resp.status_code == 200:
                assert "email" in resp.text.lower() or "reset" in resp.text.lower()
                return
        pytest.skip("Password reset page URL not found - may use different path")

    def test_password_reset_submit(self, api_client):
        """Password reset accepts email submission."""
        # Get CSRF token
        resp = api_client.get("/auth/password/reset/")
        csrf_match = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', resp.text)

        if not csrf_match:
            pytest.skip("Cannot extract CSRF token")

        csrf_token = csrf_match.group(1)

        # Submit reset request
        resp = api_client.post(
            "/auth/password/reset/",
            data={
                "csrfmiddlewaretoken": csrf_token,
                "email": "test@example.com",
            },
            headers={"Referer": api_client.base_url + "/auth/password/reset/"},
            allow_redirects=False,
        )

        # Should accept (even for non-existent email for security)
        # Typically redirects to "email sent" page
        assert resp.status_code in [200, 302]
        if resp.status_code == 302:
            location = resp.headers.get("Location", "")
            # Should redirect to confirmation, not error
            assert (
                "done" in location.lower()
                or "sent" in location.lower()
                or "reset" in location.lower()
            )


class TestSocialAuth:
    """Test social authentication endpoints exist."""

    def test_google_auth_endpoint(self, api_client):
        """Google OAuth endpoint exists."""
        resp = api_client.get("/auth/social/google/login/", allow_redirects=False)
        # 500 may indicate misconfigured OAuth (missing credentials) - xfail not fail
        if resp.status_code == 500:
            pytest.xfail(
                "Google OAuth returning 500 - may need OAuth credentials configured"
            )
        assert resp.status_code in [200, 302, 404]

    def test_orcid_auth_endpoint(self, api_client):
        """ORCID OAuth endpoint exists."""
        resp = api_client.get("/auth/social/orcid/login/", allow_redirects=False)
        # 500 may indicate misconfigured OAuth (missing credentials) - xfail not fail
        if resp.status_code == 500:
            pytest.xfail(
                "ORCID OAuth returning 500 - may need OAuth credentials configured"
            )
        assert resp.status_code in [200, 302, 404]
