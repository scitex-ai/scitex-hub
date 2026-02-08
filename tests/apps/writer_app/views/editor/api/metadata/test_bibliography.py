#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for apps/writer_app/views/editor/api/metadata/bibliography.py"""

import json
from unittest.mock import MagicMock, patch

import pytest
from django.test import RequestFactory

from apps.writer_app.views.editor.api.metadata.bibliography import (
    regenerate_bibliography_api,
)


@pytest.fixture
def rf():
    return RequestFactory()


@pytest.fixture
def authenticated_request(rf):
    """Create a POST request with authenticated user."""
    request = rf.post("/api/bibliography/regenerate/1/")
    request.user = MagicMock(is_authenticated=True, username="test-user")
    request.session = {}
    return request


@pytest.fixture
def mock_project():
    project = MagicMock()
    project.id = 1
    project.name = "test-project"
    project.git_clone_path = "/tmp/test-project"
    project.owner = MagicMock()
    return project


class TestRegenerateBibliographyApi:
    """Test bibliography regeneration API endpoint."""

    @patch("apps.project_app.models.Project.objects")
    def test_project_not_found_returns_404(self, mock_qs, authenticated_request):
        """@api_login_optional returns 404 when project doesn't exist."""
        from apps.project_app.models import Project

        mock_qs.get.side_effect = Project.DoesNotExist
        response = regenerate_bibliography_api(authenticated_request, project_id=999)
        assert response.status_code == 404

    @patch("apps.project_app.services.bibliography_manager.regenerate_bibliography")
    @patch("apps.project_app.models.Project.objects")
    def test_success_returns_scholar_count_and_duplicates(
        self, mock_qs, mock_regen, authenticated_request, mock_project
    ):
        mock_project.owner = authenticated_request.user
        mock_qs.get.return_value = mock_project
        mock_regen.return_value = {
            "success": True,
            "scholar_count": 5,
            "duplicates_removed": 2,
            "errors": [],
        }

        response = regenerate_bibliography_api(authenticated_request, project_id=1)

        assert response.status_code == 200
        data = json.loads(response.content)
        assert data["success"] is True
        assert data["scholar_count"] == 5
        assert data["duplicates_removed"] == 2
        assert "writer_count" not in data
        assert "total_count" not in data

    @patch("apps.project_app.services.bibliography_manager.regenerate_bibliography")
    @patch("apps.project_app.models.Project.objects")
    def test_failure_returns_errors(
        self, mock_qs, mock_regen, authenticated_request, mock_project
    ):
        mock_project.owner = authenticated_request.user
        mock_qs.get.return_value = mock_project
        mock_regen.return_value = {
            "success": False,
            "scholar_count": 0,
            "duplicates_removed": 0,
            "errors": ["Parse error in test.bib"],
        }

        response = regenerate_bibliography_api(authenticated_request, project_id=1)

        assert response.status_code == 500
        data = json.loads(response.content)
        assert data["success"] is False
        assert "Parse error" in data["details"][0]

    @patch("apps.project_app.models.Project.objects")
    def test_no_git_path_returns_400(
        self, mock_qs, authenticated_request, mock_project
    ):
        mock_project.owner = authenticated_request.user
        mock_project.git_clone_path = None
        mock_qs.get.return_value = mock_project

        response = regenerate_bibliography_api(authenticated_request, project_id=1)

        assert response.status_code == 400
        data = json.loads(response.content)
        assert "git repository" in data["error"]


if __name__ == "__main__":
    import os

    pytest.main([os.path.abspath(__file__)])
