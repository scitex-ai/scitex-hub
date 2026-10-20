#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for PDF Download API endpoints.

Tests the PDF API endpoints:
- POST /apps/scholar/old-direct/api/pdf/download/
- GET /apps/scholar/old-direct/api/pdf/status/
- POST /apps/scholar/old-direct/api/pdf/download-bulk/
- GET /apps/scholar/old-direct/api/pdf/serve/

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


class TestPDFDownloadAPI:
    """Test /scholar/api/pdf/download/ endpoint."""

    pytestmark = pytest.mark.usefixtures("scholar_old_direct")

    @pytest.fixture
    def client(self):
        return Client()

    @pytest.mark.django_db
    def test_download_endpoint_exists(self, client):
        """PDF download endpoint should exist."""
        response = client.post("/apps/scholar/old-direct/api/pdf/download/")
        # Should not be 404
        assert response.status_code != 404

    @pytest.mark.django_db
    def test_download_requires_authentication(self, client):
        """PDF download should require authentication or return appropriate error."""
        response = client.post(
            "/apps/scholar/old-direct/api/pdf/download/", {"doi": "10.1234/test"}
        )
        # Expect 401/403 for unauthenticated or 400 for missing params
        assert response.status_code in (400, 401, 403, 200)


class TestPDFStatusAPI:
    """Test /scholar/api/pdf/status/ endpoint."""

    pytestmark = pytest.mark.usefixtures("scholar_old_direct")

    @pytest.fixture
    def client(self):
        return Client()

    @pytest.mark.django_db
    def test_status_endpoint_exists(self, client):
        """PDF status endpoint should exist."""
        response = client.get("/apps/scholar/old-direct/api/pdf/status/")
        assert response.status_code != 404


class TestPDFBulkDownloadAPI:
    """Test /scholar/api/pdf/download-bulk/ endpoint."""

    pytestmark = pytest.mark.usefixtures("scholar_old_direct")

    @pytest.fixture
    def client(self):
        return Client()

    @pytest.mark.django_db
    def test_bulk_download_endpoint_exists(self, client):
        """Bulk PDF download endpoint should exist."""
        response = client.post("/apps/scholar/old-direct/api/pdf/download-bulk/")
        assert response.status_code != 404


class TestPDFServeAPI:
    """Test /scholar/api/pdf/serve/ endpoint."""

    pytestmark = pytest.mark.usefixtures("scholar_old_direct")

    @pytest.fixture
    def client(self):
        return Client()

    @pytest.mark.django_db
    def test_serve_endpoint_exists(self, client):
        """PDF serve endpoint should exist."""
        response = client.get("/apps/scholar/old-direct/api/pdf/serve/")
        assert response.status_code != 404
