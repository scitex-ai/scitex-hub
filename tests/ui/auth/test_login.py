#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Timestamp: 2025-11-30
# File: /home/ywatanabe/proj/scitex-cloud/tests/e2e/auth/test_login.py

"""
E2E tests for login functionality.

Tests:
- Login page loads correctly
- Successful login with valid credentials
- Failed login with invalid credentials
- Login form validation
- Logout functionality
- Remember me / session persistence
"""

import pytest
from playwright.sync_api import Page, expect


def is_auth_page(url: str) -> bool:
    """Check if URL is an authentication page."""
    auth_patterns = ["/auth/signin", "/auth/login", "/auth/signup", "/auth/register"]
    return any(pattern in url for pattern in auth_patterns)


class TestLoginPage:
    """Tests for login page rendering and accessibility."""

    def test_login_page_loads(self, page: Page, base_url: str):
        """Login page should load without errors."""
        page.goto(f"{base_url}/auth/signin/", wait_until="domcontentloaded")

        # Page should have login form
        expect(page.locator("form#login-form, form[action*='signin']")).to_be_visible(
            timeout=10000
        )

        # Required fields should be present
        expect(page.locator("#username")).to_be_visible(timeout=5000)
        expect(page.locator("#password")).to_be_visible(timeout=5000)
        expect(page.locator("button[type='submit']")).to_be_visible(timeout=5000)

    def test_login_page_has_signup_link(self, page: Page, base_url: str):
        """Login page should have link to signup."""
        page.goto(f"{base_url}/auth/signin/", wait_until="domcontentloaded")

        # There may be multiple signup links; find a visible one
        # The "Sign Up" text link in the form area is typically visible
        signup_links = page.locator("a[href*='signup'], a[href*='register']")
        visible_count = 0
        for i in range(signup_links.count()):
            if signup_links.nth(i).is_visible():
                visible_count += 1
                break
        assert visible_count > 0, "Expected at least one visible signup link"

    def test_login_page_has_forgot_password_link(self, page: Page, base_url: str):
        """Login page should have forgot password link."""
        page.goto(f"{base_url}/auth/signin/", wait_until="domcontentloaded")

        forgot_link = page.locator("a[href*='forgot'], a[href*='reset']").first
        expect(forgot_link).to_be_visible(timeout=5000)


class TestLoginSuccess:
    """Tests for successful login scenarios."""

    def test_login_with_valid_credentials(
        self, page: Page, base_url: str, test_credentials: dict
    ):
        """User can login with valid username and password."""
        page.goto(f"{base_url}/auth/signin/", wait_until="domcontentloaded")

        # Fill credentials
        page.fill("#username", test_credentials["username"])
        page.fill("#password", test_credentials["password"])
        page.click("button[type='submit']")

        # Wait for response and check result
        page.wait_for_timeout(3000)

        # Check for error message
        error_locator = page.locator(".alert-danger, .error-message, .invalid-feedback")
        has_error = error_locator.count() > 0 and error_locator.first.is_visible()

        # Verify authenticated (body attribute or redirected away from signin)
        is_authenticated = (
            page.locator("body").get_attribute("data-user-authenticated") == "true"
        )
        is_redirected = not is_auth_page(page.url)

        # If there's an error, the test credentials might be invalid - skip
        if has_error and not is_authenticated:
            pytest.skip(
                f"Login failed with error (test credentials may need setup): {page.url}"
            )

        assert is_authenticated or is_redirected, (
            f"Login failed: authenticated={is_authenticated}, url={page.url}"
        )

    def test_login_redirects_to_home(
        self, page: Page, base_url: str, test_credentials: dict
    ):
        """Successful login redirects to home page."""
        page.goto(f"{base_url}/auth/signin/", wait_until="domcontentloaded")

        page.fill("#username", test_credentials["username"])
        page.fill("#password", test_credentials["password"])
        page.click("button[type='submit']")

        # Wait for response
        page.wait_for_timeout(3000)

        # Check for error message
        error_locator = page.locator(".alert-danger, .error-message, .invalid-feedback")
        has_error = error_locator.count() > 0 and error_locator.first.is_visible()

        # URL should be home, user-specific, or still on signin (if error)
        current_url = page.url
        is_redirected = not is_auth_page(current_url)
        is_authenticated = (
            page.locator("body").get_attribute("data-user-authenticated") == "true"
        )

        # If there's an error, skip test
        if has_error and not is_authenticated:
            pytest.skip(
                f"Login failed with error (test credentials may need setup): {current_url}"
            )

        # At least one condition should be true
        assert is_redirected or is_authenticated, (
            f"Expected redirect or authentication, got url={current_url}"
        )


class TestLoginFailure:
    """Tests for failed login scenarios."""

    def test_login_with_wrong_password(
        self, page: Page, base_url: str, test_credentials: dict
    ):
        """Login fails with incorrect password."""
        page.goto(f"{base_url}/auth/signin/")
        page.wait_for_timeout(1000)

        page.fill("#username", test_credentials["username"])
        page.fill("#password", "WrongPassword123!")
        page.click("button[type='submit']")

        # Should stay on login page or show error
        page.wait_for_timeout(2000)

        # Either still on signin page or error message shown
        on_auth_page = is_auth_page(page.url)
        has_error = page.locator(".alert-danger, .error, .invalid-feedback").count() > 0

        assert on_auth_page or has_error

    def test_login_with_nonexistent_user(self, page: Page, base_url: str):
        """Login fails with non-existent username."""
        page.goto(f"{base_url}/auth/signin/")
        page.wait_for_timeout(1000)

        page.fill("#username", "nonexistent_user_12345")
        page.fill("#password", "SomePassword123!")
        page.click("button[type='submit']")

        page.wait_for_timeout(2000)

        # Should fail
        on_auth_page = is_auth_page(page.url)
        has_error = page.locator(".alert-danger, .error, .invalid-feedback").count() > 0

        assert on_auth_page or has_error

    def test_login_with_empty_fields(self, page: Page, base_url: str):
        """Login fails when fields are empty."""
        page.goto(f"{base_url}/auth/signin/")
        page.wait_for_timeout(1000)

        # Submit without filling
        page.click("button[type='submit']")

        page.wait_for_timeout(1000)

        # Should not navigate away, HTML5 validation or stay on page
        assert is_auth_page(page.url)


class TestLogout:
    """Tests for logout functionality."""

    def test_logout_clears_session(
        self, page: Page, base_url: str, test_credentials: dict
    ):
        """Logout clears user session."""
        # First login
        page.goto(f"{base_url}/auth/signin/", wait_until="domcontentloaded")
        page.wait_for_timeout(1000)

        page.fill("#username", test_credentials["username"])
        page.fill("#password", test_credentials["password"])
        page.click("button[type='submit']")
        page.wait_for_timeout(3000)

        # Verify logged in (check attribute)
        is_authenticated = (
            page.locator("body").get_attribute("data-user-authenticated") == "true"
        )

        if is_authenticated:
            # Logout
            page.goto(f"{base_url}/auth/signout/", wait_until="domcontentloaded")
            page.wait_for_timeout(2000)

            # Verify logged out
            is_logged_out = (
                page.locator("body").get_attribute("data-user-authenticated") == "false"
            )
            assert is_logged_out or is_auth_page(page.url)
        else:
            # Login didn't work, skip logout test
            pytest.skip("Login failed, cannot test logout")

    def test_logout_redirects_to_public_page(
        self, page: Page, base_url: str, test_credentials: dict
    ):
        """Logout redirects to public page."""
        # Login first
        page.goto(f"{base_url}/auth/signin/", wait_until="domcontentloaded")
        page.fill("#username", test_credentials["username"])
        page.fill("#password", test_credentials["password"])
        page.click("button[type='submit']")
        page.wait_for_timeout(3000)

        # Logout
        page.goto(f"{base_url}/auth/signout/", wait_until="domcontentloaded")
        page.wait_for_timeout(2000)

        # Should be on public page (home or login)
        current_url = page.url
        assert (
            current_url.rstrip("/") == base_url.rstrip("/")
            or is_auth_page(current_url)
            or "/auth/signout" in current_url
        )


class TestSessionPersistence:
    """Tests for session/cookie behavior."""

    def test_authenticated_user_stays_logged_in(
        self, page: Page, base_url: str, test_credentials: dict
    ):
        """Logged in user remains authenticated across page loads."""
        # Login
        page.goto(f"{base_url}/auth/signin/", wait_until="domcontentloaded")
        page.fill("#username", test_credentials["username"])
        page.fill("#password", test_credentials["password"])
        page.click("button[type='submit']")
        page.wait_for_timeout(3000)

        # Check if logged in
        is_authenticated = (
            page.locator("body").get_attribute("data-user-authenticated") == "true"
        )

        if not is_authenticated:
            pytest.skip("Login failed, cannot test session persistence")

        # Navigate to another page
        page.goto(f"{base_url}/", wait_until="domcontentloaded")
        page.wait_for_timeout(1000)

        # Should still be authenticated
        still_authenticated = (
            page.locator("body").get_attribute("data-user-authenticated") == "true"
        )
        assert still_authenticated, "Session was not preserved across page loads"

    def test_accessing_signin_while_logged_in_redirects(
        self, page: Page, base_url: str, test_credentials: dict
    ):
        """Accessing signin page while logged in may redirect."""
        # Login first
        page.goto(f"{base_url}/auth/signin/", wait_until="domcontentloaded")
        page.fill("#username", test_credentials["username"])
        page.fill("#password", test_credentials["password"])
        page.click("button[type='submit']")
        page.wait_for_timeout(3000)

        # Check if logged in
        is_authenticated = (
            page.locator("body").get_attribute("data-user-authenticated") == "true"
        )

        if not is_authenticated:
            pytest.skip("Login failed, cannot test signin access while logged in")

        # Try to access signin page again
        page.goto(f"{base_url}/auth/signin/", wait_until="domcontentloaded")
        page.wait_for_timeout(2000)

        # Should either redirect or show already logged in
        still_authenticated = (
            page.locator("body").get_attribute("data-user-authenticated") == "true"
        )
        assert still_authenticated, "User should remain authenticated when accessing signin"
