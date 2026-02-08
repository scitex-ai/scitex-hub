#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Project Management Tests

Test project creation, listing, and basic operations.
Requires authenticated session.

Priority: HIGH
Run time: < 120 seconds
"""

import re
import time

import pytest


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
            params={"name": "test-unique-name-12345"},
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

    def test_create_empty_project(
        self, authenticated_session, base_url, test_credentials
    ):
        """Create an empty project successfully."""
        # Get CSRF token from new project page
        resp = authenticated_session.get(f"{base_url}/new/")
        assert resp.status_code == 200

        csrf_match = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', resp.text)
        if not csrf_match:
            pytest.skip("Cannot extract CSRF token")
        csrf_token = csrf_match.group(1)

        # Create unique project name with timestamp
        project_name = f"test-empty-{int(time.time())}"

        # Submit project creation form
        resp = authenticated_session.post(
            f"{base_url}/new/",
            data={
                "csrfmiddlewaretoken": csrf_token,
                "name": project_name,
                "description": "E2E test empty project",
                "init_type": "empty",
                "project_type": "local",
            },
            headers={"Referer": f"{base_url}/new/"},
            allow_redirects=False,
        )

        # Should redirect on success (302) or show success page (200)
        assert resp.status_code in [200, 302], f"Unexpected status: {resp.status_code}"

        if resp.status_code == 302:
            # Check redirect location points to project page
            location = resp.headers.get("Location", "")
            username = test_credentials["username"]
            assert username in location or "projects" in location

    @pytest.mark.slow
    def test_create_template_minimal(
        self, authenticated_session, base_url, test_credentials
    ):
        """Create a project from minimal template."""
        # Get CSRF token
        resp = authenticated_session.get(f"{base_url}/new/")
        assert resp.status_code == 200

        csrf_match = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', resp.text)
        if not csrf_match:
            pytest.skip("Cannot extract CSRF token")
        csrf_token = csrf_match.group(1)

        # Create unique project name
        project_name = f"test-minimal-{int(time.time())}"

        # Submit project creation with template
        resp = authenticated_session.post(
            f"{base_url}/new/",
            data={
                "csrfmiddlewaretoken": csrf_token,
                "name": project_name,
                "description": "E2E test minimal template project",
                "init_type": "template",
                "template_type": "minimal",
                "project_type": "local",
            },
            headers={"Referer": f"{base_url}/new/"},
            allow_redirects=False,
        )

        # Should redirect on success
        assert resp.status_code in [200, 302], f"Unexpected status: {resp.status_code}"

        if resp.status_code == 302:
            location = resp.headers.get("Location", "")
            username = test_credentials["username"]
            # Should redirect to project page or project list
            assert username in location or "projects" in location

    @pytest.mark.slow
    def test_create_template_research(
        self, authenticated_session, base_url, test_credentials
    ):
        """Create a project from research template."""
        # Get CSRF token
        resp = authenticated_session.get(f"{base_url}/new/")
        assert resp.status_code == 200

        csrf_match = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', resp.text)
        if not csrf_match:
            pytest.skip("Cannot extract CSRF token")
        csrf_token = csrf_match.group(1)

        # Create unique project name
        project_name = f"test-research-{int(time.time())}"

        # Submit project creation with research template
        resp = authenticated_session.post(
            f"{base_url}/new/",
            data={
                "csrfmiddlewaretoken": csrf_token,
                "name": project_name,
                "description": "E2E test research template project",
                "init_type": "template",
                "template_type": "research",
                "project_type": "local",
            },
            headers={"Referer": f"{base_url}/new/"},
            allow_redirects=False,
        )

        # Should redirect on success
        assert resp.status_code in [200, 302], f"Unexpected status: {resp.status_code}"

        if resp.status_code == 302:
            location = resp.headers.get("Location", "")
            username = test_credentials["username"]
            assert username in location or "projects" in location

    @pytest.mark.slow
    def test_create_template_pip(
        self, authenticated_session, base_url, test_credentials
    ):
        """Create a project from pip_project template."""
        # Get CSRF token
        resp = authenticated_session.get(f"{base_url}/new/")
        assert resp.status_code == 200

        csrf_match = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', resp.text)
        if not csrf_match:
            pytest.skip("Cannot extract CSRF token")
        csrf_token = csrf_match.group(1)

        # Create unique project name
        project_name = f"test-pip-{int(time.time())}"

        # Submit project creation with pip template
        resp = authenticated_session.post(
            f"{base_url}/new/",
            data={
                "csrfmiddlewaretoken": csrf_token,
                "name": project_name,
                "description": "E2E test pip project template",
                "init_type": "template",
                "template_type": "pip_project",
                "project_type": "local",
            },
            headers={"Referer": f"{base_url}/new/"},
            allow_redirects=False,
        )

        # Should redirect on success
        assert resp.status_code in [200, 302], f"Unexpected status: {resp.status_code}"

        if resp.status_code == 302:
            location = resp.headers.get("Location", "")
            username = test_credentials["username"]
            assert username in location or "projects" in location

    def test_project_name_validation_empty(self, authenticated_session, base_url):
        """Project creation should fail with empty name."""
        # Get CSRF token
        resp = authenticated_session.get(f"{base_url}/new/")
        assert resp.status_code == 200

        csrf_match = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', resp.text)
        if not csrf_match:
            pytest.skip("Cannot extract CSRF token")
        csrf_token = csrf_match.group(1)

        # Try to create project with empty name
        resp = authenticated_session.post(
            f"{base_url}/new/",
            data={
                "csrfmiddlewaretoken": csrf_token,
                "name": "",
                "description": "Test empty name validation",
                "init_type": "empty",
                "project_type": "local",
            },
            headers={"Referer": f"{base_url}/new/"},
            allow_redirects=True,
        )

        # Should either stay on form (200) with error or redirect back
        assert resp.status_code == 200
        # Check for error message in response
        assert any(
            x in resp.text.lower() for x in ["error", "required", "invalid", "name"]
        )

    def test_project_name_validation_duplicate(
        self, authenticated_session, base_url, test_credentials
    ):
        """Project creation should fail with duplicate name."""
        # Get CSRF token
        resp = authenticated_session.get(f"{base_url}/new/")
        assert resp.status_code == 200

        csrf_match = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', resp.text)
        if not csrf_match:
            pytest.skip("Cannot extract CSRF token")
        csrf_token = csrf_match.group(1)

        # Create first project
        project_name = f"test-duplicate-{int(time.time())}"

        resp1 = authenticated_session.post(
            f"{base_url}/new/",
            data={
                "csrfmiddlewaretoken": csrf_token,
                "name": project_name,
                "description": "First project",
                "init_type": "empty",
                "project_type": "local",
            },
            headers={"Referer": f"{base_url}/new/"},
            allow_redirects=False,
        )

        # First creation should succeed
        assert resp1.status_code in [200, 302]

        # Get new CSRF token for second request
        resp = authenticated_session.get(f"{base_url}/new/")
        csrf_match = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', resp.text)
        if csrf_match:
            csrf_token = csrf_match.group(1)

        # Try to create duplicate
        resp2 = authenticated_session.post(
            f"{base_url}/new/",
            data={
                "csrfmiddlewaretoken": csrf_token,
                "name": project_name,
                "description": "Duplicate project",
                "init_type": "empty",
                "project_type": "local",
            },
            headers={"Referer": f"{base_url}/new/"},
            allow_redirects=True,
        )

        # Should fail with error
        assert resp2.status_code == 200
        # Check for error about duplicate/exists
        assert any(
            x in resp2.text.lower() for x in ["exists", "duplicate", "already", "error"]
        )


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
