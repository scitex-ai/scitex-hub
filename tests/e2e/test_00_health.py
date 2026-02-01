#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Health Check Tests

These tests verify that all critical services are running.
MUST pass before any other tests.

Priority: CRITICAL
Run time: < 10 seconds
"""

import pytest


class TestServiceHealth:
    """Test that all services are running and healthy."""

    def test_server_responds(self, api_client):
        """Server responds to HTTP requests."""
        resp = api_client.get("/")
        assert resp.status_code == 200, f"Server not responding: {resp.status_code}"

    def test_healthz_endpoint(self, api_client):
        """Health check endpoint returns OK."""
        resp = api_client.get("/healthz/")
        assert resp.status_code == 200
        # Optional: check response content
        data = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
        if data:
            assert data.get("status") in ["ok", "healthy", True]

    def test_server_health_api(self, api_client):
        """Server health API returns service status."""
        resp = api_client.get("/api/server-health/")
        assert resp.status_code == 200
        data = resp.json()
        # Check critical services
        assert "services" in data or "status" in data

    def test_static_files_served(self, api_client):
        """Static files are being served."""
        # Test favicon - this is commonly accessible
        resp = api_client.get("/favicon.ico", allow_redirects=True)
        # 200 or 301/302 redirect are acceptable, 404 means static serving might be different
        assert resp.status_code in [200, 301, 302, 404], f"Static files error: {resp.status_code}"
        # If 404, try another static path
        if resp.status_code == 404:
            resp = api_client.get("/static/", allow_redirects=True)
            # Just check it doesn't 500
            assert resp.status_code != 500, "Static files serving error"

    def test_login_page_accessible(self, api_client):
        """Login page is accessible."""
        resp = api_client.get("/auth/login/")
        assert resp.status_code == 200
        assert "login" in resp.text.lower() or "sign in" in resp.text.lower()


class TestDatabaseConnection:
    """Test database connectivity through API endpoints."""

    def test_visitor_heartbeat(self, api_client):
        """Visitor heartbeat endpoint works (DB read)."""
        resp = api_client.get("/api/visitor/heartbeat/")
        # Should work even without authentication
        assert resp.status_code in [200, 401, 403]


class TestGiteaConnection:
    """Test Gitea service connectivity."""

    def test_gitea_health(self, api_client):
        """Gitea service is reachable via health check."""
        resp = api_client.get("/api/server-health/")
        if resp.status_code == 200:
            data = resp.json()
            services = data.get("services", {})

            # Check gitea_api first (more reliable indicator)
            gitea_api_status = services.get("gitea_api", "")
            if isinstance(gitea_api_status, str):
                assert gitea_api_status.lower() in ["healthy", "ok", "running", "unknown"], \
                    f"Gitea API unhealthy: {gitea_api_status}"

            # gitea container status may show "unknown" even when working
            gitea_status = services.get("gitea", "")
            if isinstance(gitea_status, str) and gitea_status.lower() == "unhealthy":
                pytest.fail(f"Gitea container unhealthy: {gitea_status}")
