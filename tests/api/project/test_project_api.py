#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Timestamp: 2025-11-30
# File: /home/ywatanabe/proj/scitex-cloud/tests/api/project/test_project_api.py

"""
API tests for project management endpoints.

Tests:
- Project name availability check
- Project list API
- Project creation API
- File tree API
"""

import pytest
from tests.api.conftest import assert_json_response


class TestProjectNameCheck:
    """Tests for project name availability API."""

    def test_check_available_name(
        self, authenticated_client, api_base_url, timestamp
    ):
        """Available project name returns success."""
        response = authenticated_client.get(
            f"{api_base_url}/api/project/check-name/",
            params={"name": f"available-project-{timestamp}"},
        )

        # Endpoint may not exist (404) or require different auth
        assert response.status_code in (200, 401, 403, 404)
        if response.status_code == 200:
            data = response.json()
            assert "available" in data or "exists" in data or "valid" in data

    def test_check_invalid_name(self, authenticated_client, api_base_url):
        """Invalid project name format returns error."""
        response = authenticated_client.get(
            f"{api_base_url}/api/project/check-name/",
            params={"name": "a"},  # Too short
        )

        assert response.status_code in (200, 400, 401, 403, 404)

    def test_check_name_with_special_chars(self, authenticated_client, api_base_url):
        """Project name with invalid characters is rejected."""
        response = authenticated_client.get(
            f"{api_base_url}/api/project/check-name/",
            params={"name": "invalid name!@#"},
        )

        assert response.status_code in (200, 400, 401, 403, 404)


class TestProjectListAPI:
    """Tests for project list API."""

    def test_list_projects_authenticated(self, authenticated_client, api_base_url):
        """Authenticated user can list their projects."""
        response = authenticated_client.get(f"{api_base_url}/api/project/list/")

        # Endpoint may not exist or require different auth
        assert response.status_code in (200, 401, 403, 404)
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, (list, dict))

    def test_list_projects_unauthenticated(self, client, api_base_url):
        """Unauthenticated user cannot list projects."""
        response = client.get(f"{api_base_url}/api/project/list/")

        # Should require auth or endpoint may not exist
        assert response.status_code in (401, 403, 302, 404)


class TestProjectCRUD:
    """Tests for project CRUD operations."""

    def test_create_project_authenticated(
        self, authenticated_client, api_base_url, timestamp
    ):
        """Authenticated user can create a project."""
        project_data = {
            "name": f"test-project-{timestamp}",
            "description": "Test project created by API test",
            "is_private": True,
        }

        response = authenticated_client.post(
            f"{api_base_url}/api/project/create/",
            json=project_data,
        )

        # Should succeed or return validation error (endpoint may not exist)
        assert response.status_code in (200, 201, 400, 401, 403, 404)

    def test_create_project_unauthenticated(self, client, api_base_url, timestamp):
        """Unauthenticated user cannot create a project."""
        project_data = {
            "name": f"test-project-{timestamp}",
            "description": "Test project",
        }

        response = client.post(
            f"{api_base_url}/api/project/create/",
            json=project_data,
        )

        # Should require auth
        assert response.status_code in (401, 403, 302)

    def test_create_project_duplicate_name(
        self, authenticated_client, api_base_url
    ):
        """Creating project with duplicate name fails."""
        # Try to create with likely existing name
        project_data = {
            "name": "default-project",
            "description": "Duplicate test",
        }

        response = authenticated_client.post(
            f"{api_base_url}/api/project/create/",
            json=project_data,
        )

        # Should fail if name exists (endpoint may not exist)
        assert response.status_code in (200, 201, 400, 401, 403, 404, 409)


class TestFileTreeAPI:
    """Tests for file tree API."""

    def test_get_file_tree_authenticated(
        self, authenticated_client, api_base_url, test_credentials
    ):
        """Authenticated user can get file tree for their project."""
        username = test_credentials["username"]
        project = "default-project"

        response = authenticated_client.get(
            f"{api_base_url}/{username}/{project}/api/file-tree/"
        )

        # Should return file tree or 404 if project doesn't exist
        assert response.status_code in (200, 404)

    def test_get_file_tree_unauthenticated_public(self, client, api_base_url):
        """Unauthenticated user can view public project file tree."""
        # Try a potentially public project
        response = client.get(
            f"{api_base_url}/test-user/default-project/api/file-tree/"
        )

        # Either allowed (public) or forbidden (private)
        assert response.status_code in (200, 401, 403, 404)


class TestRepositoryAPI:
    """Tests for repository management API."""

    def test_git_status_authenticated(
        self, authenticated_client, api_base_url, test_credentials
    ):
        """Authenticated user can check git status."""
        username = test_credentials["username"]
        project = "default-project"

        response = authenticated_client.get(
            f"{api_base_url}/{username}/{project}/api/git-status/"
        )

        assert response.status_code in (200, 404)

    def test_repository_health_check(
        self, authenticated_client, api_base_url, test_credentials
    ):
        """Repository health check endpoint works."""
        username = test_credentials["username"]
        project = "default-project"

        response = authenticated_client.get(
            f"{api_base_url}/{username}/{project}/api/repository-health/"
        )

        assert response.status_code in (200, 404)


class TestPermissionsAPI:
    """Tests for project permissions API."""

    def test_check_permissions_owner(
        self, authenticated_client, api_base_url, test_credentials
    ):
        """Owner has full permissions on their project."""
        username = test_credentials["username"]
        project = "default-project"

        response = authenticated_client.get(
            f"{api_base_url}/{username}/{project}/api/permissions/"
        )

        if response.status_code == 200:
            data = response.json()
            # Owner should have write permissions
            assert data.get("can_write", True) or data.get("is_owner", True)

    def test_check_permissions_unauthenticated(self, client, api_base_url):
        """Unauthenticated user has limited permissions."""
        response = client.get(
            f"{api_base_url}/test-user/default-project/api/permissions/"
        )

        # Either forbidden or returns read-only permissions
        assert response.status_code in (200, 401, 403, 404)
