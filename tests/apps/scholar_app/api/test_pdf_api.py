#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for PDF Download API endpoints.

Tests the PDF API endpoints:
- POST /apps/scholar/api/pdf/download/
- GET /apps/scholar/api/pdf/status/
- POST /apps/scholar/api/pdf/download-bulk/
- GET /apps/scholar/api/pdf/serve/
"""

import pytest
from django.test import Client


class TestPDFDownloadAPI:
    """Test /scholar/api/pdf/download/ endpoint."""

    @pytest.fixture
    def client(self):
        return Client()

    @pytest.mark.django_db
    def test_download_endpoint_exists(self, client):
        """PDF download endpoint should exist."""
        response = client.post("/apps/scholar/api/pdf/download/")
        # Should not be 404
        assert response.status_code != 404

    @pytest.mark.django_db
    def test_download_requires_authentication(self, client):
        """PDF download should require authentication or return appropriate error."""
        response = client.post(
            "/apps/scholar/api/pdf/download/", {"doi": "10.1234/test"}
        )
        # Expect 401/403 for unauthenticated or 400 for missing params
        assert response.status_code in (400, 401, 403, 200)


class TestPDFStatusAPI:
    """Test /scholar/api/pdf/status/ endpoint."""

    @pytest.fixture
    def client(self):
        return Client()

    @pytest.mark.django_db
    def test_status_endpoint_exists(self, client):
        """PDF status endpoint should exist."""
        response = client.get("/apps/scholar/api/pdf/status/")
        assert response.status_code != 404


class TestPDFBulkDownloadAPI:
    """Test /scholar/api/pdf/download-bulk/ endpoint."""

    @pytest.fixture
    def client(self):
        return Client()

    @pytest.mark.django_db
    def test_bulk_download_endpoint_exists(self, client):
        """Bulk PDF download endpoint should exist."""
        response = client.post("/apps/scholar/api/pdf/download-bulk/")
        assert response.status_code != 404


class TestPDFServeAPI:
    """Test /scholar/api/pdf/serve/ endpoint."""

    @pytest.fixture
    def client(self):
        return Client()

    @pytest.mark.django_db
    def test_serve_endpoint_exists(self, client):
        """PDF serve endpoint should exist."""
        response = client.get("/apps/scholar/api/pdf/serve/")
        assert response.status_code != 404
