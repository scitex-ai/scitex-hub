#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Timestamp: "2025-12-18 (ywatanabe)"
# File: /home/ywatanabe/proj/scitex-cloud/tests/apps/vis_app/services/test_figz_service.py

"""Tests for FigzService - embedded panel workflow.

Critical Architecture Requirement:
- Panels MUST be embedded INSIDE the .figz bundle as {panel_id}.pltz
- NO standalone .pltz files should be created
- The gallery -> canvas flow embeds panels directly in figz
"""

import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def temp_figz_dir():
    """Create a temporary directory for figz bundles."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def figz_class():
    """Get Figz class from scitex package."""
    import os
    import sys

    SCITEX_CODE_PATH = os.environ.get(
        "SCITEX_CODE_PATH", "/home/ywatanabe/proj/scitex-code"
    )
    if f"{SCITEX_CODE_PATH}/src" not in sys.path:
        sys.path.insert(0, f"{SCITEX_CODE_PATH}/src")

    try:
        from scitex.fig import Figz
    except (ImportError, ModuleNotFoundError):
        pytest.skip("scitex[fig] not installed (requires pip install scitex[fig])")

    return Figz


@pytest.fixture
def pltz_class():
    """Get Pltz class from scitex package."""
    import os
    import sys

    SCITEX_CODE_PATH = os.environ.get(
        "SCITEX_CODE_PATH", "/home/ywatanabe/proj/scitex-code"
    )
    if f"{SCITEX_CODE_PATH}/src" not in sys.path:
        sys.path.insert(0, f"{SCITEX_CODE_PATH}/src")

    from scitex.plt import Pltz

    return Pltz


class TestFigzEmbeddedPanels:
    """Test embedded panel workflow - panels inside figz, no standalone pltz."""

    def test_create_empty_figz(self, temp_figz_dir, figz_class):
        """Test creating an empty figz bundle."""
        figz_path = temp_figz_dir / "Figure1.figz"

        figz = figz_class.create(figz_path, "Figure1")

        assert figz_path.exists()
        assert figz.figure_name == "Figure1"
        assert figz.panels == []

    def test_add_panel_embeds_pltz(self, temp_figz_dir, figz_class, pltz_class):
        """Test that add_panel embeds pltz bytes inside figz."""
        figz_path = temp_figz_dir / "Figure1.figz"
        pltz_path = temp_figz_dir / "temp_panel.pltz"

        # Create a pltz from gallery
        pltz = pltz_class.create_from_gallery(pltz_path, "line", "plot")
        with open(pltz_path, "rb") as f:
            pltz_bytes = f.read()

        # Create figz and add panel
        figz = figz_class.create(figz_path, "Figure1")
        figz.add_panel(
            "A", pltz_bytes, {"x_mm": 10, "y_mm": 10}, {"width_mm": 80, "height_mm": 60}
        )

        # Verify panel is embedded
        assert len(figz.panels) == 1
        assert figz.panels[0]["id"] == "A"
        assert figz.panels[0]["plot"] == "A.pltz"

        # Verify pltz bytes can be retrieved
        retrieved_bytes = figz.get_panel_pltz("A")
        assert retrieved_bytes is not None
        assert len(retrieved_bytes) > 0

    def test_panel_preserved_after_reload(self, temp_figz_dir, figz_class, pltz_class):
        """Test that embedded panel persists after reload."""
        figz_path = temp_figz_dir / "Figure1.figz"
        pltz_path = temp_figz_dir / "temp_panel.pltz"

        # Create and save figz with panel
        pltz = pltz_class.create_from_gallery(pltz_path, "line", "plot")
        with open(pltz_path, "rb") as f:
            pltz_bytes = f.read()

        figz = figz_class.create(figz_path, "Figure1")
        figz.add_panel(
            "A", pltz_bytes, {"x_mm": 5, "y_mm": 5}, {"width_mm": 80, "height_mm": 68}
        )

        # Reload figz
        figz2 = figz_class(figz_path)

        # Verify panel is still there
        assert len(figz2.panels) == 1
        assert figz2.panels[0]["id"] == "A"

        # Verify pltz bytes match
        retrieved_bytes = figz2.get_panel_pltz("A")
        assert retrieved_bytes == pltz_bytes

    def test_multiple_panels(self, temp_figz_dir, figz_class, pltz_class):
        """Test adding multiple panels."""
        figz_path = temp_figz_dir / "Figure1.figz"
        pltz_path = temp_figz_dir / "temp_panel.pltz"

        # Create pltz bytes
        pltz = pltz_class.create_from_gallery(pltz_path, "line", "plot")
        with open(pltz_path, "rb") as f:
            pltz_bytes = f.read()

        # Create figz with multiple panels
        figz = figz_class.create(figz_path, "Figure1")
        figz.add_panel("A", pltz_bytes, {"x_mm": 5, "y_mm": 5})
        figz.add_panel("B", pltz_bytes, {"x_mm": 90, "y_mm": 5})
        figz.add_panel("C", pltz_bytes, {"x_mm": 5, "y_mm": 75})

        # Verify all panels
        assert len(figz.panels) == 3
        panel_ids = figz.list_panel_ids()
        assert "A" in panel_ids
        assert "B" in panel_ids
        assert "C" in panel_ids


class TestSaveCanvasAsBundle:
    """Test save_canvas_as_bundle preserves embedded panels."""

    def test_save_preserves_embedded_panels(
        self, temp_figz_dir, figz_class, pltz_class
    ):
        """Test that save_canvas_as_bundle preserves embedded panel bytes."""
        from apps.vis_app.services.figz import save_canvas_as_bundle

        figz_path = temp_figz_dir / "Figure1.figz"
        pltz_path = temp_figz_dir / "temp_panel.pltz"

        # Create figz with embedded panel
        pltz = pltz_class.create_from_gallery(pltz_path, "line", "plot")
        with open(pltz_path, "rb") as f:
            original_pltz_bytes = f.read()

        figz = figz_class.create(figz_path, "Figure1")
        figz.add_panel(
            "A",
            original_pltz_bytes,
            {"x_mm": 5, "y_mm": 5},
            {"width_mm": 80, "height_mm": 68},
        )

        # Verify panel was created correctly
        figz_check = figz_class(figz_path)
        assert len(figz_check.panels) == 1, f"Panel not created: {figz_check.panels}"
        check_bytes = figz_check.get_panel_pltz("A")
        assert check_bytes is not None, "Panel bytes not stored after creation"

        # Simulate auto-save with embedded panel path (uses '#' notation)
        panels = [
            {
                "label": "A",
                "pltz_path": f"{figz_path}#A",  # Embedded panel notation
                "position": {"x_mm": 10, "y_mm": 15},  # Updated position
                "size": {"width_mm": 85, "height_mm": 70},  # Updated size
            }
        ]

        # Mock project context by manually setting bundle path
        # In real usage, this uses project_owner/project_slug
        import unittest.mock as mock

        with mock.patch("apps.vis_app.services.figz.get_bundle_base_path") as mock_path:
            mock_path.return_value = temp_figz_dir

            # Call save with mock user
            class MockUser:
                id = 1

            result = save_canvas_as_bundle(
                project_owner=None,
                project_slug=None,
                figure_name="Figure1",
                panels=panels,
                canvas_size={"width_mm": 170, "height_mm": 120},
                user=MockUser(),
            )

        assert result["saved"] is True
        # Verify result path matches expected path
        assert result["path"] == str(
            figz_path
        ), f"Path mismatch: {result['path']} != {figz_path}"

        # Reload and verify panel bytes are preserved
        figz2 = figz_class(figz_path)
        assert len(figz2.panels) == 1, f"Panels after save: {figz2.panels}"

        retrieved_bytes = figz2.get_panel_pltz("A")
        assert retrieved_bytes is not None, "Panel bytes are None after save"
        assert (
            retrieved_bytes == original_pltz_bytes
        ), f"Bytes mismatch: {len(retrieved_bytes) if retrieved_bytes else 0} vs {len(original_pltz_bytes)}"

        # Verify position was updated
        panel = figz2.get_panel("A")
        assert panel["position"]["x_mm"] == 10
        assert panel["position"]["y_mm"] == 15

    def test_no_standalone_pltz_created(self, temp_figz_dir, figz_class, pltz_class):
        """Verify no standalone .pltz files are created during workflow."""
        # After workflow, only .figz should exist, no standalone .pltz

        figz_path = temp_figz_dir / "Figure1.figz"
        pltz_path = temp_figz_dir / "temp_panel.pltz"

        # Create figz with panel
        pltz = pltz_class.create_from_gallery(pltz_path, "line", "plot")
        with open(pltz_path, "rb") as f:
            pltz_bytes = f.read()

        figz = figz_class.create(figz_path, "Figure1")
        figz.add_panel("A", pltz_bytes)

        # Clean up temp pltz
        pltz_path.unlink()

        # Check no standalone .pltz files in directory
        pltz_files = list(temp_figz_dir.glob("*.pltz"))
        assert len(pltz_files) == 0, f"Found standalone .pltz files: {pltz_files}"

        # Only figz should exist
        figz_files = list(temp_figz_dir.glob("*.figz"))
        assert len(figz_files) == 1


class TestPanelPreviewRendering:
    """Test panel preview rendering from embedded pltz."""

    def test_render_panel_preview(self, temp_figz_dir, figz_class, pltz_class):
        """Test rendering preview from embedded panel."""
        figz_path = temp_figz_dir / "Figure1.figz"
        pltz_path = temp_figz_dir / "temp_panel.pltz"

        # Create figz with panel
        pltz = pltz_class.create_from_gallery(pltz_path, "line", "plot")
        with open(pltz_path, "rb") as f:
            pltz_bytes = f.read()

        figz = figz_class.create(figz_path, "Figure1")
        figz.add_panel("A", pltz_bytes)

        # Extract pltz and render preview
        retrieved_bytes = figz.get_panel_pltz("A")
        assert retrieved_bytes is not None

        # Save to temp file and load as Pltz to render
        temp_pltz = temp_figz_dir / "temp_render.pltz"
        with open(temp_pltz, "wb") as f:
            f.write(retrieved_bytes)

        pltz_for_render = pltz_class(temp_pltz)
        preview = pltz_for_render.render_preview()

        assert preview is not None
        assert len(preview) > 0
        # PNG files start with specific magic bytes
        assert preview[:8] == b"\x89PNG\r\n\x1a\n"


if __name__ == "__main__":
    import os

    pytest.main([os.path.abspath(__file__), "-v"])
