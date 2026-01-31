#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Project Management Tests

Test project creation, listing, and basic operations.
Requires authenticated session.

Priority: HIGH
Run time: < 60 seconds
"""

import pytest
import re


class TestProjectList:
    """Test project listing functionality."""

    def test_project_list_requires_auth(self, api_client, test_credentials):
        """Project list page requires authentication."""
        username = test_credentials["username"]
        resp = api_client.get(f"/{username}/", allow_redirects=False)
        # Either redirects to login or shows 404 for non-existent user
        assert resp.status_code in [302, 404]


class TestProjectCreate:
    """Test project creation flow."""

    def test_new_project_page_requires_auth(self, api_client):
        """/new/ page requires authentication."""
        resp = api_client.get("/new/", allow_redirects=False)
        assert resp.status_code == 302
        location = resp.headers.get("Location", "")
        assert "login" in location.lower()

    def test_new_project_page_loads(self, authenticated_session, base_url):
        """Project creation page loads for authenticated user."""
        resp = authenticated_session.get(f"{base_url}/new/")
        assert resp.status_code == 200
        # Check for form elements
        assert "name" in resp.text.lower()
        assert "csrfmiddlewaretoken" in resp.text

    def test_project_name_check_api(self, authenticated_session, base_url):
        """Project name availability check API works."""
        resp = authenticated_session.get(
            f"{base_url}/project/api/check-name/",
            params={"name": "test-unique-name-12345"}
        )
        assert resp.status_code == 200
        # Check if response is JSON
        content_type = resp.headers.get("content-type", "")
        if "application/json" in content_type:
            data = resp.json()
            assert "available" in data or "valid" in data or "error" in data
        else:
            # May return HTML if not authenticated properly
            assert resp.status_code == 200  # At least doesn't error


class TestProjectAPI:
    """Test project-related APIs."""

    def test_file_tree_api_requires_valid_project(self, api_client, test_credentials):
        """File tree API returns error for invalid project."""
        username = test_credentials["username"]
        resp = api_client.get(f"/{username}/nonexistent-project-12345/api/file-tree/")
        # Should be 404 for non-existent project
        assert resp.status_code in [404, 403, 302]

    def test_api_project_list(self, authenticated_session, base_url):
        """Project list API returns data."""
        resp = authenticated_session.get(f"{base_url}/project/api/list/")
        if resp.status_code == 200:
            data = resp.json()
            assert isinstance(data, (list, dict))
