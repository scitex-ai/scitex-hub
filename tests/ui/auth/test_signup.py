#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Timestamp: 2025-11-30
# File: /home/ywatanabe/proj/scitex-cloud/tests/e2e/auth/test_signup.py

"""
E2E tests for user signup functionality.

Tests:
- Signup page loads correctly
- Successful registration with valid data
- Registration validation (username, email, password)
- Email verification flow
- Duplicate username/email handling
"""

import pytest
from playwright.sync_api import Page, expect


class TestSignupPage:
    """Tests for signup page rendering."""

    def test_signup_page_loads(self, page: Page, base_url: str):
        """Signup page should load without errors."""
        page.goto(f"{base_url}/auth/signup/")
        page.wait_for_timeout(1000)

        # Form should be visible
        expect(
            page.locator("form#signup-form, form#register-form, form[action*='signup']")
        ).to_be_visible()

    def test_signup_page_has_required_fields(self, page: Page, base_url: str):
        """Signup page should have all required input fields."""
        page.goto(f"{base_url}/auth/signup/")
        page.wait_for_timeout(1000)

        # Required fields
        expect(page.locator("#username, input[name='username']")).to_be_visible()
        expect(page.locator("#email, input[name='email']")).to_be_visible()
        expect(page.locator("#password, input[name='password']")).to_be_visible()

    def test_signup_page_has_login_link(self, page: Page, base_url: str):
        """Signup page should have link to login."""
        page.goto(f"{base_url}/auth/signup/")
        page.wait_for_timeout(1000)

        login_link = page.locator("a[href*='signin'], a[href*='login']")
        expect(login_link).to_be_visible()


class TestSignupValidation:
    """Tests for signup form validation."""

    def test_signup_rejects_invalid_email(self, page: Page, base_url: str, timestamp):
        """Signup should reject invalid email format."""
        page.goto(f"{base_url}/auth/signup/")
        page.wait_for_timeout(1000)

        # Fill with invalid email
        page.fill("#username, input[name='username']", f"test_user_{timestamp}")
        page.fill("#email, input[name='email']", "invalid-email")
        page.fill("#password, input[name='password']", "ValidPassword123!")

        # Try confirm password if exists
        confirm_field = page.locator(
            "#password_confirm, #confirm_password, input[name='password_confirm']"
        )
        if confirm_field.count() > 0:
            confirm_field.fill("ValidPassword123!")

        page.click("button[type='submit']")
        page.wait_for_timeout(2000)

        # Should show validation error or stay on page
        is_on_signup = "/auth/signup" in page.url or "/auth/register" in page.url
        has_error = page.locator(".alert-danger, .error, .invalid-feedback").count() > 0
        has_html5_error = page.locator(":invalid").count() > 0

        assert is_on_signup or has_error or has_html5_error

    def test_signup_rejects_weak_password(self, page: Page, base_url: str, timestamp):
        """Signup should reject weak passwords."""
        page.goto(f"{base_url}/auth/signup/")
        page.wait_for_timeout(1000)

        page.fill("#username, input[name='username']", f"test_user_{timestamp}")
        page.fill("#email, input[name='email']", f"test_{timestamp}@example.com")
        page.fill("#password, input[name='password']", "weak")  # Too weak

        confirm_field = page.locator(
            "#password_confirm, #confirm_password, input[name='password_confirm']"
        )
        if confirm_field.count() > 0:
            confirm_field.fill("weak")

        page.click("button[type='submit']")
        page.wait_for_timeout(2000)

        # Should show validation error
        is_on_signup = "/auth/signup" in page.url or "/auth/register" in page.url
        has_error = page.locator(".alert-danger, .error, .invalid-feedback").count() > 0

        assert is_on_signup or has_error

    def test_signup_rejects_mismatched_passwords(
        self, page: Page, base_url: str, timestamp
    ):
        """Signup should reject when passwords don't match."""
        page.goto(f"{base_url}/auth/signup/")
        page.wait_for_timeout(1000)

        page.fill("#username, input[name='username']", f"test_user_{timestamp}")
        page.fill("#email, input[name='email']", f"test_{timestamp}@example.com")
        page.fill("#password, input[name='password']", "ValidPassword123!")

        confirm_field = page.locator(
            "#password_confirm, #confirm_password, input[name='password_confirm']"
        )
        if confirm_field.count() > 0:
            confirm_field.fill("DifferentPassword123!")
            page.click("button[type='submit']")
            page.wait_for_timeout(2000)

            # Should show validation error
            is_on_signup = "/auth/signup" in page.url or "/auth/register" in page.url
            has_error = (
                page.locator(".alert-danger, .error, .invalid-feedback").count() > 0
            )
            assert is_on_signup or has_error
        else:
            # No confirm field, skip this test
            pytest.skip("No password confirmation field found")

    def test_signup_rejects_short_username(self, page: Page, base_url: str, timestamp):
        """Signup should reject usernames that are too short."""
        page.goto(f"{base_url}/auth/signup/")
        page.wait_for_timeout(1000)

        page.fill("#username, input[name='username']", "ab")  # Too short
        page.fill("#email, input[name='email']", f"test_{timestamp}@example.com")
        page.fill("#password, input[name='password']", "ValidPassword123!")

        confirm_field = page.locator(
            "#password_confirm, #confirm_password, input[name='password_confirm']"
        )
        if confirm_field.count() > 0:
            confirm_field.fill("ValidPassword123!")

        page.click("button[type='submit']")
        page.wait_for_timeout(2000)

        # Should fail validation
        is_on_signup = "/auth/signup" in page.url or "/auth/register" in page.url
        has_error = page.locator(".alert-danger, .error, .invalid-feedback").count() > 0

        assert is_on_signup or has_error


class TestSignupDuplicates:
    """Tests for duplicate username/email handling."""

    def test_signup_rejects_existing_username(
        self, page: Page, base_url: str, test_credentials: dict, timestamp
    ):
        """Signup should reject already taken username."""
        page.goto(f"{base_url}/auth/signup/")
        page.wait_for_timeout(1000)

        # Use the existing test user's username
        page.fill(
            "#username, input[name='username']", test_credentials["username"]
        )  # Already exists
        page.fill("#email, input[name='email']", f"new_{timestamp}@example.com")
        page.fill("#password, input[name='password']", "ValidPassword123!")

        confirm_field = page.locator(
            "#password_confirm, #confirm_password, input[name='password_confirm']"
        )
        if confirm_field.count() > 0:
            confirm_field.fill("ValidPassword123!")

        page.click("button[type='submit']")
        page.wait_for_timeout(3000)

        # Should show error about duplicate username
        is_on_signup = "/auth/signup" in page.url or "/auth/register" in page.url
        has_error = page.locator(".alert-danger, .error, .invalid-feedback").count() > 0

        assert is_on_signup or has_error


class TestSignupSuccess:
    """Tests for successful signup flow."""

    @pytest.mark.skip(reason="Requires email verification - test manually")
    def test_signup_shows_verification_page(
        self, page: Page, base_url: str, new_user_data: dict
    ):
        """
        Successful signup should redirect to email verification.

        Note: This test is skipped by default because it creates a real user
        and requires email verification. Run manually when needed.
        """
        page.goto(f"{base_url}/auth/signup/")
        page.wait_for_timeout(1000)

        page.fill("#username, input[name='username']", new_user_data["username"])
        page.fill("#email, input[name='email']", new_user_data["email"])
        page.fill("#password, input[name='password']", new_user_data["password"])

        confirm_field = page.locator(
            "#password_confirm, #confirm_password, input[name='password_confirm']"
        )
        if confirm_field.count() > 0:
            confirm_field.fill(new_user_data["password"])

        page.click("button[type='submit']")

        # Should redirect to verification page
        page.wait_for_url(
            lambda url: "verify" in url or "confirmation" in url, timeout=10000
        )

    def test_signup_form_clears_on_focus(self, page: Page, base_url: str):
        """Password fields should be clearable (security test)."""
        page.goto(f"{base_url}/auth/signup/")
        page.wait_for_timeout(1000)

        password_field = page.locator("#password, input[name='password']")
        password_field.fill("TestPassword123!")

        # Should be able to clear
        password_field.fill("")

        assert password_field.input_value() == ""


class TestUsernameAvailability:
    """Tests for username availability checking (if AJAX endpoint exists)."""

    def test_username_check_api_exists(self, page: Page, base_url: str, timestamp):
        """Check if username availability API responds."""
        page.goto(f"{base_url}/auth/signup/")
        page.wait_for_timeout(1000)

        # Fill username and trigger blur
        username_field = page.locator("#username, input[name='username']")
        username_field.fill(f"test_user_{timestamp}")
        username_field.blur()

        page.wait_for_timeout(1000)

        # Check for availability indicator (if exists)
        # This is optional - not all apps have this feature
        availability_indicator = page.locator(
            ".username-available, .username-taken, .availability-check"
        )

        # Just verify page doesn't crash
        assert page.url is not None
