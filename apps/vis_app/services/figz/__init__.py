"""
FigzBundle Service - Thin Django wrapper around scitex.fig.Figz.

Supports both unified .stx format (v2.0.0) and legacy .figz format.
Migration strategy: "Save as .stx, read all formats"
"""

import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from django.conf import settings
from django.utils.text import slugify

logger = logging.getLogger(__name__)

SCITEX_CODE_PATH = os.environ.get(
    "SCITEX_CODE_PATH", "/home/ywatanabe/proj/scitex-code"
)
if SCITEX_CODE_PATH not in sys.path:
    sys.path.insert(0, f"{SCITEX_CODE_PATH}/src")


def _get_figz_class():
    """Lazy import Figz class."""
    from scitex.fig import Figz

    return Figz


def _get_bundle_module():
    """Lazy import bundle module."""
    import scitex.io.bundle as bundle

    return bundle


# Supported extensions (unified .stx + legacy)
STX_EXTENSION = ".stx"
FIGZ_EXTENSION = ".figz"
BUNDLE_EXTENSIONS = (STX_EXTENSION, FIGZ_EXTENSION)

# Constants for backward compatibility
SPEC_FILE = "spec.json"
STYLE_FILE = "style.json"
EXPORTS_DIR = "exports"
CACHE_DIR = "cache"
GEOMETRY_FILE = "geometry_px.json"
PANEL_LABELS = list("ABCDEFGH")


def get_bundle_base_path(user_id: int) -> Path:
    """Get base path for user's figz bundles."""
    return Path(settings.MEDIA_ROOT) / "vis" / "bundles" / "figz" / str(user_id)


def is_figz_bundle(path: Union[str, Path]) -> bool:
    """Check if path is a valid figz bundle (legacy, also checks .stx)."""
    return is_figure_bundle(path)


def is_figure_bundle(path: Union[str, Path]) -> bool:
    """Check if path is a valid figure bundle (.stx or .figz).

    Supports both unified .stx format and legacy .figz format.
    """
    bundle = _get_bundle_module()
    path = Path(path)

    # Check supported extensions
    if path.suffix not in BUNDLE_EXTENSIONS:
        return False

    if not path.is_file():
        return False

    try:
        with bundle.ZipBundle(path, mode="r") as zb:
            spec = zb.read_json("spec.json")
            # For .stx, verify it's a figure type
            if path.suffix == STX_EXTENSION:
                content_type = bundle.get_stx_type(spec)
                return content_type == "figure"
            return True
    except Exception:
        return False


def load_bundle(bundle_path: Union[str, Path]) -> Dict[str, Any]:
    """Load a figure bundle (.stx or .figz) using scitex.fig.Figz.

    Supports both unified .stx format and legacy .figz format.
    Returns normalized v2.0.0 spec regardless of input format.
    """
    bundle = _get_bundle_module()
    Figz = _get_figz_class()
    path = Path(bundle_path)

    if not path.exists():
        raise FileNotFoundError(f"Bundle not found: {path}")

    figz = Figz(path)

    # Determine content type
    content_type = "figure"
    if path.suffix == STX_EXTENSION:
        content_type = figz.spec.get("type", "figure")

    return {
        "path": str(path),
        "is_zip": path.suffix in BUNDLE_EXTENSIONS,
        "format": "stx" if path.suffix == STX_EXTENSION else "figz",
        "content_type": content_type,
        "bundle_id": figz.spec.get("bundle_id"),
        "spec": figz.spec,
        "style": figz.style,
        "panels": figz.panels,
    }


def save_bundle(
    spec: Dict,
    style: Dict,
    panels: Optional[Dict[str, Union[str, Path, Dict]]] = None,
    output_path: Optional[Union[str, Path]] = None,
    user_id: Optional[int] = None,
    name: Optional[str] = None,
    as_zip: bool = True,
    generate_exports: bool = True,
    use_stx: bool = False,
) -> Dict[str, Any]:
    """Save a new figure bundle using scitex.fig.Figz.

    Args:
        spec: Figure specification
        style: Figure style
        panels: Panel data (optional)
        output_path: Output path (optional, uses user_id/name if not provided)
        user_id: User ID for default path generation
        name: Figure name for default path generation
        as_zip: Save as ZIP archive (default True)
        generate_exports: Generate preview exports (default True)
        use_stx: Use unified .stx format instead of legacy .figz (default False)

    Returns:
        Dict with path, is_zip, format, and spec
    """
    Figz = _get_figz_class()
    ext = STX_EXTENSION if use_stx else FIGZ_EXTENSION

    if output_path:
        path = Path(output_path)
    elif user_id and name:
        base_path = get_bundle_base_path(user_id)
        base_path.mkdir(parents=True, exist_ok=True)
        path = base_path / f"{slugify(name)}{ext}"
    else:
        raise ValueError("Either output_path or (user_id, name) required")

    figure_name = spec.get("figure", {}).get("id", name or "Figure")
    size_mm = spec.get("size_mm")
    figz = Figz.create(path, figure_name, size_mm)
    if style:
        figz.style = style
    figz.save()

    return {
        "path": str(path),
        "is_zip": True,
        "format": "stx" if use_stx else "figz",
        "bundle_id": figz.spec.get("bundle_id"),
        "spec": figz.spec,
    }


def delete_bundle(bundle_path: Union[str, Path]) -> bool:
    """Delete a figz bundle."""
    import shutil

    path = Path(bundle_path)
    if not path.exists():
        return False
    if path.is_file():
        path.unlink()
    else:
        shutil.rmtree(path)
    return True


def add_panel(
    bundle_path: Union[str, Path], label: str, panel_source: Union[str, Path, Dict]
) -> Dict[str, Any]:
    """Add or update a panel in figz bundle."""
    Figz = _get_figz_class()
    figz = Figz(bundle_path)
    if isinstance(panel_source, (str, Path)):
        pltz_path = Path(panel_source)
        if pltz_path.exists():
            with open(pltz_path, "rb") as f:
                pltz_bytes = f.read()
        else:
            raise FileNotFoundError(f"Panel source not found: {pltz_path}")
    else:
        import tempfile

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
    Figz = _get_figz_class()
    figz = Figz(bundle_path)
    figz.remove_panel(label)
    figz.save()
    return {"label": label, "removed": True}


def get_preview_image(
    bundle_path: Union[str, Path], image_type: str = "png"
) -> Optional[bytes]:
    """Get composed figure preview image."""
    Figz = _get_figz_class()
    try:
        figz = Figz(bundle_path)
        return figz.render_preview()
    except Exception as e:
        logger.warning(f"Failed to get preview: {e}")
        return None


def get_preview_base64(
    bundle_path: Union[str, Path], image_type: str = "png"
) -> Optional[str]:
    """Get preview image as base64 data URL."""
    import base64

    data = get_preview_image(bundle_path, image_type)
    if data:
        return f"data:image/png;base64,{base64.b64encode(data).decode('utf-8')}"
    return None


def get_panel_previews(bundle_path: Union[str, Path]) -> Dict[str, Optional[str]]:
    """Get preview images for all panels as base64."""
    Figz = _get_figz_class()
    import base64
    import tempfile

    from scitex.plt import Pltz

    result = {}
    try:
        figz = Figz(bundle_path)
        for panel_id in figz.list_panel_ids():
            pltz_bytes = figz.get_panel_pltz(panel_id)
            if pltz_bytes:
                with tempfile.NamedTemporaryFile(suffix=".pltz", delete=False) as f:
                    f.write(pltz_bytes)
                    temp_path = f.name
                try:
                    pltz = Pltz(temp_path)
                    preview = pltz.get_preview() or pltz.render_preview()
                    result[panel_id] = (
                        f"data:image/png;base64,{base64.b64encode(preview).decode('utf-8')}"
                    )
                finally:
                    Path(temp_path).unlink(missing_ok=True)
    except Exception as e:
        logger.warning(f"Failed to get panel previews: {e}")
    return result


def get_layout_positions(layout: str) -> Dict[str, Dict]:
    """Get default panel positions for a layout."""
    layouts = {
        "1x1": {"A": {"x": 0, "y": 0, "width": 1, "height": 1}},
        "2x1": {
            "A": {"x": 0, "y": 0, "width": 0.5, "height": 1},
            "B": {"x": 0.5, "y": 0, "width": 0.5, "height": 1},
        },
        "1x2": {
            "A": {"x": 0, "y": 0, "width": 1, "height": 0.5},
            "B": {"x": 0, "y": 0.5, "width": 1, "height": 0.5},
        },
        "2x2": {
            "A": {"x": 0, "y": 0, "width": 0.5, "height": 0.5},
            "B": {"x": 0.5, "y": 0, "width": 0.5, "height": 0.5},
            "C": {"x": 0, "y": 0.5, "width": 0.5, "height": 0.5},
            "D": {"x": 0.5, "y": 0.5, "width": 0.5, "height": 0.5},
        },
    }
    return layouts.get(layout, layouts["1x1"])


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
    Figz = _get_figz_class()
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
        "width": canvas_size.get("width_mm", 170),
        "height": canvas_size.get("height_mm", 120),
    }

    # Pre-extract embedded panel bytes BEFORE creating new figz
    # (Figz.create overwrites the file, so we must extract first)
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

    # Create new figz (this overwrites the file)
    figz = Figz.create(bundle_path, figure_name, size_mm)

    for panel in panels:
        pltz_path = panel.get("pltz_path")
        label = panel.get("label", "A")
        position = panel.get("position")
        size = panel.get("size")

        # Check if this is an embedded panel (path contains '#')
        if pltz_path and "#" in str(pltz_path):
            embedded_label = str(pltz_path).split("#")[-1]
            # Use pre-extracted bytes
            pltz_bytes = embedded_panel_bytes.get(embedded_label)
            if pltz_bytes:
                figz.add_panel(label, pltz_bytes, position, size)
        elif pltz_path and Path(pltz_path).exists():
            # Standalone pltz file
            with open(pltz_path, "rb") as f:
                figz.add_panel(label, f.read(), position, size)

    figz.save()
    return {"path": str(bundle_path), "saved": True}


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
