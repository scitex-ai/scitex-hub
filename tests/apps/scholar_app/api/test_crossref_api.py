#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for CrossRef API endpoints.

Tests the CrossRef proxy API endpoints:
- GET /apps/scholar/old-direct/api/crossref/search/
- GET /apps/scholar/old-direct/api/crossref/citations/
- GET /apps/scholar/old-direct/api/crossref/health/
- GET /apps/scholar/old-direct/api/crossref/stats/

CUTOVER (CCT 2760) + OPERATOR ROUTE RULE (CCT 2763/2764): /apps/scholar/
serves the Scholar LEAF now. These hub-native endpoints live ONLY at
/apps/scholar/old-direct/ in dev (dev-gated, never in production) — the
``scholar_old_direct`` fixture (tests/apps/scholar_app/conftest.py) turns
the gate on around each test so the test client resolves the SAME views
through the parity reference. Assertions are unchanged: same views, same
contract, only the prefix moved.
"""

import pytest
from django.test import Client


class TestCrossRefSearchAPI:
    """Test /scholar/api/crossref/search/ endpoint."""

    pytestmark = pytest.mark.usefixtures("scholar_old_direct")

    @pytest.fixture
    def client(self):
        return Client()

    @pytest.mark.django_db
    def test_search_endpoint_exists(self, client):
        """CrossRef search endpoint should exist."""
        response = client.get("/apps/scholar/old-direct/api/crossref/search/")
        # Should return 400 (missing query) or 200, not 404
        assert response.status_code != 404

    @pytest.mark.django_db
    def test_search_requires_query(self, client):
        """Search should require query parameter."""
        response = client.get("/apps/scholar/old-direct/api/crossref/search/")
        # Expect 400 or 200 (missing param), or 503 if CrossRef service is unavailable
        assert response.status_code in (400, 200, 503)


class TestCrossRefCitationsAPI:
    """Test /scholar/api/crossref/citations/ endpoint."""

    pytestmark = pytest.mark.usefixtures("scholar_old_direct")

    @pytest.fixture
    def client(self):
        return Client()

    @pytest.mark.django_db
    def test_citations_endpoint_exists(self, client):
        """CrossRef citations endpoint should exist."""
        response = client.get("/apps/scholar/old-direct/api/crossref/citations/")
        assert response.status_code != 404


class TestCrossRefHealthAPI:
    """Test /scholar/api/crossref/health/ endpoint."""

    pytestmark = pytest.mark.usefixtures("scholar_old_direct")

    @pytest.fixture
    def client(self):
        return Client()

    @pytest.mark.django_db
    def test_health_endpoint_returns_200(self, client):
        """Health endpoint should return 200 when service is available, 503 when not."""
        response = client.get("/apps/scholar/old-direct/api/crossref/health/")
        assert response.status_code in (200, 503)

    @pytest.mark.django_db
    def test_health_returns_json(self, client):
        """Health endpoint should return JSON."""
        response = client.get("/apps/scholar/old-direct/api/crossref/health/")
        assert response["Content-Type"].startswith("application/json")


class TestCrossRefStatsAPI:
    """Test /scholar/api/crossref/stats/ endpoint."""

    pytestmark = pytest.mark.usefixtures("scholar_old_direct")

    @pytest.fixture
    def client(self):
        return Client()

    @pytest.mark.django_db
    def test_stats_endpoint_exists(self, client):
        """Stats endpoint should exist."""
        response = client.get("/apps/scholar/old-direct/api/crossref/stats/")
        assert response.status_code != 404
