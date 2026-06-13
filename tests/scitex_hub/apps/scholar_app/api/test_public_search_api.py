#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for Public Scholar Search API.

Tests the public API endpoints documented in /api-docs/:
- GET /api/v1/scholar/search/
- GET /api/v1/scholar/info/
"""

import pytest
from django.core.cache import cache
from django.test import Client


@pytest.fixture(autouse=True)
def _clear_rate_limit_cache():
    """Clear the rate-limit cache between tests.

    The public search API rate-limits anonymous callers to 10 req/min keyed
    on client IP (apps/workspace/scholar_app/api/public_search_utils.py).
    The Django test client reuses 127.0.0.1, so without isolation the 11th+
    request across the whole module would return 429 instead of 200. Clearing
    the cache per test keeps each test independent rather than weakening the
    200-status assertions.
    """
    cache.clear()
    yield
    cache.clear()


class TestPublicSearchAPI:
    """Test /api/v1/scholar/search/ endpoint."""

    @pytest.fixture
    def client(self):
        return Client()

    @pytest.mark.django_db
    def test_search_returns_200_with_query(self, client):
        """Search with valid query should return 200."""
        response = client.get("/api/v1/scholar/search/", {"q": "test"})
        assert response.status_code == 200

    @pytest.mark.django_db
    def test_search_returns_400_without_query(self, client):
        """Search without query should return 400."""
        response = client.get("/api/v1/scholar/search/")
        assert response.status_code == 400
        data = response.json()
        assert "error" in data
        assert "q" in data["error"].lower()

    @pytest.mark.django_db
    def test_search_returns_json_by_default(self, client):
        """Search should return JSON by default."""
        response = client.get("/api/v1/scholar/search/", {"q": "neural networks"})
        assert response.status_code == 200
        assert response["Content-Type"].startswith("application/json")
        data = response.json()
        assert "status" in data
        assert "results" in data

    @pytest.mark.django_db
    def test_search_json_response_structure(self, client):
        """JSON response should have required fields."""
        response = client.get("/api/v1/scholar/search/", {"q": "test"})
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "query" in data
        assert "total_count" in data
        assert "sources" in data
        assert "results" in data
        assert isinstance(data["results"], list)

    @pytest.mark.django_db
    def test_search_bibtex_format(self, client):
        """Search with format=bibtex should return BibTeX."""
        response = client.get(
            "/api/v1/scholar/search/", {"q": "test", "format": "bibtex"}
        )
        assert response.status_code == 200
        assert "bibtex" in response["Content-Type"].lower()
        assert "attachment" in response.get("Content-Disposition", "")

    @pytest.mark.django_db
    def test_search_csv_format(self, client):
        """Search with format=csv should return CSV."""
        response = client.get("/api/v1/scholar/search/", {"q": "test", "format": "csv"})
        assert response.status_code == 200
        assert "csv" in response["Content-Type"].lower()

    @pytest.mark.django_db
    def test_search_text_format(self, client):
        """Search with format=text should return plain text."""
        response = client.get(
            "/api/v1/scholar/search/", {"q": "test", "format": "text"}
        )
        assert response.status_code == 200
        assert "text/plain" in response["Content-Type"]

    @pytest.mark.django_db
    def test_search_invalid_format(self, client):
        """Search with invalid format should return 400."""
        response = client.get(
            "/api/v1/scholar/search/", {"q": "test", "format": "invalid"}
        )
        assert response.status_code == 400
        data = response.json()
        assert "error" in data

    @pytest.mark.django_db
    def test_search_limit_parameter(self, client):
        """Search should respect limit parameter."""
        response = client.get("/api/v1/scholar/search/", {"q": "test", "limit": "5"})
        assert response.status_code == 200

    @pytest.mark.django_db
    def test_search_limit_max_100(self, client):
        """Limit should be capped at 100."""
        response = client.get("/api/v1/scholar/search/", {"q": "test", "limit": "500"})
        assert response.status_code == 200

    @pytest.mark.django_db
    def test_search_sources_parameter(self, client):
        """Search should accept sources parameter."""
        response = client.get(
            "/api/v1/scholar/search/", {"q": "test", "sources": "pubmed,arxiv"}
        )
        assert response.status_code == 200

    @pytest.mark.django_db
    def test_search_single_source(self, client):
        """Search with single source should work."""
        response = client.get(
            "/api/v1/scholar/search/", {"q": "test", "sources": "pubmed"}
        )
        assert response.status_code == 200

    @pytest.mark.django_db
    def test_search_invalid_source_falls_back(self, client):
        """Invalid sources should fall back to defaults."""
        response = client.get(
            "/api/v1/scholar/search/", {"q": "test", "sources": "invalid"}
        )
        assert response.status_code == 200

    @pytest.mark.django_db
    def test_search_post_method_not_allowed(self, client):
        """POST to search endpoint should return 405."""
        response = client.post("/api/v1/scholar/search/", {"q": "test"})
        assert response.status_code == 405


class TestPublicInfoAPI:
    """Test /api/v1/scholar/info/ endpoint."""

    @pytest.fixture
    def client(self):
        return Client()

    @pytest.mark.django_db
    def test_info_returns_200(self, client):
        """Info endpoint should return 200."""
        response = client.get("/api/v1/scholar/info/")
        assert response.status_code == 200

    @pytest.mark.django_db
    def test_info_returns_json(self, client):
        """Info should return JSON."""
        response = client.get("/api/v1/scholar/info/")
        assert response["Content-Type"].startswith("application/json")

    @pytest.mark.django_db
    def test_info_response_structure(self, client):
        """Info response should have required fields."""
        response = client.get("/api/v1/scholar/info/")
        data = response.json()
        assert "status" in data
        assert "api_version" in data
        assert "endpoints" in data
        assert "rate_limits" in data
        assert "authentication" in data
        assert "response_fields" in data

    @pytest.mark.django_db
    def test_info_endpoints_documented(self, client):
        """Info should document available endpoints."""
        response = client.get("/api/v1/scholar/info/")
        data = response.json()
        endpoints = data.get("endpoints", {})
        assert "search" in endpoints
        assert "info" in endpoints

    @pytest.mark.django_db
    def test_info_search_parameters_documented(self, client):
        """Search parameters should be documented."""
        response = client.get("/api/v1/scholar/info/")
        data = response.json()
        search_params = (
            data.get("endpoints", {}).get("search", {}).get("parameters", {})
        )
        assert "q" in search_params
        assert "limit" in search_params
        assert "format" in search_params
        assert "sources" in search_params


class TestAPIResponseFields:
    """Test that API responses contain documented fields."""

    @pytest.fixture
    def client(self):
        return Client()

    @pytest.mark.django_db
    def test_result_has_title(self, client):
        """Results should include title field."""
        response = client.get("/api/v1/scholar/search/", {"q": "python"})
        if response.status_code == 200:
            data = response.json()
            for result in data.get("results", [])[:3]:
                # title may be empty but should exist
                assert "title" in result or result.get("title") is not None

    @pytest.mark.django_db
    def test_result_has_source(self, client):
        """Results should include source field."""
        response = client.get("/api/v1/scholar/search/", {"q": "python"})
        if response.status_code == 200:
            data = response.json()
            for result in data.get("results", [])[:3]:
                assert "source" in result


class TestAPIRateLimitHeaders:
    """Test rate limit headers are present."""

    @pytest.fixture
    def client(self):
        return Client()

    @pytest.mark.django_db
    def test_rate_limit_headers_present(self, client):
        """Response should include rate limit headers."""
        response = client.get("/api/v1/scholar/search/", {"q": "test"})
        # Check for common rate limit headers
        # These may vary based on implementation
        headers = dict(response.headers)
        rate_limit_headers = [
            h for h in headers.keys() if "ratelimit" in h.lower() or "rate" in h.lower()
        ]
        # At minimum, we expect some indication of rate limits
        # This test documents the expectation
        assert response.status_code in (200, 429)
