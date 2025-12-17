#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UI test configuration - Browser-based Playwright tests.

Provides fixtures for:
- Browser page management
- User authentication
- Visual feedback (scitex.browser)
- Screenshot/artifact capture
"""

import os
import sys
from pathlib import Path

import pytest

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent.parent
ARTIFACTS_DIR = Path(__file__).parent / "artifacts"
ARTIFACTS_DIR.mkdir(exist_ok=True)

# Environment configuration
TEST_USER_USERNAME = os.getenv("SCITEX_CLOUD_TEST_USER_USERNAME", "test-user")
TEST_USER_PASSWORD = os.getenv("SCITEX_CLOUD_TEST_USER_PASSWORD", "Password123!")
BASE_URL = os.getenv("SCITEX_BASE_URL", "http://127.0.0.1:8000")


@pytest.fixture(scope="session")
def base_url():
    """Base URL for the application."""
    return BASE_URL


@pytest.fixture(scope="session")
def test_credentials():
    """Test user credentials."""
    return {
        "username": TEST_USER_USERNAME,
        "password": TEST_USER_PASSWORD,
    }


@pytest.fixture
def artifacts_dir():
    """Directory for test artifacts (screenshots, videos)."""
    return ARTIFACTS_DIR


def login_user(page, base_url: str, credentials: dict) -> None:
    """Helper function to log in a user."""
    page.goto(f"{base_url}/auth/login/")
    page.fill('input[name="username"]', credentials["username"])
    page.fill('input[name="password"]', credentials["password"])
    page.click('button[type="submit"]')
    page.wait_for_load_state("networkidle")


@pytest.fixture
def logged_in_page(page, base_url, test_credentials):
    """Playwright page with user already logged in."""
    login_user(page, base_url, test_credentials)
    return page


@pytest.fixture
def visual_page(page):
    """Page with visual effects enabled (if scitex.browser available)."""
    try:
        from scitex.browser import inject_visual_effects

        inject_visual_effects(page)
    except ImportError:
        pass  # Visual effects disabled
    return page


@pytest.fixture
def logged_in_visual_page(logged_in_page):
    """Logged-in page with visual effects."""
    try:
        from scitex.browser import inject_visual_effects

        inject_visual_effects(logged_in_page)
    except ImportError:
        pass
    return logged_in_page


@pytest.fixture(autouse=True)
def capture_on_failure(request, page, artifacts_dir):
    """Capture screenshot on test failure."""
    yield
    if request.node.rep_call.failed if hasattr(request.node, "rep_call") else False:
        screenshot_path = artifacts_dir / f"{request.node.name}_failure.png"
        try:
            page.screenshot(path=str(screenshot_path))
            print(f"\nScreenshot saved: {screenshot_path}")
        except Exception:
            pass


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """Store test result for failure detection."""
    outcome = yield
    rep = outcome.get_result()
    setattr(item, f"rep_{rep.when}", rep)
