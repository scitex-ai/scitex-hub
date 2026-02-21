#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Canvas save operations for FigzBundle."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from .bundle_ops import get_bundle_base_path


def save_canvas_as_bundle(
    project_owner: Optional[str],
    project_slug: Optional[str],
    figure_name: str,
    panels: List[Dict],
    canvas_size: Dict,
    theme: str = "light",
    user: Optional[Any] = None,
) -> Dict[str, Any]:
    """Auto-save canvas state as a figz bundle.

    For embedded panels (pltz_path contains '#'), preserves the existing pltz bytes.
    Only updates panel positions and sizes.
    """
    import figrecipe

    if project_owner and project_slug:
        from apps.project_app.models import Project

        project = Project.objects.get(owner__username=project_owner, slug=project_slug)
        figures_dir = project.get_local_path() / "scitex" / "vis" / "figures"
        figures_dir.mkdir(parents=True, exist_ok=True)
        bundle_path = figures_dir / f"{figure_name}.figz"
    elif user:
        bundle_path = get_bundle_base_path(user.id) / f"{figure_name}.figz"
    else:
        raise ValueError("project info or user required")

    size_mm = {
        "width_mm": canvas_size.get("width_mm", 170),
        "height_mm": canvas_size.get("height_mm", 120),
    }

    # Pre-extract embedded panel bytes BEFORE creating new figz
    embedded_panel_bytes = _extract_embedded_panels(bundle_path, panels, figrecipe.Figz)

    # Create new figz (this overwrites the file)
    figz = figrecipe.Figz.create(bundle_path, figure_name, size_mm)

    for panel in panels:
        _add_panel_to_figz(figz, panel, embedded_panel_bytes)

    return {"path": str(bundle_path), "saved": True}


def _extract_embedded_panels(
    bundle_path: Path, panels: List[Dict], Figz
) -> Dict[str, bytes]:
    """Extract embedded panel bytes from existing bundle."""
    embedded_panel_bytes = {}
    if bundle_path.exists():
        try:
            existing_figz = Figz(bundle_path)
            for panel in panels:
                pltz_path = panel.get("pltz_path")
                if pltz_path and "#" in str(pltz_path):
                    embedded_label = str(pltz_path).split("#")[-1]
                    pltz_bytes = existing_figz.get_panel_pltz(embedded_label)
                    if pltz_bytes:
                        embedded_panel_bytes[embedded_label] = pltz_bytes
        except Exception:
            pass
    return embedded_panel_bytes


def _add_panel_to_figz(
    figz, panel: Dict, embedded_panel_bytes: Dict[str, bytes]
) -> None:
    """Add a single panel to the figz bundle."""
    pltz_path = panel.get("pltz_path")
    label = panel.get("label", "A")
    position = panel.get("position")
    size = panel.get("size")

    if pltz_path and "#" in str(pltz_path):
        # Embedded panel - use pre-extracted bytes
        embedded_label = str(pltz_path).split("#")[-1]
        pltz_bytes = embedded_panel_bytes.get(embedded_label)
        if pltz_bytes:
            figz.add_panel(label, pltz_bytes, position, size)
    elif pltz_path and Path(pltz_path).exists():
        # Standalone pltz file
        figz.add_panel(label, Path(pltz_path).read_bytes(), position, size)


# EOF
