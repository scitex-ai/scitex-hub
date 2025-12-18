"""Tests for bundle path resolution helpers."""

from pathlib import Path
from unittest.mock import Mock, patch


class TestResolveBundlePath:
    """Tests for resolve_bundle_path function."""

    def test_absolute_path_returned_unchanged(self):
        """Absolute paths should be returned as-is."""
        from apps.vis_app.views.api.bundles._path_helpers import resolve_bundle_path

        abs_path = "/home/user/project/figure.figz"
        result = resolve_bundle_path(abs_path)

        assert result == Path(abs_path)

    def test_relative_path_with_project_context(self):
        """Relative paths should be resolved using project context."""
        from apps.vis_app.views.api.bundles._path_helpers import resolve_bundle_path

        mock_project = Mock()
        mock_project.get_local_path.return_value = Path("/data/projects/owner/slug")

        with patch("apps.project_app.models.Project") as MockProject:
            MockProject.objects.get.return_value = mock_project

            result = resolve_bundle_path(
                "scitex/vis/figures/Figure1.figz",
                project_owner="owner",
                project_slug="slug"
            )

            assert result == Path("/data/projects/owner/slug/scitex/vis/figures/Figure1.figz")

    def test_relative_path_with_user_fallback(self):
        """Relative paths should fall back to user's project."""
        from apps.vis_app.views.api.bundles._path_helpers import resolve_bundle_path

        mock_project = Mock()
        mock_project.get_local_path.return_value = Path("/data/user/default")
        mock_user = Mock()

        with patch("apps.project_app.services.project_utils.get_user_project") as mock_get:
            mock_get.return_value = mock_project

            result = resolve_bundle_path(
                "scitex/vis/figures/Figure1.figz",
                user=mock_user
            )

            assert result == Path("/data/user/default/scitex/vis/figures/Figure1.figz")

    def test_relative_path_no_context_returns_as_is(self):
        """Relative paths without context should be returned as-is."""
        from apps.vis_app.views.api.bundles._path_helpers import resolve_bundle_path

        rel_path = "scitex/vis/figures/Figure1.figz"
        result = resolve_bundle_path(rel_path)

        assert result == Path(rel_path)

    def test_project_resolution_error_handled(self):
        """Project resolution errors should be handled gracefully."""
        from apps.vis_app.views.api.bundles._path_helpers import resolve_bundle_path

        with patch("apps.project_app.models.Project") as MockProject:
            MockProject.objects.get.side_effect = Exception("DB error")

            # Should not raise, should return path as-is
            result = resolve_bundle_path(
                "scitex/vis/figures/Figure1.figz",
                project_owner="owner",
                project_slug="slug"
            )

            assert result == Path("scitex/vis/figures/Figure1.figz")
