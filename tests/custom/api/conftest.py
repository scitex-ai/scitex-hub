#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Timestamp: 2025-11-30
# File: /home/ywatanabe/proj/scitex-hub/tests/api/conftest.py

"""
API test fixtures using requests library.

Provides:
- HTTP client with session management
- Authentication helpers
- JSON response utilities
"""

import pytest

# Skip the whole ``tests/custom/api/`` tree when ``requests`` isn't installed
# (PA-303) — collection-safety on minimal envs.
requests = pytest.importorskip(
    "requests",
    reason="requests not installed — api/ tests skipped",
)

# Import from parent conftest
from tests.conftest import (
    BASE_URL,
    TEST_USER_PASSWORD,
    TEST_USER_USERNAME,
)  # noqa: E402


def _is_server_reachable(url: str, timeout: float = 1.5) -> bool:
    try:
        requests.head(url, timeout=timeout, allow_redirects=False)
        return True
    except (requests.ConnectionError, requests.Timeout):
        return False


# Skip the whole `tests/custom/api/` tree when no Django dev server is running at
# BASE_URL. These are integration tests against a live HTTP surface, not
# unit tests; CI can't run them without spinning up the server.
collect_ignore_marker = "scitex-hub-api-server-unreachable"


def pytest_collection_modifyitems(config, items):  # noqa: D401
    if _is_server_reachable(BASE_URL):
        return
    skip_no_server = pytest.mark.skip(
        reason=f"requires running Django server at {BASE_URL} (set SCITEX_BASE_URL or start `manage.py runserver`)"
    )
    for item in items:
        if "/tests/custom/api/" in str(item.fspath):
            item.add_marker(skip_no_server)


@pytest.fixture(scope="session")
def api_base_url():
    """Base URL for API endpoints."""
    return BASE_URL


@pytest.fixture(scope="function")
def client():
    """Create a new requests session for each test."""
    session = requests.Session()
    session.headers.update(
        {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
    )
    yield session
    session.close()


@pytest.fixture(scope="function")
def authenticated_client(client, api_base_url):
    """
    Client with authenticated session (logged in as test-user).

    Gets CSRF token and session cookie via login.
    """
    # Get CSRF token from login page
    login_page = client.get(f"{api_base_url}/auth/signin/")

    # Extract CSRF token from cookies or page
    csrf_token = client.cookies.get("csrftoken", "")

    if csrf_token:
        client.headers.update({"X-CSRFToken": csrf_token})

    # Login
    login_data = {
        "username": TEST_USER_USERNAME,
        "password": TEST_USER_PASSWORD,
    }

    response = client.post(
        f"{api_base_url}/auth/login/",
        data=login_data,
        headers={"Referer": f"{api_base_url}/auth/signin/"},
        allow_redirects=False,
    )

    # Update CSRF token after login if changed
    if "csrftoken" in client.cookies:
        client.headers.update({"X-CSRFToken": client.cookies["csrftoken"]})

    return client


@pytest.fixture
def csrf_token(client, api_base_url):
    """Get CSRF token for form submissions."""
    client.get(f"{api_base_url}/")
    return client.cookies.get("csrftoken", "")


# =============================================================================
# Response Helpers
# =============================================================================


def assert_json_response(response, status_code=200):
    """Assert response is valid JSON with expected status."""
    assert (
        response.status_code == status_code
    ), f"Expected {status_code}, got {response.status_code}: {response.text[:200]}"
    try:
        return response.json()
    except ValueError:
        pytest.fail(f"Response is not valid JSON: {response.text[:200]}")


def assert_error_response(response, status_code=400):
    """Assert response is an error with expected status."""
    assert (
        response.status_code == status_code
    ), f"Expected error {status_code}, got {response.status_code}"
    return response


def assert_redirect(response, expected_path=None):
    """Assert response is a redirect."""
    assert response.status_code in (
        301,
        302,
        303,
        307,
        308,
    ), f"Expected redirect, got {response.status_code}"
    if expected_path:
        location = response.headers.get("Location", "")
        assert (
            expected_path in location
        ), f"Expected redirect to '{expected_path}', got '{location}'"
    return response
