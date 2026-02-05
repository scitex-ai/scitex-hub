#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Timestamp: 2026-02-05
# File: /home/ywatanabe/proj/scitex-cloud/tests/api/scholar/test_public_api.py

"""
Tests for the Public Scholar API (v1).

Tests the documented API endpoints:
- /api/v1/scholar/info/
- /api/v1/scholar/search/
- /api/token/ (JWT authentication)

Run with: pytest tests/api/scholar/test_public_api.py -v
"""

import pytest

from tests.api.conftest import assert_json_response
from tests.conftest import TEST_USER_PASSWORD, TEST_USER_USERNAME


@pytest.fixture(scope="module")
def scitex_api_key():
    """Create or get a SciTeX API key for testing (bypasses rate limits)."""
    try:
        from django.contrib.auth import get_user_model

        from apps.accounts_app.models import APIKey

        User = get_user_model()
        user = User.objects.filter(username=TEST_USER_USERNAME).first()
        if not user:
            return None

        # Check for existing test API key
        existing_key = APIKey.objects.filter(user=user, name="pytest-test-key").first()
        if existing_key:
            # We can't retrieve the full key, so delete and recreate
            existing_key.delete()

        # Create new API key
        api_key, full_key = APIKey.create_key(
            user=user,
            name="pytest-test-key",
            scopes=["scholar:read"],
        )
        return full_key
    except Exception as e:
        print(f"Could not create API key: {e}")
        return None


@pytest.fixture
def auth_client(client, scitex_api_key):
    """Client with API key for higher rate limits (100 req/min)."""
    if scitex_api_key:
        client.headers.update({"X-SCITEX-API-KEY": scitex_api_key})
    return client


class TestScholarInfoAPI:
    """Tests for /api/v1/scholar/info/ endpoint."""

    def test_info_returns_200(self, client, api_base_url):
        """Info endpoint should return 200 OK."""
        response = client.get(f"{api_base_url}/api/v1/scholar/info/")
        assert response.status_code == 200

    def test_info_returns_json(self, client, api_base_url):
        """Info endpoint should return valid JSON."""
        response = client.get(f"{api_base_url}/api/v1/scholar/info/")
        data = assert_json_response(response, 200)
        assert "status" in data
        assert data["status"] == "ok"

    def test_info_contains_api_version(self, client, api_base_url):
        """Info endpoint should include API version."""
        response = client.get(f"{api_base_url}/api/v1/scholar/info/")
        data = response.json()
        assert "api_version" in data
        assert data["api_version"] == "v1"

    def test_info_contains_endpoints(self, client, api_base_url):
        """Info endpoint should document available endpoints."""
        response = client.get(f"{api_base_url}/api/v1/scholar/info/")
        data = response.json()
        assert "endpoints" in data
        assert "search" in data["endpoints"]
        assert "info" in data["endpoints"]

    def test_info_contains_rate_limits(self, client, api_base_url):
        """Info endpoint should document rate limits."""
        response = client.get(f"{api_base_url}/api/v1/scholar/info/")
        data = response.json()
        assert "rate_limits" in data


class TestScholarSearchAPI:
    """Tests for /api/v1/scholar/search/ endpoint (using auth to avoid rate limits)."""

    def test_search_requires_query(self, auth_client, api_base_url):
        """Search endpoint should require 'q' parameter."""
        response = auth_client.get(f"{api_base_url}/api/v1/scholar/search/")
        assert response.status_code == 400
        data = response.json()
        assert "error" in data or "detail" in data

    def test_search_returns_json_by_default(self, auth_client, api_base_url):
        """Search should return JSON by default."""
        response = auth_client.get(
            f"{api_base_url}/api/v1/scholar/search/",
            params={"q": "machine learning", "limit": 2},
        )
        assert response.status_code == 200
        data = response.json()
        assert "results" in data or "papers" in data or isinstance(data, list)

    def test_search_returns_bibtex(self, auth_client, api_base_url):
        """Search should return BibTeX when format=bibtex."""
        response = auth_client.get(
            f"{api_base_url}/api/v1/scholar/search/",
            params={"q": "neural networks", "format": "bibtex", "limit": 1},
        )
        assert response.status_code == 200
        content = response.text
        # BibTeX format check
        assert "@" in content, "BibTeX should contain @ entries"
        assert "title" in content.lower(), "BibTeX should contain title field"

    def test_search_returns_csv(self, auth_client, api_base_url):
        """Search should return CSV when format=csv."""
        response = auth_client.get(
            f"{api_base_url}/api/v1/scholar/search/",
            params={"q": "deep learning", "format": "csv", "limit": 2},
        )
        assert response.status_code == 200
        content = response.text
        # CSV format check - should have header row
        assert "title" in content.lower() or "," in content

    def test_search_returns_text(self, auth_client, api_base_url):
        """Search should return plain text when format=text."""
        response = auth_client.get(
            f"{api_base_url}/api/v1/scholar/search/",
            params={"q": "cancer research", "format": "text", "limit": 1},
        )
        assert response.status_code == 200
        # Should be readable text, not JSON
        content = response.text
        assert len(content) > 0

    def test_search_respects_limit(self, auth_client, api_base_url):
        """Search should respect the limit parameter (per source)."""
        response = auth_client.get(
            f"{api_base_url}/api/v1/scholar/search/",
            params={"q": "python programming", "limit": 3, "sources": "arxiv"},
        )
        assert response.status_code == 200
        data = response.json()
        results = data.get("results", data.get("papers", data))
        if isinstance(results, list):
            # Limit is per-source, so with single source should be <= limit
            assert len(results) <= 3

    def test_search_with_sources(self, auth_client, api_base_url):
        """Search should filter by sources when specified."""
        response = auth_client.get(
            f"{api_base_url}/api/v1/scholar/search/",
            params={"q": "genetics", "sources": "pubmed", "limit": 2},
        )
        assert response.status_code == 200

    def test_search_invalid_format(self, auth_client, api_base_url):
        """Search should handle invalid format gracefully."""
        response = auth_client.get(
            f"{api_base_url}/api/v1/scholar/search/",
            params={"q": "test", "format": "invalid_format"},
        )
        # Should either return 400 or default to JSON
        assert response.status_code in (200, 400)


class TestJWTAuthentication:
    """Tests for /api/token/ JWT endpoint."""

    def test_token_endpoint_exists(self, client, api_base_url):
        """Token endpoint should exist."""
        response = client.post(f"{api_base_url}/api/token/")
        # Should not be 404 (endpoint exists but may need credentials)
        assert response.status_code != 404

    def test_token_requires_credentials(self, client, api_base_url):
        """Token endpoint should require username and password."""
        response = client.post(f"{api_base_url}/api/token/", json={})
        assert response.status_code in (400, 401)

    def test_token_invalid_credentials(self, client, api_base_url):
        """Token endpoint should reject invalid credentials."""
        response = client.post(
            f"{api_base_url}/api/token/",
            json={"username": "nonexistent", "password": "wrongpassword"},
        )
        assert response.status_code == 401

    def test_token_valid_credentials(self, client, api_base_url):
        """Token endpoint should return JWT for valid credentials."""
        response = client.post(
            f"{api_base_url}/api/token/",
            json={
                "username": TEST_USER_USERNAME,
                "password": TEST_USER_PASSWORD,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "access" in data, "Response should contain access token"
        assert "refresh" in data, "Response should contain refresh token"

    def test_token_refresh(self, client, api_base_url):
        """Token refresh endpoint should work."""
        # First get tokens
        response = client.post(
            f"{api_base_url}/api/token/",
            json={
                "username": TEST_USER_USERNAME,
                "password": TEST_USER_PASSWORD,
            },
        )
        assert response.status_code == 200
        tokens = response.json()

        # Then refresh
        response = client.post(
            f"{api_base_url}/api/token/refresh/",
            json={"refresh": tokens["refresh"]},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access" in data


class TestAPIDocumentation:
    """Tests to verify API documentation examples work."""

    def test_documented_search_example_1(self, auth_client, api_base_url):
        """Test: /api/v1/scholar/search/?q=neural+networks"""
        response = auth_client.get(
            f"{api_base_url}/api/v1/scholar/search/",
            params={"q": "neural networks"},
        )
        assert response.status_code == 200

    def test_documented_search_example_2(self, auth_client, api_base_url):
        """Test: /api/v1/scholar/search/?q=cancer&format=bibtex&limit=50"""
        response = auth_client.get(
            f"{api_base_url}/api/v1/scholar/search/",
            params={"q": "cancer", "format": "bibtex", "limit": 50},
        )
        assert response.status_code == 200
        assert "@" in response.text  # BibTeX format

    def test_documented_search_example_3(self, auth_client, api_base_url):
        """Test: /api/v1/scholar/search/?q=covid&sources=pubmed,crossref&format=csv"""
        response = auth_client.get(
            f"{api_base_url}/api/v1/scholar/search/",
            params={"q": "covid", "sources": "pubmed,crossref", "format": "csv"},
        )
        assert response.status_code == 200


class TestHealthEndpoints:
    """Tests for health check endpoints."""

    def test_healthz_endpoint(self, client, api_base_url):
        """/healthz/ should return healthy status."""
        response = client.get(f"{api_base_url}/healthz/")
        assert response.status_code == 200


# EOF
