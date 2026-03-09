#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Panel operations for FigzBundle."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Union


def add_panel(
    bundle_path: Union[str, Path], label: str, panel_source: Union[str, Path, Dict]
) -> Dict[str, Any]:
    """Add or update a panel in figz bundle."""
    import figrecipe

    figz = figrecipe.Figz(bundle_path)

    if isinstance(panel_source, (str, Path)):
        pltz_path = Path(panel_source)
        if pltz_path.exists():
            pltz_bytes = pltz_path.read_bytes()
        else:
            raise FileNotFoundError(f"Panel source not found: {pltz_path}")
    else:
        raise ValueError(
            "panel_source must be a path to a .plt.zip file. "
            "Creating panels from spec dicts is not supported."
        )

    figz.add_panel(label, pltz_bytes)
    return {"label": label, "added": True}


def remove_panel(bundle_path: Union[str, Path], label: str) -> Dict[str, Any]:
    """Remove a panel from figz bundle."""
    import figrecipe

    figz = figrecipe.Figz(bundle_path)
    figz.remove_panel(label)
    return {"label": label, "removed": True}


# EOF
