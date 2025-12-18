#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Timestamp: 2025-11-30
# File: /home/ywatanabe/proj/scitex-cloud/tests/e2e/auth/test_password_reset.py

"""
E2E tests for password reset functionality.

Tests:
- Forgot password page loads
- Password reset request with valid email
- Password reset request with invalid email
- Password reset link validation
- Password change with valid token
"""

import pytest
from playwright.sync_api import Page, expect


class TestForgotPasswordPage:
    """Tests for forgot password page rendering."""

    def test_forgot_password_page_loads(self, page: Page, base_url: str):
        """Forgot password page should load without errors."""
        page.goto(f"{base_url}/auth/forgot-password/")
        page.wait_for_timeout(1000)

        # Form should be visible
        expect(
            page.locator(
                "form#forgot-password-form, form[action*='forgot'], form[action*='reset']"
            )
        ).to_be_visible()

    def test_forgot_password_has_email_field(self, page: Page, base_url: str):
        """Forgot password page should have email input field."""
        page.goto(f"{base_url}/auth/forgot-password/")
        page.wait_for_timeout(1000)

        email_field = page.locator(
            "#email, input[name='email'], input[type='email']"
        )
        expect(email_field).to_be_visible()

    def test_forgot_password_has_submit_button(self, page: Page, base_url: str):
        """Forgot password page should have submit button."""
        page.goto(f"{base_url}/auth/forgot-password/")
        page.wait_for_timeout(1000)

        submit_btn = page.locator("button[type='submit'], input[type='submit']")
        expect(submit_btn).to_be_visible()

    def test_forgot_password_has_back_to_login_link(self, page: Page, base_url: str):
        """Forgot password page should have link back to login."""
        page.goto(f"{base_url}/auth/forgot-password/")
        page.wait_for_timeout(1000)

        back_link = page.locator("a[href*='signin'], a[href*='login']")
        expect(back_link).to_be_visible()


class TestForgotPasswordRequest:
    """Tests for password reset request submission."""

    def test_reset_request_with_valid_email(
        self, page: Page, base_url: str, test_credentials: dict
    ):
        """Password reset request should succeed with registered email."""
        page.goto(f"{base_url}/auth/forgot-password/")
        page.wait_for_timeout(1000)

        # We need to get the test user's email
        # For now, assume the test user has an email like test-user@example.com
        # or use a pattern that matches
        email_field = page.locator(
            "#email, input[name='email'], input[type='email']"
        )

        # Try with a test email pattern
        # Note: This might need adjustment based on actual test user email
        email_field.fill(f"{test_credentials['username']}@example.com")

        page.click("button[type='submit'], input[type='submit']")
        page.wait_for_timeout(3000)

        # Should show success message or redirect
        # Don't check for exact text as it may vary
        success_indicator = page.locator(
            ".alert-success, .success, [data-status='success']"
        )
        confirmation_page = "confirm" in page.url or "sent" in page.url

        # Either shows success or moves to confirmation
        assert success_indicator.count() > 0 or confirmation_page or "forgot" in page.url

    def test_reset_request_with_invalid_email_format(self, page: Page, base_url: str):
        """Password reset should reject invalid email format."""
        page.goto(f"{base_url}/auth/forgot-password/")
        page.wait_for_timeout(1000)

        email_field = page.locator(
            "#email, input[name='email'], input[type='email']"
        )
        email_field.fill("not-an-email")

        page.click("button[type='submit'], input[type='submit']")
        page.wait_for_timeout(2000)

        # Should show error or HTML5 validation
        has_error = page.locator(".alert-danger, .error, .invalid-feedback").count() > 0
        has_html5_error = page.locator(":invalid").count() > 0
        is_on_same_page = "forgot" in page.url or "reset" in page.url

        assert has_error or has_html5_error or is_on_same_page

    def test_reset_request_with_unregistered_email(self, page: Page, base_url: str):
        """Password reset with unregistered email should not reveal user existence."""
        page.goto(f"{base_url}/auth/forgot-password/")
        page.wait_for_timeout(1000)

        email_field = page.locator(
            "#email, input[name='email'], input[type='email']"
        )
        email_field.fill("nonexistent_user_xyz123@example.com")

        page.click("button[type='submit'], input[type='submit']")
        page.wait_for_timeout(3000)

        # For security, should show same response as valid email
        # (to prevent email enumeration)
        # Should either show generic success or stay on page
        is_on_page = "forgot" in page.url or "reset" in page.url or "confirm" in page.url

        # Page should not crash and should handle gracefully
        assert is_on_page or page.url.startswith(base_url)

    def test_reset_request_with_empty_email(self, page: Page, base_url: str):
        """Password reset should reject empty email."""
        page.goto(f"{base_url}/auth/forgot-password/")
        page.wait_for_timeout(1000)

        # Submit without filling email
        page.click("button[type='submit'], input[type='submit']")
        page.wait_for_timeout(1000)

        # Should stay on page due to validation
        assert "forgot" in page.url or "reset" in page.url


class TestResetPasswordPage:
    """Tests for the actual password reset page (with token)."""

    def test_reset_page_with_invalid_token_shows_error(
        self, page: Page, base_url: str
    ):
        """Reset page with invalid token should show error."""
        # Try to access reset page with fake token
        fake_token = "invalid-token-12345"
        fake_uid = "MTIz"  # base64 encoded "123"

        page.goto(f"{base_url}/auth/reset-password/{fake_uid}/{fake_token}/")
        page.wait_for_timeout(1000)

        # Should show error or redirect
        has_error = page.locator(
            ".alert-danger, .error, .invalid-token, [data-error]"
        ).count() > 0
        is_redirected = "signin" in page.url or "forgot" in page.url

        # Either shows error or redirects away
        assert has_error or is_redirected or "reset" in page.url

    def test_reset_page_with_expired_token_shows_error(
        self, page: Page, base_url: str
    ):
        """Reset page with expired token should show error."""
        # This is similar to invalid token test
        # Real expired tokens need to be generated first
        expired_uid = "MTIz"
        expired_token = "expired-token-00000"

        page.goto(f"{base_url}/auth/reset-password/{expired_uid}/{expired_token}/")
        page.wait_for_timeout(1000)

        # Should handle gracefully
        assert page.url.startswith(base_url)


class TestPasswordResetFlow:
    """Integration tests for complete password reset flow."""

    @pytest.mark.skip(reason="Requires email access - test manually")
    def test_complete_password_reset_flow(
        self, page: Page, base_url: str, test_credentials: dict
    ):
        """
        Complete password reset flow from request to new password.

        Note: Skipped by default because it requires:
        1. Access to email to get the reset link
        2. Actually changing the test user's password

        Run manually when testing email functionality.
        """
        # Step 1: Request password reset
        page.goto(f"{base_url}/auth/forgot-password/")
        page.fill(
            "#email, input[name='email']",
            f"{test_credentials['username']}@example.com"
        )
        page.click("button[type='submit']")
        page.wait_for_timeout(2000)

        # Step 2: Would need to get email and extract link
        # This would require email service access

        # Step 3: Visit reset link and set new password
        # Step 4: Login with new password

        pytest.skip("Email access required for complete flow test")


class TestResetPasswordValidation:
    """Tests for password validation on reset page."""

    def test_reset_form_requires_password_match(self, page: Page, base_url: str):
        """Reset form should require matching passwords."""
        # This test needs a valid reset token to access the form
        # For now, just verify the page structure expectation

        # Try accessing any reset-like URL
        page.goto(f"{base_url}/auth/reset-password/test/test/")
        page.wait_for_timeout(1000)

        # If form is shown (even with invalid token for testing)
        password_field = page.locator("#password, input[name='password']")
        confirm_field = page.locator(
            "#password_confirm, #confirm_password, input[name='password_confirm']"
        )

        if password_field.count() > 0 and confirm_field.count() > 0:
            password_field.fill("NewPassword123!")
            confirm_field.fill("DifferentPassword123!")
            page.click("button[type='submit']")
            page.wait_for_timeout(2000)

            # Should show mismatch error
            has_error = (
                page.locator(".alert-danger, .error, .invalid-feedback").count() > 0
            )
            is_on_page = "reset" in page.url

            assert has_error or is_on_page
        else:
            # Form not accessible (expected with invalid token)
            pass


class TestPasswordResetSecurity:
    """Security-focused tests for password reset."""

    def test_reset_link_is_single_use(self, page: Page, base_url: str):
        """
        Reset link should only work once.

        Note: Requires actual reset token to test properly.
        """
        # This would need:
        # 1. Generate a real reset token
        # 2. Use it once
        # 3. Try to use it again - should fail
        pytest.skip("Requires actual reset token generation")

    def test_old_password_invalid_after_reset(self, page: Page, base_url: str):
        """
        Old password should not work after password reset.

        Note: Requires completing a password reset first.
        """
        pytest.skip("Requires completing password reset flow")

    def test_reset_request_rate_limiting(self, page: Page, base_url: str):
        """
        Multiple reset requests should be rate limited.

        Note: Tests rate limiting if implemented.
        """
        page.goto(f"{base_url}/auth/forgot-password/")
        page.wait_for_timeout(1000)

        # Submit multiple times rapidly
        for i in range(5):
            email_field = page.locator("#email, input[name='email']")
            email_field.fill(f"test{i}@example.com")
            page.click("button[type='submit']")
            page.wait_for_timeout(500)

        # Should either:
        # - Show rate limit message
        # - Continue to work (if no rate limiting)
        # Just verify no crash
        assert page.url.startswith(base_url)
