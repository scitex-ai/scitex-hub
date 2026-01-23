#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Timestamp: 2025-11-30
# File: /home/ywatanabe/proj/scitex-cloud/tests/api/conftest.py

"""
API test fixtures using requests library.

Provides:
- HTTP client with session management
- Authentication helpers
- JSON response utilities
"""

import os
import requests
import pytest

# Import from parent conftest
from tests.conftest import BASE_URL, TEST_USER_USERNAME, TEST_USER_PASSWORD


@pytest.fixture(scope="session")
def api_base_url():
    """Base URL for API endpoints."""
    return BASE_URL


@pytest.fixture(scope="function")
def client():
    """Create a new requests session for each test."""
    session = requests.Session()
    session.headers.update({
        "Content-Type": "application/json",
        "Accept": "application/json",
    })
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
    assert response.status_code == status_code, (
        f"Expected {status_code}, got {response.status_code}: {response.text[:200]}"
    )
    try:
        return response.json()
    except ValueError:
        pytest.fail(f"Response is not valid JSON: {response.text[:200]}")


def assert_error_response(response, status_code=400):
    """Assert response is an error with expected status."""
    assert response.status_code == status_code, (
        f"Expected error {status_code}, got {response.status_code}"
    )
    return response


def assert_redirect(response, expected_path=None):
    """Assert response is a redirect."""
    assert response.status_code in (301, 302, 303, 307, 308), (
        f"Expected redirect, got {response.status_code}"
    )
    if expected_path:
        location = response.headers.get("Location", "")
        assert expected_path in location, (
            f"Expected redirect to '{expected_path}', got '{location}'"
        )
    return response
