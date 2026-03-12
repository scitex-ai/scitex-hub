#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Axis bounding box extraction functions."""

from __future__ import annotations

from typing import Any


def extract_axis_bboxes(
    ax, renderer, bboxes: dict[str, Any], bbox_to_img_coords, Bbox
) -> None:
    """Extract bboxes for X and Y axis elements."""
    try:
        # X-axis: combine spine and tick labels
        x_axis_bboxes = []
        for ticklabel in ax.xaxis.get_ticklabels():
            if ticklabel.get_visible():
                try:
                    tb = ticklabel.get_window_extent(renderer)
                    if tb.width > 0:
                        x_axis_bboxes.append(tb)
                except Exception:
                    pass
        for tick in ax.xaxis.get_major_ticks():
            if tick.tick1line.get_visible():
                try:
                    tb = tick.tick1line.get_window_extent(renderer)
                    if tb.width > 0 or tb.height > 0:
                        x_axis_bboxes.append(tb)
                except Exception:
                    pass
        spine_bbox = ax.spines["bottom"].get_window_extent(renderer)
        if spine_bbox.width > 0:
            if x_axis_bboxes:
                tick_union = Bbox.union(x_axis_bboxes)
                constrained_spine = Bbox.from_extents(
                    tick_union.x0, spine_bbox.y0, tick_union.x1, spine_bbox.y1
                )
                x_axis_bboxes.append(constrained_spine)
            else:
                x_axis_bboxes.append(spine_bbox)
        if x_axis_bboxes:
            combined = Bbox.union(x_axis_bboxes)
            bboxes["xaxis_ticks"] = bbox_to_img_coords(combined)
            bboxes["xaxis_ticks"]["label"] = "X Spine & Ticks"

        # Y-axis: combine spine and tick labels
        y_axis_bboxes = []
        for ticklabel in ax.yaxis.get_ticklabels():
            if ticklabel.get_visible():
                try:
                    tb = ticklabel.get_window_extent(renderer)
                    if tb.width > 0:
                        y_axis_bboxes.append(tb)
                except Exception:
                    pass
        for tick in ax.yaxis.get_major_ticks():
            if tick.tick1line.get_visible():
                try:
                    tb = tick.tick1line.get_window_extent(renderer)
                    if tb.width > 0 or tb.height > 0:
                        y_axis_bboxes.append(tb)
                except Exception:
                    pass
        spine_bbox = ax.spines["left"].get_window_extent(renderer)
        if spine_bbox.height > 0:
            if y_axis_bboxes:
                tick_union = Bbox.union(y_axis_bboxes)
                constrained_spine = Bbox.from_extents(
                    spine_bbox.x0, tick_union.y0, spine_bbox.x1, tick_union.y1
                )
                y_axis_bboxes.append(constrained_spine)
            else:
                y_axis_bboxes.append(spine_bbox)
        if y_axis_bboxes:
            combined = Bbox.union(y_axis_bboxes)
            padded = Bbox.from_extents(
                combined.x0 - 10, combined.y0 - 5, combined.x1 + 5, combined.y1 + 5
            )
            bboxes["yaxis_ticks"] = bbox_to_img_coords(padded)
            bboxes["yaxis_ticks"]["label"] = "Y Spine & Ticks"

    except Exception as e:
        print(f"Error getting axis bboxes: {e}")


# EOF
