"""Tests for path-based pltz bundle API views."""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from django.test import RequestFactory


@pytest.fixture
def request_factory():
    """Create a Django request factory."""
    return RequestFactory()


@pytest.fixture
def mock_user():
    """Create a mock authenticated user."""
    user = Mock()
    user.is_authenticated = True
    user.id = 1
    return user


class TestGetPltzPreviewByPath:
    """Tests for get_pltz_preview_by_path endpoint."""

    def test_missing_path_returns_400(self, request_factory, mock_user):
        """Should return 400 if path parameter is missing."""
        from apps.workspace.figrecipe_app.views.api.bundles.path_pltz import (
            get_pltz_preview_by_path,
        )

        request = request_factory.get("/vis/api/bundles/pltz/preview/")
        request.user = mock_user

        response = get_pltz_preview_by_path(request)

        assert response.status_code == 400

    def test_resolves_relative_path_with_project_context(
        self, request_factory, mock_user
    ):
        """Should resolve relative paths using project context."""
        from apps.workspace.figrecipe_app.views.api.bundles.path_pltz import (
            get_pltz_preview_by_path,
        )

        mock_project = Mock()
        mock_project.get_local_path.return_value = Path("/data/projects/owner/slug")

        with patch("apps.infra.project_app.models.Project") as MockProject:
            MockProject.objects.get.return_value = mock_project
            with patch(
                "apps.workspace.figrecipe_app.services.pltz_service.PltzService.get_preview_image"
            ) as mock_preview:
                mock_preview.return_value = b"PNG_DATA"

                request = request_factory.get(
                    "/vis/api/bundles/pltz/preview/",
                    {
                        "path": "scitex/vis/figures/Figure1.figz/A.pltz",
                        "project_owner": "owner",
                        "project_slug": "slug",
                    },
                )
                request.user = mock_user

                response = get_pltz_preview_by_path(request)

                assert response.status_code == 200
                # Verify the resolved path was passed to the service
                mock_preview.assert_called_once()
                called_path = mock_preview.call_args[0][0]
                assert "/data/projects/owner/slug" in called_path

    def test_returns_png_content_type(self, request_factory, mock_user):
        """Should return correct content type for PNG."""
        from apps.workspace.figrecipe_app.views.api.bundles.path_pltz import (
            get_pltz_preview_by_path,
        )

        with patch(
            "apps.workspace.figrecipe_app.views.api.bundles._path_helpers.resolve_bundle_path"
        ) as mock_resolve:
            mock_resolve.return_value = Path("/absolute/path/figure.pltz")
            with patch(
                "apps.workspace.figrecipe_app.services.pltz_service.PltzService.get_preview_image"
            ) as mock_preview:
                mock_preview.return_value = b"PNG_DATA"

                request = request_factory.get(
                    "/vis/api/bundles/pltz/preview/",
                    {"path": "/absolute/path/figure.pltz", "type": "png"},
                )
                request.user = mock_user

                response = get_pltz_preview_by_path(request)

                assert response.status_code == 200
                assert response["Content-Type"] == "image/png"


class TestLoadPltzByPath:
    """Tests for load_pltz_by_path endpoint."""

    def test_missing_path_returns_400(self, request_factory, mock_user):
        """Should return 400 if path parameter is missing."""
        from apps.workspace.figrecipe_app.views.api.bundles.path_pltz import (
            load_pltz_by_path,
        )

        request = request_factory.get("/vis/api/bundles/pltz/load/")
        request.user = mock_user

        response = load_pltz_by_path(request)

        assert response.status_code == 400


class TestCreatePltzFromPlot:
    """Tests for create_pltz_from_plot endpoint."""

    def test_missing_plot_type_returns_400(self, request_factory, mock_user):
        """Should return 400 if plot_type is missing."""
        import json

        from apps.workspace.figrecipe_app.views.api.bundles.path_pltz import (
            create_pltz_from_plot,
        )

        request = request_factory.post(
            "/vis/api/bundles/pltz/create/",
            data=json.dumps({}),
            content_type="application/json",
        )
        request.user = mock_user

        response = create_pltz_from_plot(request)

        assert response.status_code == 400
