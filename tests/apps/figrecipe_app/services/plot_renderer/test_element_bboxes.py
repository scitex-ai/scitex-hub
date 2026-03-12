#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for apps/figrecipe_app/services/plot_renderer/element_bboxes.py"""

import pytest

# from apps.workspace.figrecipe_app.services.plot_renderer.element_bboxes import ...


class TestPlaceholder:
    """Placeholder test class - replace with actual tests."""

    def test_placeholder(self):
        """Placeholder test - implement actual tests."""
        pytest.skip("Not implemented yet")


if __name__ == "__main__":
    import os

    import pytest

    pytest.main([os.path.abspath(__file__)])

# --------------------------------------------------------------------------------
# Start of Source Code from: apps/figrecipe_app/services/plot_renderer/element_bboxes.py
# --------------------------------------------------------------------------------
# #!/usr/bin/env python3
# # -*- coding: utf-8 -*-
# """
# Element bounding box extraction for figure elements.
# Used for element-level selection in the canvas editor.
#
# Enhanced with Schema v0.3 geometry for shape-based hit testing:
# - Lines: path_simplified (Douglas-Peucker simplified polyline)
# - Scatter: points with hit_radius_px
# - Fill/Violin: polygon (closed shape)
# - Bar: rectangles
# """
#
# import numpy as np
# from typing import Dict, Any, List, Tuple
#
# # Try to import schema v0.3 geometry extraction (from scitex package)
# try:
#     import sys
#     sys.path.insert(0, '/home/ywatanabe/proj/scitex-code/src')
#     from scitex.plt.utils.metadata._geometry_extraction import (
#         extract_axes_bbox_px,
#         data_to_axes_px,
#         extract_line_geometry,
#         extract_scatter_geometry,
#         extract_polygon_geometry,
#         extract_bar_group_geometry,
#         _simplify_path,
#     )
#     GEOMETRY_V03_AVAILABLE = True
# except ImportError:
#     GEOMETRY_V03_AVAILABLE = False
#
#
# def extract_element_bboxes(
#     fig, ax, renderer, img_width: int, img_height: int
# ) -> Dict[str, Any]:
#     """Extract bounding boxes for all figure elements.
#
#     Args:
#         fig: Matplotlib figure
#         ax: Matplotlib axes
#         renderer: Matplotlib renderer
#         img_width: Actual saved image width in pixels
#         img_height: Actual saved image height in pixels
#
#     Returns:
#         Dict with element bboxes keyed by element name
#     """
#     from matplotlib.transforms import Bbox
#
#     # Get figure tight bbox in inches
#     fig_bbox = fig.get_tightbbox(renderer)
#     tight_x0 = fig_bbox.x0
#     tight_y0 = fig_bbox.y0
#     tight_width = fig_bbox.width
#     tight_height = fig_bbox.height
#
#     # bbox_inches='tight' adds pad_inches around the tight bbox
#     pad_inches = 0.1
#     saved_width_inches = tight_width + 2 * pad_inches
#     saved_height_inches = tight_height + 2 * pad_inches
#
#     # Scale factors for converting inches to pixels
#     scale_x = img_width / saved_width_inches
#     scale_y = img_height / saved_height_inches
#
#     bboxes = {}
#
#     def get_element_bbox(element, name: str) -> None:
#         """Get element bbox in image pixel coordinates."""
#         try:
#             bbox = element.get_window_extent(renderer)
#
#             # Check for invalid bbox
#             if not (np.isfinite(bbox.x0) and np.isfinite(bbox.x1) and
#                     np.isfinite(bbox.y0) and np.isfinite(bbox.y1)):
#                 return
#
#             elem_x0_inches = bbox.x0 / fig.dpi
#             elem_x1_inches = bbox.x1 / fig.dpi
#             elem_y0_inches = bbox.y0 / fig.dpi
#             elem_y1_inches = bbox.y1 / fig.dpi
#
#             x0_rel = elem_x0_inches - tight_x0 + pad_inches
#             x1_rel = elem_x1_inches - tight_x0 + pad_inches
#             y0_rel = saved_height_inches - (elem_y1_inches - tight_y0 + pad_inches)
#             y1_rel = saved_height_inches - (elem_y0_inches - tight_y0 + pad_inches)
#
#             bboxes[name] = {
#                 "x0": max(0, int(x0_rel * scale_x)),
#                 "y0": max(0, int(y0_rel * scale_y)),
#                 "x1": min(img_width, int(x1_rel * scale_x)),
#                 "y1": min(img_height, int(y1_rel * scale_y)),
#                 "label": name.replace("_", " ").title(),
#             }
#         except Exception as e:
#             print(f"Error getting bbox for {name}: {e}")
#
#     def coords_to_img_points(data_coords: List[Tuple[float, float]]) -> List[List[int]]:
#         """Convert data coordinates to image pixel coordinates."""
#         if len(data_coords) == 0:
#             return []
#         transform = ax.transData
#         points_display = transform.transform(data_coords)
#         points_img = []
#         for px, py in points_display:
#             if not np.isfinite(px) or not np.isfinite(py):
#                 continue
#             px_inches = px / fig.dpi
#             py_inches = py / fig.dpi
#             x_rel = px_inches - tight_x0 + pad_inches
#             y_rel = saved_height_inches - (py_inches - tight_y0 + pad_inches)
#             x_img = max(-10000, min(10000, int(x_rel * scale_x)))
#             y_img = max(-10000, min(10000, int(y_rel * scale_y)))
#             points_img.append([x_img, y_img])
#         # Downsample if too many
#         if len(points_img) > 100:
#             step = len(points_img) // 100
#             points_img = points_img[::step]
#         return points_img
#
#     def bbox_to_img_coords(bbox) -> Dict[str, int]:
#         """Convert matplotlib bbox to image pixel coordinates."""
#         x0_inches = bbox.x0 / fig.dpi
#         y0_inches = bbox.y0 / fig.dpi
#         x1_inches = bbox.x1 / fig.dpi
#         y1_inches = bbox.y1 / fig.dpi
#         x0_rel = x0_inches - tight_x0 + pad_inches
#         y0_rel = y0_inches - tight_y0 + pad_inches
#         x1_rel = x1_inches - tight_x0 + pad_inches
#         y1_rel = y1_inches - tight_y0 + pad_inches
#         return {
#             "x0": int(x0_rel * scale_x),
#             "y0": int((saved_height_inches - y1_rel) * scale_y),
#             "x1": int(x1_rel * scale_x),
#             "y1": int((saved_height_inches - y0_rel) * scale_y),
#         }
#
#     # Get axes panel bbox
#     try:
#         ax_bbox = ax.get_window_extent(renderer)
#         coords = bbox_to_img_coords(ax_bbox)
#         bboxes["panel"] = {
#             **coords,
#             "label": "Panel",
#             "is_panel": True,
#         }
#     except Exception as e:
#         print(f"Error getting panel bbox: {e}")
#
#     # Get title bbox
#     if ax.title.get_text():
#         get_element_bbox(ax.title, "title")
#
#     # Get axis labels
#     if ax.xaxis.label.get_text():
#         get_element_bbox(ax.xaxis.label, "xlabel")
#     if ax.yaxis.label.get_text():
#         get_element_bbox(ax.yaxis.label, "ylabel")
#
#     # Get legend bbox
#     legend = ax.get_legend()
#     if legend:
#         get_element_bbox(legend, "legend")
#
#     # Get axis tick bboxes
#     _extract_axis_bboxes(ax, renderer, bboxes, bbox_to_img_coords, Bbox)
#
#     # Get trace bboxes (lines, scatter, bars, etc.)
#     _extract_trace_bboxes(ax, fig, bboxes, get_element_bbox, coords_to_img_points, bbox_to_img_coords, img_width, img_height)
#
#     # Add schema v0.3 axes bbox for coordinate transformation (axes-local pixels)
#     if GEOMETRY_V03_AVAILABLE:
#         try:
#             axes_bbox_px = extract_axes_bbox_px(ax, fig)
#             bboxes["_meta"] = {
#                 "schema_version": "0.3.0",
#                 "axes_bbox_px": axes_bbox_px,
#                 "coord_space": "axes",  # geometry uses axes-local pixels
#             }
#         except Exception as e:
#             print(f"Error extracting axes bbox for schema v0.3: {e}")
#
#     return bboxes
#
#
# def _extract_axis_bboxes(ax, renderer, bboxes, bbox_to_img_coords, Bbox):
#     """Extract bboxes for X and Y axis elements."""
#     try:
#         # X-axis: combine spine and tick labels
#         x_axis_bboxes = []
#         for ticklabel in ax.xaxis.get_ticklabels():
#             if ticklabel.get_visible():
#                 try:
#                     tb = ticklabel.get_window_extent(renderer)
#                     if tb.width > 0:
#                         x_axis_bboxes.append(tb)
#                 except Exception:
#                     pass
#         for tick in ax.xaxis.get_major_ticks():
#             if tick.tick1line.get_visible():
#                 try:
#                     tb = tick.tick1line.get_window_extent(renderer)
#                     if tb.width > 0 or tb.height > 0:
#                         x_axis_bboxes.append(tb)
#                 except Exception:
#                     pass
#         spine_bbox = ax.spines["bottom"].get_window_extent(renderer)
#         if spine_bbox.width > 0:
#             if x_axis_bboxes:
#                 tick_union = Bbox.union(x_axis_bboxes)
#                 constrained_spine = Bbox.from_extents(
#                     tick_union.x0, spine_bbox.y0, tick_union.x1, spine_bbox.y1
#                 )
#                 x_axis_bboxes.append(constrained_spine)
#             else:
#                 x_axis_bboxes.append(spine_bbox)
#         if x_axis_bboxes:
#             combined = Bbox.union(x_axis_bboxes)
#             bboxes["xaxis_ticks"] = bbox_to_img_coords(combined)
#             bboxes["xaxis_ticks"]["label"] = "X Spine & Ticks"
#
#         # Y-axis: combine spine and tick labels
#         y_axis_bboxes = []
#         for ticklabel in ax.yaxis.get_ticklabels():
#             if ticklabel.get_visible():
#                 try:
#                     tb = ticklabel.get_window_extent(renderer)
#                     if tb.width > 0:
#                         y_axis_bboxes.append(tb)
#                 except Exception:
#                     pass
#         for tick in ax.yaxis.get_major_ticks():
#             if tick.tick1line.get_visible():
#                 try:
#                     tb = tick.tick1line.get_window_extent(renderer)
#                     if tb.width > 0 or tb.height > 0:
#                         y_axis_bboxes.append(tb)
#                 except Exception:
#                     pass
#         spine_bbox = ax.spines["left"].get_window_extent(renderer)
#         if spine_bbox.height > 0:
#             if y_axis_bboxes:
#                 tick_union = Bbox.union(y_axis_bboxes)
#                 constrained_spine = Bbox.from_extents(
#                     spine_bbox.x0, tick_union.y0, spine_bbox.x1, tick_union.y1
#                 )
#                 y_axis_bboxes.append(constrained_spine)
#             else:
#                 y_axis_bboxes.append(spine_bbox)
#         if y_axis_bboxes:
#             combined = Bbox.union(y_axis_bboxes)
#             padded = Bbox.from_extents(
#                 combined.x0 - 10, combined.y0 - 5, combined.x1 + 5, combined.y1 + 5
#             )
#             bboxes["yaxis_ticks"] = bbox_to_img_coords(padded)
#             bboxes["yaxis_ticks"]["label"] = "Y Spine & Ticks"
#
#     except Exception as e:
#         print(f"Error getting axis bboxes: {e}")
#
#
# def _extract_trace_bboxes(ax, fig, bboxes, get_element_bbox, coords_to_img_points, bbox_to_img_coords, img_width, img_height):
#     """Extract bboxes for all data elements (lines, scatter, bars, etc.)."""
#     from matplotlib.transforms import Bbox
#
#     # 1. Extract lines (separate user lines from boxplot lines)
#     line_idx = 0
#     boxplot_lines = []  # Collect boxplot lines for grouping
#
#     for line in ax.get_lines():
#         try:
#             label = line.get_label()
#
#             # Check if this is a boxplot line (starts with _child or _nolegend_)
#             if label.startswith("_child") or label == "_nolegend_":
#                 boxplot_lines.append(line)
#                 continue
#
#             # Skip other underscore-prefixed labels
#             if label.startswith("_"):
#                 continue
#
#             trace_name = f"trace_{line_idx}"
#             get_element_bbox(line, trace_name)
#
#             if trace_name in bboxes:
#                 bboxes[trace_name]["label"] = label or f"Line {line_idx}"
#                 bboxes[trace_name]["trace_idx"] = line_idx
#                 bboxes[trace_name]["element_type"] = "line"
#
#                 xdata, ydata = line.get_xdata(), line.get_ydata()
#                 if len(xdata) > 0:
#                     bboxes[trace_name]["points"] = coords_to_img_points(
#                         list(zip(xdata, ydata))
#                     )
#
#                     # Add schema v0.3 geometry (axes-local pixels with path simplification)
#                     if GEOMETRY_V03_AVAILABLE:
#                         try:
#                             geom = extract_line_geometry(line, ax, fig, simplify_threshold=0.5)
#                             bboxes[trace_name]["geometry_px"] = geom
#                         except Exception:
#                             pass
#             line_idx += 1
#         except Exception as e:
#             print(f"Error getting line bbox: {e}")
#
#     # 1b. Group boxplot lines into box elements by x-position
#     if boxplot_lines:
#         _extract_boxplot_bboxes(ax, boxplot_lines, bboxes, bbox_to_img_coords, Bbox)
#
#     # 2. Extract collections (scatter, fill_between, violin, etc.)
#     coll_idx = 0
#     scatter_idx = 0
#     fill_idx = 0
#     violin_idx = 0
#     for coll in ax.collections:
#         try:
#             label = coll.get_label()
#             is_internal = label.startswith("_") if label else False
#             if is_internal:
#                 label = None
#
#             coll_type = type(coll).__name__
#             if coll_type == "PathCollection":
#                 # Scatter points - need special handling as get_window_extent returns inf
#                 element_name = f"scatter_{scatter_idx}"
#                 offsets = coll.get_offsets()
#
#                 if len(offsets) > 0:
#                     # Compute bbox from the scatter point coordinates
#                     points_img = coords_to_img_points(offsets)
#                     if points_img:
#                         xs = [p[0] for p in points_img]
#                         ys = [p[1] for p in points_img]
#                         # Add padding for marker size
#                         padding = 10
#                         bboxes[element_name] = {
#                             "x0": max(0, min(xs) - padding),
#                             "y0": max(0, min(ys) - padding),
#                             "x1": min(img_width, max(xs) + padding),
#                             "y1": min(img_height, max(ys) + padding),
#                             "label": label or f"Scatter {scatter_idx}",
#                             "element_type": "scatter",
#                             "points": points_img,
#                         }
#
#                         # Add schema v0.3 geometry (axes-local pixels with hit_radius_px)
#                         if GEOMETRY_V03_AVAILABLE:
#                             try:
#                                 geom = extract_scatter_geometry(coll, ax, fig)
#                                 bboxes[element_name]["geometry_px"] = geom
#                             except Exception:
#                                 pass
#                 scatter_idx += 1
#
#             elif coll_type == "FillBetweenPolyCollection":
#                 # Violin plot bodies / fill_between
#                 element_name = f"violin_{violin_idx}"
#                 get_element_bbox(coll, element_name)
#
#                 if element_name in bboxes:
#                     bboxes[element_name]["label"] = f"Violin {violin_idx + 1}"
#                     bboxes[element_name]["element_type"] = "violin"
#
#                     # Add schema v0.3 geometry (axes-local polygon)
#                     if GEOMETRY_V03_AVAILABLE:
#                         try:
#                             geom = extract_polygon_geometry(coll, ax, fig)
#                             bboxes[element_name]["geometry_px"] = geom
#                         except Exception:
#                             pass
#                 violin_idx += 1
#
#             elif coll_type == "PolyCollection":
#                 # Fill areas
#                 element_name = f"fill_{fill_idx}"
#                 get_element_bbox(coll, element_name)
#
#                 if element_name in bboxes:
#                     bboxes[element_name]["label"] = label or f"Fill {fill_idx}"
#                     bboxes[element_name]["element_type"] = "fill"
#
#                     # Add schema v0.3 geometry (axes-local polygon)
#                     if GEOMETRY_V03_AVAILABLE:
#                         try:
#                             geom = extract_polygon_geometry(coll, ax, fig)
#                             bboxes[element_name]["geometry_px"] = geom
#                         except Exception:
#                             pass
#                 fill_idx += 1
#
#             # Skip LineCollection from violin plots (internal elements)
#             elif coll_type == "LineCollection" and is_internal:
#                 pass
#
#             coll_idx += 1
#         except Exception as e:
#             print(f"Error getting collection bbox: {e}")
#
#     # 3. Extract patches (bars, rectangles, etc.)
#     patch_idx = 0
#     for patch in ax.patches:
#         try:
#             label = patch.get_label()
#             patch_type = type(patch).__name__
#
#             if patch_type == "Rectangle":
#                 element_name = f"bar_{patch_idx}"
#                 get_element_bbox(patch, element_name)
#
#                 if element_name in bboxes:
#                     bboxes[element_name]["label"] = label or f"Bar {patch_idx}"
#                     bboxes[element_name]["element_type"] = "bar"
#
#             patch_idx += 1
#         except Exception as e:
#             print(f"Error getting patch bbox: {e}")
#
#
# def _extract_boxplot_bboxes(ax, boxplot_lines, bboxes, bbox_to_img_coords, Bbox):
#     """Extract bboxes for boxplot elements by grouping lines by x-position."""
#     import numpy as np
#
#     # Group lines by their x center position
#     x_groups = {}
#     for line in boxplot_lines:
#         try:
#             xdata = line.get_xdata()
#             if len(xdata) == 0:
#                 continue
#             # Use mean x as grouping key (round to handle floating point)
#             x_center = round(np.mean(xdata), 2)
#             if x_center not in x_groups:
#                 x_groups[x_center] = []
#             x_groups[x_center].append(line)
#         except Exception:
#             pass
#
#     # Create a bbox for each box group
#     renderer = ax.figure.canvas.get_renderer()
#     sorted_positions = sorted(x_groups.keys())
#
#     for idx, x_pos in enumerate(sorted_positions):
#         lines = x_groups[x_pos]
#         if not lines:
#             continue
#
#         try:
#             # Combine all line bboxes in this group
#             line_bboxes = []
#             for line in lines:
#                 try:
#                     lb = line.get_window_extent(renderer)
#                     if lb.width > 0 or lb.height > 0:
#                         line_bboxes.append(lb)
#                 except Exception:
#                     pass
#
#             if line_bboxes:
#                 combined = Bbox.union(line_bboxes)
#                 element_name = f"boxplot_{idx}"
#                 coords = bbox_to_img_coords(combined)
#                 bboxes[element_name] = {
#                     **coords,
#                     "label": f"Box {idx + 1}",
#                     "element_type": "boxplot",
#                 }
#         except Exception as e:
#             print(f"Error extracting boxplot bbox: {e}")
#
#
# # EOF

# --------------------------------------------------------------------------------
# End of Source Code from: apps/figrecipe_app/services/plot_renderer/element_bboxes.py
# --------------------------------------------------------------------------------
