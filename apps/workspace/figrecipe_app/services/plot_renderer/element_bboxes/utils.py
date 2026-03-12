#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Utility functions for element bounding box extraction."""

from __future__ import annotations

from typing import Any

import numpy as np

# Try to import schema v0.3 geometry extraction (from scitex package)
try:
    import sys

    sys.path.insert(0, "/home/ywatanabe/proj/scitex-code/src")
    from scitex.plt.utils.metadata._geometry_extraction import (
        _simplify_path,
        data_to_axes_px,
        extract_axes_bbox_px,
        extract_bar_group_geometry,
        extract_line_geometry,
        extract_polygon_geometry,
        extract_scatter_geometry,
    )

    GEOMETRY_V03_AVAILABLE = True
except ImportError:
    GEOMETRY_V03_AVAILABLE = False
    extract_axes_bbox_px = None
    extract_line_geometry = None
    extract_scatter_geometry = None
    extract_polygon_geometry = None


class CoordinateTransformer:
    """Helper class for coordinate transformations."""

    def __init__(
        self,
        fig,
        ax,
        tight_x0: float,
        tight_y0: float,
        pad_inches: float,
        saved_height_inches: float,
        scale_x: float,
        scale_y: float,
    ):
        self.fig = fig
        self.ax = ax
        self.tight_x0 = tight_x0
        self.tight_y0 = tight_y0
        self.pad_inches = pad_inches
        self.saved_height_inches = saved_height_inches
        self.scale_x = scale_x
        self.scale_y = scale_y

    def coords_to_img_points(
        self, data_coords: list[tuple[float, float]]
    ) -> list[list[int]]:
        """Convert data coordinates to image pixel coordinates."""
        if len(data_coords) == 0:
            return []
        transform = self.ax.transData
        points_display = transform.transform(data_coords)
        points_img = []
        for px, py in points_display:
            if not np.isfinite(px) or not np.isfinite(py):
                continue
            px_inches = px / self.fig.dpi
            py_inches = py / self.fig.dpi
            x_rel = px_inches - self.tight_x0 + self.pad_inches
            y_rel = self.saved_height_inches - (
                py_inches - self.tight_y0 + self.pad_inches
            )
            x_img = max(-10000, min(10000, int(x_rel * self.scale_x)))
            y_img = max(-10000, min(10000, int(y_rel * self.scale_y)))
            points_img.append([x_img, y_img])
        # Downsample if too many
        if len(points_img) > 100:
            step = len(points_img) // 100
            points_img = points_img[::step]
        return points_img

    def bbox_to_img_coords(self, bbox) -> dict[str, int]:
        """Convert matplotlib bbox to image pixel coordinates."""
        x0_inches = bbox.x0 / self.fig.dpi
        y0_inches = bbox.y0 / self.fig.dpi
        x1_inches = bbox.x1 / self.fig.dpi
        y1_inches = bbox.y1 / self.fig.dpi
        x0_rel = x0_inches - self.tight_x0 + self.pad_inches
        y0_rel = y0_inches - self.tight_y0 + self.pad_inches
        x1_rel = x1_inches - self.tight_x0 + self.pad_inches
        y1_rel = y1_inches - self.tight_y0 + self.pad_inches
        return {
            "x0": int(x0_rel * self.scale_x),
            "y0": int((self.saved_height_inches - y1_rel) * self.scale_y),
            "x1": int(x1_rel * self.scale_x),
            "y1": int((self.saved_height_inches - y0_rel) * self.scale_y),
        }


def get_element_bbox(
    element,
    name: str,
    fig,
    renderer,
    tight_x0: float,
    pad_inches: float,
    saved_height_inches: float,
    scale_x: float,
    scale_y: float,
    img_width: int,
    img_height: int,
) -> dict[str, Any] | None:
    """Get element bbox in image pixel coordinates."""
    try:
        bbox = element.get_window_extent(renderer)

        # Check for invalid bbox
        if not (
            np.isfinite(bbox.x0)
            and np.isfinite(bbox.x1)
            and np.isfinite(bbox.y0)
            and np.isfinite(bbox.y1)
        ):
            return None

        elem_x0_inches = bbox.x0 / fig.dpi
        elem_x1_inches = bbox.x1 / fig.dpi
        elem_y0_inches = bbox.y0 / fig.dpi
        elem_y1_inches = bbox.y1 / fig.dpi

        x0_rel = elem_x0_inches - tight_x0 + pad_inches
        x1_rel = elem_x1_inches - tight_x0 + pad_inches
        y0_rel = saved_height_inches - (elem_y1_inches - tight_x0 + pad_inches)
        y1_rel = saved_height_inches - (elem_y0_inches - tight_x0 + pad_inches)

        return {
            "x0": max(0, int(x0_rel * scale_x)),
            "y0": max(0, int(y0_rel * scale_y)),
            "x1": min(img_width, int(x1_rel * scale_x)),
            "y1": min(img_height, int(y1_rel * scale_y)),
            "label": name.replace("_", " ").title(),
        }
    except Exception as e:
        print(f"Error getting bbox for {name}: {e}")
        return None


# EOF
