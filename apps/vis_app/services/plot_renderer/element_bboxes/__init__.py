#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Element bounding box extraction for figure elements.

Used for element-level selection in the canvas editor.

Enhanced with Schema v0.3 geometry for shape-based hit testing:
- Lines: path_simplified (Douglas-Peucker simplified polyline)
- Scatter: points with hit_radius_px
- Fill/Violin: polygon (closed shape)
- Bar: rectangles
"""

from __future__ import annotations

from typing import Any

import numpy as np

from .axis_extraction import extract_axis_bboxes
from .trace_extraction import extract_trace_bboxes
from .utils import (
    GEOMETRY_V03_AVAILABLE,
    CoordinateTransformer,
    extract_axes_bbox_px,
    get_element_bbox,
)


def extract_element_bboxes(
    fig, ax, renderer, img_width: int, img_height: int
) -> dict[str, Any]:
    """Extract bounding boxes for all figure elements.

    Args:
        fig: Matplotlib figure
        ax: Matplotlib axes
        renderer: Matplotlib renderer
        img_width: Actual saved image width in pixels
        img_height: Actual saved image height in pixels

    Returns:
        Dict with element bboxes keyed by element name
    """
    from matplotlib.transforms import Bbox

    # Get figure tight bbox in inches
    fig_bbox = fig.get_tightbbox(renderer)
    tight_x0 = fig_bbox.x0
    tight_y0 = fig_bbox.y0
    tight_width = fig_bbox.width
    tight_height = fig_bbox.height

    # bbox_inches='tight' adds pad_inches around the tight bbox
    pad_inches = 0.1
    saved_width_inches = tight_width + 2 * pad_inches
    saved_height_inches = tight_height + 2 * pad_inches

    # Scale factors for converting inches to pixels
    scale_x = img_width / saved_width_inches
    scale_y = img_height / saved_height_inches

    bboxes = {}

    # Create coordinate transformer
    transformer = CoordinateTransformer(
        fig, ax, tight_x0, tight_y0, pad_inches, saved_height_inches, scale_x, scale_y
    )

    def _get_element_bbox(element, name: str) -> dict[str, Any] | None:
        """Wrapper for get_element_bbox with pre-filled params."""
        return get_element_bbox(
            element,
            name,
            fig,
            renderer,
            tight_x0,
            pad_inches,
            saved_height_inches,
            scale_x,
            scale_y,
            img_width,
            img_height,
        )

    # Get axes panel bbox
    try:
        ax_bbox = ax.get_window_extent(renderer)
        coords = transformer.bbox_to_img_coords(ax_bbox)
        bboxes["panel"] = {
            **coords,
            "label": "Panel",
            "is_panel": True,
        }
    except Exception as e:
        print(f"Error getting panel bbox: {e}")

    # Get title bbox
    if ax.title.get_text():
        result = _get_element_bbox(ax.title, "title")
        if result:
            bboxes["title"] = result

    # Get axis labels
    if ax.xaxis.label.get_text():
        result = _get_element_bbox(ax.xaxis.label, "xlabel")
        if result:
            bboxes["xlabel"] = result
    if ax.yaxis.label.get_text():
        result = _get_element_bbox(ax.yaxis.label, "ylabel")
        if result:
            bboxes["ylabel"] = result

    # Get legend bbox
    legend = ax.get_legend()
    if legend:
        result = _get_element_bbox(legend, "legend")
        if result:
            bboxes["legend"] = result

    # Get axis tick bboxes
    extract_axis_bboxes(ax, renderer, bboxes, transformer.bbox_to_img_coords, Bbox)

    # Get trace bboxes (lines, scatter, bars, etc.)
    extract_trace_bboxes(
        ax,
        fig,
        bboxes,
        _get_element_bbox,
        transformer.coords_to_img_points,
        transformer.bbox_to_img_coords,
        img_width,
        img_height,
    )

    # Add schema v0.3 axes bbox for coordinate transformation
    if GEOMETRY_V03_AVAILABLE and extract_axes_bbox_px is not None:
        try:
            axes_bbox_px = extract_axes_bbox_px(ax, fig)
            bboxes["_meta"] = {
                "schema_version": "0.3.0",
                "axes_bbox_px": axes_bbox_px,
                "coord_space": "axes",
            }
        except Exception as e:
            print(f"Error extracting axes bbox for schema v0.3: {e}")

    return bboxes


__all__ = ["extract_element_bboxes", "GEOMETRY_V03_AVAILABLE"]


# EOF
