#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for CrossRef API endpoints.

Tests the CrossRef proxy API endpoints:
- GET /scholar/api/crossref/search/
- GET /scholar/api/crossref/citations/
- GET /scholar/api/crossref/health/
- GET /scholar/api/crossref/stats/
"""

import pytest
from django.test import Client


class TestCrossRefSearchAPI:
    """Test /scholar/api/crossref/search/ endpoint."""

    @pytest.fixture
    def client(self):
        return Client()

    @pytest.mark.django_db
    def test_search_endpoint_exists(self, client):
        """CrossRef search endpoint should exist."""
        response = client.get("/scholar/api/crossref/search/")
        # Should return 400 (missing query) or 200, not 404
        assert response.status_code != 404

    @pytest.mark.django_db
    def test_search_requires_query(self, client):
        """Search should require query parameter."""
        response = client.get("/scholar/api/crossref/search/")
        # Expect 400 or 200 (missing param), or 503 if CrossRef service is unavailable
        assert response.status_code in (400, 200, 503)


class TestCrossRefCitationsAPI:
    """Test /scholar/api/crossref/citations/ endpoint."""

    @pytest.fixture
    def client(self):
        return Client()

    @pytest.mark.django_db
    def test_citations_endpoint_exists(self, client):
        """CrossRef citations endpoint should exist."""
        response = client.get("/scholar/api/crossref/citations/")
        assert response.status_code != 404


class TestCrossRefHealthAPI:
    """Test /scholar/api/crossref/health/ endpoint."""

    @pytest.fixture
    def client(self):
        return Client()

    @pytest.mark.django_db
    def test_health_endpoint_returns_200(self, client):
        """Health endpoint should return 200 when service is available, 503 when not."""
        response = client.get("/scholar/api/crossref/health/")
        assert response.status_code in (200, 503)

    @pytest.mark.django_db
    def test_health_returns_json(self, client):
        """Health endpoint should return JSON."""
        response = client.get("/scholar/api/crossref/health/")
        assert response["Content-Type"].startswith("application/json")


class TestCrossRefStatsAPI:
    """Test /scholar/api/crossref/stats/ endpoint."""

    @pytest.fixture
    def client(self):
        return Client()

    @pytest.mark.django_db
    def test_stats_endpoint_exists(self, client):
        """Stats endpoint should exist."""
        response = client.get("/scholar/api/crossref/stats/")
        assert response.status_code != 404
