"""Tests for path-based figz bundle API views."""

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


class TestLoadFigzByPath:
    """Tests for load_figz_by_path endpoint."""

    def test_missing_path_returns_400(self, request_factory, mock_user):
        """Should return 400 if path parameter is missing."""
        from apps.workspace.vis_app.views.api.bundles.path_figz import load_figz_by_path

        request = request_factory.get("/vis/api/bundles/figz/load/")
        request.user = mock_user

        response = load_figz_by_path(request)

        assert response.status_code == 400

    def test_resolves_relative_path(self, request_factory, mock_user):
        """Should resolve relative paths using project context."""
        from apps.workspace.vis_app.views.api.bundles.path_figz import load_figz_by_path

        with patch(
            "apps.workspace.vis_app.views.api.bundles.path_figz.resolve_bundle_path"
        ) as mock_resolve:
            mock_resolve.return_value = Path("/data/projects/owner/slug/figure.figz")
            with patch(
                "apps.workspace.vis_app.services.figz.FigzService.load_bundle"
            ) as mock_load:
                mock_load.return_value = {"spec": {"panels": []}, "style": {}}

                request = request_factory.get(
                    "/vis/api/bundles/figz/load/",
                    {
                        "path": "scitex/vis/figures/Figure1.figz",
                        "project_owner": "owner",
                        "project_slug": "slug",
                    },
                )
                request.user = mock_user

                response = load_figz_by_path(request)

                assert response.status_code == 200
                mock_resolve.assert_called_once()


class TestSaveFigzCanvas:
    """Tests for save_figz_canvas endpoint."""

    def test_invalid_json_returns_400(self, request_factory, mock_user):
        """Should return 400 for invalid JSON."""
        from apps.workspace.vis_app.views.api.bundles.path_figz import save_figz_canvas

        request = request_factory.post(
            "/vis/api/bundles/figz/save/",
            data="not json",
            content_type="application/json",
        )
        request.user = mock_user

        response = save_figz_canvas(request)

        assert response.status_code == 400

    def test_saves_canvas_successfully(self, request_factory, mock_user):
        """Should save canvas state as figz bundle."""
        import json

        from apps.workspace.vis_app.views.api.bundles.path_figz import save_figz_canvas

        with patch(
            "apps.workspace.vis_app.services.figz.FigzService.save_canvas_as_bundle"
        ) as mock_save:
            mock_save.return_value = {"bundle_path": "/path/to/Figure1.figz"}

            request = request_factory.post(
                "/vis/api/bundles/figz/save/",
                data=json.dumps(
                    {
                        "project_owner": "owner",
                        "project_slug": "slug",
                        "figure_name": "Figure1",
                        "panels": [],
                    }
                ),
                content_type="application/json",
            )
            request.user = mock_user

            response = save_figz_canvas(request)

            assert response.status_code == 200
