"""Plots Metadata - Metadata extraction from images."""

import base64
import os
from typing import Dict


def extract_image_metadata_from_base64(image_data: str) -> Dict:
    """Extract scitex metadata from base64 image data."""
    import json as json_module
    import tempfile

    if image_data.startswith("data:"):
        try:
            image_data = image_data.split(",", 1)[1]
        except IndexError:
            raise ValueError("Invalid data URL format")

    try:
        image_bytes = base64.b64decode(image_data)
    except Exception as e:
        raise ValueError(f"Invalid base64 data: {e}")

    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        tmp.write(image_bytes)
        tmp_path = tmp.name

    try:
        metadata = None
        try:
            from scitex.io._metadata import read_metadata

            metadata = read_metadata(tmp_path)
        except ImportError:
            from PIL import Image

            img = Image.open(tmp_path)
            if hasattr(img, "info") and "scitex_metadata" in img.info:
                try:
                    metadata = json_module.loads(img.info["scitex_metadata"])
                except:
                    pass
            img.close()

        if not metadata:
            return {
                "success": True,
                "has_metadata": False,
                "message": "No scitex metadata found in image",
            }

        result = extract_metadata_fields(metadata)
        result["success"] = True
        result["has_metadata"] = True
        result["metadata"] = metadata
        return result

    finally:
        try:
            os.unlink(tmp_path)
        except:
            pass


def extract_metadata_fields(metadata: Dict) -> Dict:
    """Extract axes_bbox_px and figure_size_px from metadata."""
    axes_bbox_px = None
    figure_size_px = None

    if "axes" in metadata and len(metadata["axes"]) > 0:
        ax_meta = metadata["axes"][0]
        if "bbox_px" in ax_meta:
            bbox = ax_meta["bbox_px"]
            axes_bbox_px = {
                "x0": bbox.get("x_left", 0),
                "y0": bbox.get("y_top", 0),
                "x1": bbox.get("x_right", 0),
                "y1": bbox.get("y_bottom", 0),
                "width": bbox.get("width", 0),
                "height": bbox.get("height", 0),
            }

    if "dimensions" in metadata:
        dims = metadata["dimensions"]
        if "figure_size_px" in dims:
            size = dims["figure_size_px"]
            if isinstance(size, list):
                figure_size_px = {"width": size[0], "height": size[1]}
            else:
                figure_size_px = size

    if not axes_bbox_px and "axes_bbox_px" in metadata:
        axes_bbox_px = metadata["axes_bbox_px"]

    return {"axes_bbox_px": axes_bbox_px, "figure_size_px": figure_size_px}
