"""Gallery Utils - Helper functions for gallery operations."""

import base64
import json
import logging
from pathlib import Path

from ...services.gallery_generator import get_gallery_path, get_template_gallery_path

logger = logging.getLogger(__name__)


def find_image_in_gallery(gallery_base, category, plot_name, ext):
    """Find image in gallery (bundle or flat format)."""
    if not gallery_base:
        return None
    bundle_path = (
        gallery_base
        / category
        / f"{plot_name}.pltz.d"
        / "exports"
        / f"{plot_name}.{ext}"
    )
    if bundle_path.exists():
        return bundle_path
    flat_path = gallery_base / category / f"{plot_name}.{ext}"
    return flat_path if flat_path.exists() else None


def find_png_path(project, category, plot_name):
    """Find PNG path checking multiple locations."""
    if project:
        gallery_path = get_gallery_path(project.get_local_path())
        png_path = find_image_in_gallery(gallery_path, category, plot_name, "png")
        if png_path:
            return png_path

    temp_gallery = Path("/tmp/scitex_gallery_with_bboxes")
    png_path = find_image_in_gallery(temp_gallery, category, plot_name, "png")
    if png_path:
        return png_path

    return find_image_in_gallery(
        get_template_gallery_path(), category, plot_name, "png"
    )


def add_metadata_to_result(result, png_path):
    """Add metadata from companion JSON to result."""
    json_path = png_path.parent.parent / "spec.json"
    if not json_path.exists():
        json_path = png_path.with_suffix(".json")
    if not json_path.exists():
        return

    try:
        with open(json_path, "r") as f:
            metadata = json.load(f)
        if "axes_bbox_px" in metadata:
            result["axes_bbox_px"] = metadata["axes_bbox_px"]
        if "element_bboxes" in metadata:
            result["element_bboxes"] = metadata["element_bboxes"]
        if "dimensions" in metadata and "figure_size_px" in metadata["dimensions"]:
            result["figure_size_px"] = metadata["dimensions"]["figure_size_px"]
        if "hitmap_color_map" in metadata:
            result["hitmap_color_map"] = metadata["hitmap_color_map"]
        if "hitmap_file" in metadata:
            hitmap_path = png_path.parent / metadata["hitmap_file"]
            if hitmap_path.exists():
                with open(hitmap_path, "rb") as f:
                    hitmap_data = f.read()
                result["hitmap"] = (
                    f"data:image/png;base64,{base64.b64encode(hitmap_data).decode('utf-8')}"
                )
    except Exception as e:
        logger.warning(f"Failed to load metadata: {e}")
