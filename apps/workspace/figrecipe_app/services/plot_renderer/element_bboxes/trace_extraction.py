#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Trace/data element bounding box extraction functions."""

from __future__ import annotations

from typing import Any, Callable

from .utils import (
    GEOMETRY_V03_AVAILABLE,
    extract_line_geometry,
    extract_polygon_geometry,
    extract_scatter_geometry,
)


def extract_trace_bboxes(
    ax,
    fig,
    bboxes: dict[str, Any],
    get_element_bbox: Callable,
    coords_to_img_points: Callable,
    bbox_to_img_coords: Callable,
    img_width: int,
    img_height: int,
) -> None:
    """Extract bboxes for all data elements (lines, scatter, bars, etc.)."""
    from matplotlib.transforms import Bbox

    # 1. Extract lines (separate user lines from boxplot lines)
    line_idx = 0
    boxplot_lines = []  # Collect boxplot lines for grouping

    for line in ax.get_lines():
        try:
            label = line.get_label()

            # Check if this is a boxplot line (starts with _child or _nolegend_)
            if label.startswith("_child") or label == "_nolegend_":
                boxplot_lines.append(line)
                continue

            # Skip other underscore-prefixed labels
            if label.startswith("_"):
                continue

            trace_name = f"trace_{line_idx}"
            bbox_result = get_element_bbox(line, trace_name)
            if bbox_result:
                bboxes[trace_name] = bbox_result
                bboxes[trace_name]["label"] = label or f"Line {line_idx}"
                bboxes[trace_name]["trace_idx"] = line_idx
                bboxes[trace_name]["element_type"] = "line"

                xdata, ydata = line.get_xdata(), line.get_ydata()
                if len(xdata) > 0:
                    bboxes[trace_name]["points"] = coords_to_img_points(
                        list(zip(xdata, ydata))
                    )

                    # Add schema v0.3 geometry
                    if GEOMETRY_V03_AVAILABLE:
                        try:
                            geom = extract_line_geometry(
                                line, ax, fig, simplify_threshold=0.5
                            )
                            bboxes[trace_name]["geometry_px"] = geom
                        except Exception:
                            pass
            line_idx += 1
        except Exception as e:
            print(f"Error getting line bbox: {e}")

    # 1b. Group boxplot lines into box elements by x-position
    if boxplot_lines:
        _extract_boxplot_bboxes(ax, boxplot_lines, bboxes, bbox_to_img_coords, Bbox)

    # 2. Extract collections (scatter, fill_between, violin, etc.)
    _extract_collections(
        ax,
        fig,
        bboxes,
        get_element_bbox,
        coords_to_img_points,
        img_width,
        img_height,
    )

    # 3. Extract patches (bars, rectangles, etc.)
    _extract_patches(ax, bboxes, get_element_bbox)


def _extract_collections(
    ax,
    fig,
    bboxes: dict[str, Any],
    get_element_bbox: Callable,
    coords_to_img_points: Callable,
    img_width: int,
    img_height: int,
) -> None:
    """Extract bboxes for matplotlib collections (scatter, fill, violin)."""
    scatter_idx = 0
    fill_idx = 0
    violin_idx = 0

    for coll in ax.collections:
        try:
            label = coll.get_label()
            is_internal = label.startswith("_") if label else False
            if is_internal:
                label = None

            coll_type = type(coll).__name__
            if coll_type == "PathCollection":
                # Scatter points
                element_name = f"scatter_{scatter_idx}"
                offsets = coll.get_offsets()

                if len(offsets) > 0:
                    points_img = coords_to_img_points(offsets)
                    if points_img:
                        xs = [p[0] for p in points_img]
                        ys = [p[1] for p in points_img]
                        padding = 10
                        bboxes[element_name] = {
                            "x0": max(0, min(xs) - padding),
                            "y0": max(0, min(ys) - padding),
                            "x1": min(img_width, max(xs) + padding),
                            "y1": min(img_height, max(ys) + padding),
                            "label": label or f"Scatter {scatter_idx}",
                            "element_type": "scatter",
                            "points": points_img,
                        }

                        if GEOMETRY_V03_AVAILABLE:
                            try:
                                geom = extract_scatter_geometry(coll, ax, fig)
                                bboxes[element_name]["geometry_px"] = geom
                            except Exception:
                                pass
                scatter_idx += 1

            elif coll_type == "FillBetweenPolyCollection":
                element_name = f"violin_{violin_idx}"
                bbox_result = get_element_bbox(coll, element_name)
                if bbox_result:
                    bboxes[element_name] = bbox_result
                    bboxes[element_name]["label"] = f"Violin {violin_idx + 1}"
                    bboxes[element_name]["element_type"] = "violin"

                    if GEOMETRY_V03_AVAILABLE:
                        try:
                            geom = extract_polygon_geometry(coll, ax, fig)
                            bboxes[element_name]["geometry_px"] = geom
                        except Exception:
                            pass
                violin_idx += 1

            elif coll_type == "PolyCollection":
                element_name = f"fill_{fill_idx}"
                bbox_result = get_element_bbox(coll, element_name)
                if bbox_result:
                    bboxes[element_name] = bbox_result
                    bboxes[element_name]["label"] = label or f"Fill {fill_idx}"
                    bboxes[element_name]["element_type"] = "fill"

                    if GEOMETRY_V03_AVAILABLE:
                        try:
                            geom = extract_polygon_geometry(coll, ax, fig)
                            bboxes[element_name]["geometry_px"] = geom
                        except Exception:
                            pass
                fill_idx += 1

        except Exception as e:
            print(f"Error getting collection bbox: {e}")


def _extract_patches(ax, bboxes: dict[str, Any], get_element_bbox: Callable) -> None:
    """Extract bboxes for matplotlib patches (bars, rectangles)."""
    patch_idx = 0
    for patch in ax.patches:
        try:
            label = patch.get_label()
            patch_type = type(patch).__name__

            if patch_type == "Rectangle":
                element_name = f"bar_{patch_idx}"
                bbox_result = get_element_bbox(patch, element_name)
                if bbox_result:
                    bboxes[element_name] = bbox_result
                    bboxes[element_name]["label"] = label or f"Bar {patch_idx}"
                    bboxes[element_name]["element_type"] = "bar"

            patch_idx += 1
        except Exception as e:
            print(f"Error getting patch bbox: {e}")


def _extract_boxplot_bboxes(
    ax, boxplot_lines, bboxes: dict[str, Any], bbox_to_img_coords, Bbox
) -> None:
    """Extract bboxes for boxplot elements by grouping lines by x-position."""
    import numpy as np

    # Group lines by their x center position
    x_groups = {}
    for line in boxplot_lines:
        try:
            xdata = line.get_xdata()
            if len(xdata) == 0:
                continue
            x_center = round(np.mean(xdata), 2)
            if x_center not in x_groups:
                x_groups[x_center] = []
            x_groups[x_center].append(line)
        except Exception:
            pass

    # Create a bbox for each box group
    renderer = ax.figure.canvas.get_renderer()
    sorted_positions = sorted(x_groups.keys())

    for idx, x_pos in enumerate(sorted_positions):
        lines = x_groups[x_pos]
        if not lines:
            continue

        try:
            line_bboxes = []
            for line in lines:
                try:
                    lb = line.get_window_extent(renderer)
                    if lb.width > 0 or lb.height > 0:
                        line_bboxes.append(lb)
                except Exception:
                    pass

            if line_bboxes:
                combined = Bbox.union(line_bboxes)
                element_name = f"boxplot_{idx}"
                coords = bbox_to_img_coords(combined)
                bboxes[element_name] = {
                    **coords,
                    "label": f"Box {idx + 1}",
                    "element_type": "boxplot",
                }
        except Exception as e:
            print(f"Error extracting boxplot bbox: {e}")


# EOF
