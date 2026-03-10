"""
FigzBundle Service - Thin Django wrapper around scitex.fig.Figz.

Supports both unified .stx format (v2.0.0) and legacy .figz format.
Migration strategy: "Save as .stx, read all formats"
"""

from .bundle_ops import (
    delete_bundle,
    get_bundle_base_path,
    is_figure_bundle,
    is_figz_bundle,
    load_bundle,
    save_bundle,
)
from .canvas import save_canvas_as_bundle
from .constants import (
    BUNDLE_EXTENSIONS,
    CACHE_DIR,
    EXPORTS_DIR,
    FIGZ_EXTENSION,
    GEOMETRY_FILE,
    PANEL_LABELS,
    SPEC_FILE,
    STX_EXTENSION,
    STYLE_FILE,
)
from .layout import get_layout_positions
from .panel_ops import add_panel, remove_panel
from .preview import get_panel_previews, get_preview_base64, get_preview_image


class FigzService:
    """Service class for figure bundle operations.

    Supports both unified .stx format (v2.0.0) and legacy .figz format.
    """

    # Extensions
    STX_EXTENSION = STX_EXTENSION
    FIGZ_EXTENSION = FIGZ_EXTENSION
    BUNDLE_EXTENSIONS = BUNDLE_EXTENSIONS

    # Constants
    SPEC_FILE, STYLE_FILE, EXPORTS_DIR = SPEC_FILE, STYLE_FILE, EXPORTS_DIR
    CACHE_DIR, GEOMETRY_FILE, PANEL_LABELS = CACHE_DIR, GEOMETRY_FILE, PANEL_LABELS

    # Static methods
    get_bundle_base_path = staticmethod(get_bundle_base_path)
    is_figz_bundle = staticmethod(is_figz_bundle)
    is_figure_bundle = staticmethod(is_figure_bundle)
    load_bundle = staticmethod(load_bundle)
    save_bundle = staticmethod(save_bundle)
    delete_bundle = staticmethod(delete_bundle)
    add_panel = staticmethod(add_panel)
    remove_panel = staticmethod(remove_panel)
    get_preview_image = staticmethod(get_preview_image)
    get_preview_base64 = staticmethod(get_preview_base64)
    get_panel_previews = staticmethod(get_panel_previews)
    get_layout_positions = staticmethod(get_layout_positions)
    save_canvas_as_bundle = staticmethod(save_canvas_as_bundle)


__all__ = [
    # Service class
    "FigzService",
    # Extensions
    "STX_EXTENSION",
    "FIGZ_EXTENSION",
    "BUNDLE_EXTENSIONS",
    # Constants
    "SPEC_FILE",
    "STYLE_FILE",
    "EXPORTS_DIR",
    "CACHE_DIR",
    "GEOMETRY_FILE",
    "PANEL_LABELS",
    # Functions
    "get_bundle_base_path",
    "is_figz_bundle",
    "is_figure_bundle",
    "load_bundle",
    "save_bundle",
    "delete_bundle",
    "add_panel",
    "remove_panel",
    "get_preview_image",
    "get_preview_base64",
    "get_panel_previews",
    "get_layout_positions",
    "save_canvas_as_bundle",
]
