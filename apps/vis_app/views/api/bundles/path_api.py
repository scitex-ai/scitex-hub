"""
Path-Based Bundle API Views - Re-export module.

This module re-exports all path-based API views for backward compatibility.
The actual implementations are in:
- path_pltz.py: Pltz bundle operations
- path_figz.py: Figz bundle operations
- path_panel.py: Panel operations
"""

# Pltz path-based operations
# Figz path-based operations
from .path_figz import (
    load_figz_by_path,
    save_figz_canvas,
)

# Panel operations
from .path_panel import (
    add_panel_to_figz,
    get_figz_panel_preview,
)
from .path_pltz import (
    create_pltz_from_plot,
    get_pltz_data_by_path,
    get_pltz_geometry_by_path,
    get_pltz_preview_by_path,
    load_pltz_by_path,
    render_pltz_by_path,
    update_pltz_by_path,
)

__all__ = [
    # Pltz
    "load_pltz_by_path",
    "get_pltz_preview_by_path",
    "get_pltz_geometry_by_path",
    "get_pltz_data_by_path",
    "update_pltz_by_path",
    "render_pltz_by_path",
    "create_pltz_from_plot",
    # Figz
    "load_figz_by_path",
    "save_figz_canvas",
    # Panel
    "add_panel_to_figz",
    "get_figz_panel_preview",
]
