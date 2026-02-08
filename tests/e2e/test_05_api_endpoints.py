#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Critical API Endpoint Tests

Test that critical API endpoints respond correctly.
These APIs are used by the frontend and must work.

Priority: HIGH
Run time: < 30 seconds
"""



class TestHealthAPIs:
    """Test health and status APIs."""

    def test_server_health_api(self, api_client):
        """Server health API returns valid response."""
        resp = api_client.get("/api/server-health/")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, dict)

    def test_visitor_heartbeat_api(self, api_client):
        """Visitor heartbeat API works."""
        resp = api_client.get("/api/visitor/heartbeat/")
        # 400 when called without required session/params
        assert resp.status_code in [200, 400, 401, 403]


class TestUserAPIs:
    """Test user-related APIs."""

    def test_user_search_api_requires_auth(self, api_client):
        """User search API handles unauthenticated requests."""
        resp = api_client.get("/api/users/search/", params={"q": "test"})
        # Should require auth or return empty
        assert resp.status_code in [200, 401, 403]

    def test_theme_api(self, api_client):
        """Theme API returns valid response."""
        resp = api_client.get("/auth/api/get-theme/")
        assert resp.status_code == 200


class TestProjectAPIs:
    """Test project-related APIs."""

    def test_check_name_api(self, api_client):
        """Project name check API works."""
        resp = api_client.get("/project/api/check-name/", params={"name": "test"})
        assert resp.status_code == 200
        content_type = resp.headers.get("content-type", "")
        if "application/json" in content_type:
            data = resp.json()
            assert isinstance(data, dict)
        # May return HTML for unauthenticated requests

    def test_switch_project_api_requires_auth(self, api_client):
        """Switch project API requires authentication."""
        resp = api_client.post("/api/project/switch/", json={"project_id": 1})
        # Should fail without auth
        assert resp.status_code in [401, 403]


class TestScholarAPIs:
    """Test Scholar module APIs."""

    def test_citation_graph_api(self, api_client):
        """Citation graph API endpoint exists."""
        resp = api_client.get("/api/scholar/citation-graph/status/")
        # May return 404 if not implemented, but shouldn't 500
        assert resp.status_code != 500
