"""Tests for path-based panel API views."""

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


class TestAddPanelToFigz:
    """Tests for add_panel_to_figz endpoint."""

    def test_invalid_json_returns_400(self, request_factory, mock_user):
        """Should return 400 for invalid JSON."""
        from apps.workspace.vis_app.views.api.bundles.path_panel import (
            add_panel_to_figz,
        )

        request = request_factory.post(
            "/vis/api/bundles/figz/add-panel/",
            data="not json",
            content_type="application/json",
        )
        request.user = mock_user

        response = add_panel_to_figz(request)

        assert response.status_code == 400

    def test_missing_gallery_info_returns_400(self, request_factory, mock_user):
        """Should return 400 if gallery_category or gallery_plot_name missing."""
        import json

        from apps.workspace.vis_app.views.api.bundles.path_panel import (
            add_panel_to_figz,
        )

        request = request_factory.post(
            "/vis/api/bundles/figz/add-panel/",
            data=json.dumps({"project_owner": "owner", "project_slug": "slug"}),
            content_type="application/json",
        )
        request.user = mock_user

        response = add_panel_to_figz(request)

        assert response.status_code == 400


class TestGetFigzPanelPreview:
    """Tests for get_figz_panel_preview endpoint."""

    def test_missing_path_returns_400(self, request_factory, mock_user):
        """Should return 400 if path parameter is missing."""
        from apps.workspace.vis_app.views.api.bundles.path_panel import (
            get_figz_panel_preview,
        )

        request = request_factory.get("/vis/api/bundles/figz/panel-preview/")
        request.user = mock_user

        response = get_figz_panel_preview(request)

        assert response.status_code == 400

    def test_missing_panel_returns_400(self, request_factory, mock_user):
        """Should return 400 if panel parameter is missing."""
        from apps.workspace.vis_app.views.api.bundles.path_panel import (
            get_figz_panel_preview,
        )

        request = request_factory.get(
            "/vis/api/bundles/figz/panel-preview/", {"path": "/path/to/figure.figz"}
        )
        request.user = mock_user

        response = get_figz_panel_preview(request)

        assert response.status_code == 400

    def test_resolves_relative_path(self, request_factory, mock_user):
        """Should resolve relative paths using project context."""
        from apps.workspace.vis_app.views.api.bundles.path_panel import (
            get_figz_panel_preview,
        )

        with patch(
            "apps.workspace.vis_app.views.api.bundles.path_panel.resolve_bundle_path"
        ) as mock_resolve:
            mock_resolve.return_value = Path("/data/projects/owner/slug/figure.figz")
            with patch("scitex.fig.Figz") as MockFigz:
                mock_figz = Mock()
                mock_figz.get_panel_pltz.return_value = None
                MockFigz.return_value = mock_figz

                request = request_factory.get(
                    "/vis/api/bundles/figz/panel-preview/",
                    {
                        "path": "scitex/vis/figures/Figure1.figz",
                        "panel": "A",
                        "project_owner": "owner",
                        "project_slug": "slug",
                    },
                )
                request.user = mock_user

                response = get_figz_panel_preview(request)

                # Should have called resolve_bundle_path
                mock_resolve.assert_called_once()
