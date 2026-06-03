#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
E2E Test Configuration

Shared fixtures for E2E tests running against a live server.
"""

import os
from urllib.parse import urljoin

import pytest

# Skip the whole ``tests/e2e/`` tree when ``requests`` isn't installed
# (PA-303) — collection-safety on minimal envs.
requests = pytest.importorskip(
    "requests",
    reason="requests not installed — e2e/ tests skipped",
)

# =============================================================================
# Configuration
# =============================================================================

BASE_URL = os.getenv("SCITEX_BASE_URL", "http://127.0.0.1:8000")
TEST_USER = os.getenv("SCITEX_E2E_TEST_USER", "test-user")
TEST_PASS = os.getenv("SCITEX_E2E_TEST_PASS", "Password123!")
TIMEOUT = int(os.getenv("SCITEX_E2E_TIMEOUT", "30"))


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture(scope="session")
def base_url():
    """Base URL for the running server."""
    return BASE_URL.rstrip("/")


@pytest.fixture(scope="session")
def session():
    """Requests session with cookie persistence."""
    s = requests.Session()
    s.verify = False  # Allow self-signed certs in dev
    s.timeout = TIMEOUT
    yield s
    s.close()


@pytest.fixture(scope="session")
def test_credentials():
    """Test user credentials."""
    return {"username": TEST_USER, "password": TEST_PASS}


@pytest.fixture
def authenticated_session(session, base_url, test_credentials):
    """
    Session authenticated with test user.

    Note: Requires test user to exist in the database.
    Create with: python manage.py create_e2e_test_user
    """
    # Get CSRF token from login page
    login_url = urljoin(base_url, "/auth/login/")
    resp = session.get(login_url)

    if resp.status_code != 200:
        pytest.skip(f"Cannot access login page: {resp.status_code}")

    # Extract CSRF token
    csrf_token = session.cookies.get("csrftoken")
    if not csrf_token:
        # Try to extract from HTML
        import re

        match = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', resp.text)
        if match:
            csrf_token = match.group(1)

    if not csrf_token:
        pytest.skip("Cannot get CSRF token")

    # Login
    resp = session.post(
        login_url,
        data={
            "csrfmiddlewaretoken": csrf_token,
            "username": test_credentials["username"],
            "password": test_credentials["password"],
        },
        headers={"Referer": login_url},
        allow_redirects=False,
    )

    # Check login success (redirect to home or dashboard)
    if resp.status_code not in [200, 302]:
        pytest.skip(f"Login failed: {resp.status_code}")

    return session


@pytest.fixture
def api_client(session, base_url):
    """
    API client helper.
    """

    class APIClient:
        def __init__(self, session, base_url):
            self.session = session
            self.base_url = base_url

        def get(self, path, **kwargs):
            url = urljoin(self.base_url, path)
            return self.session.get(url, **kwargs)

        def post(self, path, **kwargs):
            url = urljoin(self.base_url, path)
            return self.session.post(url, **kwargs)

        def json_get(self, path, **kwargs):
            resp = self.get(path, **kwargs)
            return resp.json() if resp.status_code == 200 else None

    return APIClient(session, base_url)
