#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Panel operations for FigzBundle."""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any, Dict, Union

from .constants import get_figz_class


def add_panel(
    bundle_path: Union[str, Path], label: str, panel_source: Union[str, Path, Dict]
) -> Dict[str, Any]:
    """Add or update a panel in figz bundle."""
    Figz = get_figz_class()
    figz = Figz(bundle_path)

    if isinstance(panel_source, (str, Path)):
        pltz_path = Path(panel_source)
        if pltz_path.exists():
            with open(pltz_path, "rb") as f:
                pltz_bytes = f.read()
        else:
            raise FileNotFoundError(f"Panel source not found: {pltz_path}")
    else:
        from scitex.plt import Pltz

        with tempfile.NamedTemporaryFile(suffix=".pltz", delete=False) as f:
            temp_path = f.name
        pltz = Pltz.create(temp_path, plot_type=panel_source.get("plot_type", "line"))
        with open(temp_path, "rb") as f:
            pltz_bytes = f.read()
        Path(temp_path).unlink()

    figz.add_panel(label, pltz_bytes)
    return {"label": label, "added": True}


def remove_panel(bundle_path: Union[str, Path], label: str) -> Dict[str, Any]:
    """Remove a panel from figz bundle."""
    Figz = get_figz_class()
    figz = Figz(bundle_path)
    figz.remove_panel(label)
    figz.save()
    return {"label": label, "removed": True}


# EOF
