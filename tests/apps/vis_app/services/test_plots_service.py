#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for apps/vis_app/services/plots_service.py"""

import pytest

# from apps.workspace.vis_app.services.plots_service import ...


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
# Start of Source Code from: apps/vis_app/services/plots_service.py
# --------------------------------------------------------------------------------
# """
# Plots Service - Business logic for plot rendering operations.
#
# Handles:
# - Converting CSV data to plots
# - Detecting X/Y column pairs
# - Rendering plots by type
# - Applying plot styling
# - Processing uploaded data files
# - Extracting image metadata
# """
#
# import base64
# import io
# import logging
# import os
# import re
# import tempfile
# import uuid
# from pathlib import Path
# from typing import Dict, List, Tuple, Optional
#
# import pandas as pd
# import numpy as np
#
# logger = logging.getLogger(__name__)
#
#
# class PlotsService:
#     """Service for plot rendering operations."""
#
#     @staticmethod
#     def detect_xy_column_pairs(cols: list) -> List[Tuple[str, str, str]]:
#         """
#         Detect paired X/Y columns from scitex gallery CSV format.
#
#         Column naming convention: ax-row-X-col-Y_trace-id-NAME_variable-{x|y}
#
#         Args:
#             cols: List of column names
#
#         Returns:
#             List of (x_col, y_col, trace_name) tuples for each detected trace
#         """
#         pairs = []
#         y_cols = []
#         x_cols = []
#
#         for col in cols:
#             if col.endswith('_variable-y') or col.endswith('variable_y'):
#                 y_cols.append(col)
#             elif col.endswith('_variable-x') or col.endswith('variable_x'):
#                 x_cols.append(col)
#
#         # Match Y columns with their X counterparts
#         for y_col in y_cols:
#             # Extract trace ID from column name
#             base = y_col.replace('_variable-y', '').replace('variable_y', '')
#
#             # Find matching X column
#             x_col = None
#             for xc in x_cols:
#                 xc_base = xc.replace('_variable-x', '').replace('variable_x', '')
#                 if xc_base == base:
#                     x_col = xc
#                     break
#
#             if x_col is None and x_cols:
#                 # Use first X column if no exact match
#                 x_col = x_cols[0]
#
#             # Extract trace name for label
#             match = re.search(r'trace-id-([^_]+)', y_col)
#             trace_name = match.group(1).replace('-', ' ') if match else y_col
#
#             if x_col:
#                 pairs.append((x_col, y_col, trace_name))
#
#         return pairs
#
#     @staticmethod
#     def prepare_dataframe(csv_data: List[List]) -> pd.DataFrame:
#         """
#         Convert CSV data to pandas DataFrame with numeric conversion.
#
#         Args:
#             csv_data: 2D list with header row and data rows
#
#         Returns:
#             Pandas DataFrame with numeric columns converted
#
#         Raises:
#             ValueError: If CSV data is invalid
#         """
#         if not csv_data or len(csv_data) < 2:
#             raise ValueError('CSV data must have at least 2 rows (header + data)')
#
#         headers = csv_data[0]
#         rows = csv_data[1:]
#         df = pd.DataFrame(rows, columns=headers)
#
#         # Convert numeric columns
#         for col in df.columns:
#             try:
#                 df[col] = pd.to_numeric(df[col])
#             except (ValueError, TypeError):
#                 pass
#
#         return df
#
#     @staticmethod
#     def render_plot_by_type(ax, df: pd.DataFrame, plot_type: str, category: str, overrides: dict):
#         """
#         Render plot based on type using scitex/matplotlib methods.
#
#         Args:
#             ax: Matplotlib axes object
#             df: Data DataFrame
#             plot_type: Plot type (e.g., 'plot', 'scatter', 'bar')
#             category: Plot category (e.g., 'line', 'scatter')
#             overrides: Style override dictionary
#         """
#         # Get column names
#         cols = df.columns.tolist()
#
#         # Detect paired X/Y columns from scitex gallery format
#         xy_pairs = PlotsService.detect_xy_column_pairs(cols)
#
#         if xy_pairs:
#             # Use detected X/Y pairs
#             x_col = xy_pairs[0][0]  # Use first X column as default
#             y_cols = [pair[1] for pair in xy_pairs]  # All Y columns
#         else:
#             # Fallback: Default x and y columns
#             x_col = overrides.get('x_column', cols[0] if len(cols) > 0 else None)
#             y_cols = overrides.get('y_columns', cols[1:] if len(cols) > 1 else [])
#
#         if isinstance(y_cols, str):
#             y_cols = [y_cols]
#
#         # Get data
#         x = df[x_col].values if x_col and x_col in df.columns else np.arange(len(df))
#
#         # Line plots - use paired X/Y columns if available
#         if plot_type in ['plot', 'line', 'stx_line']:
#             if xy_pairs:
#                 # Use detected X/Y pairs with proper trace names
#                 for x_col_i, y_col, trace_name in xy_pairs:
#                     if x_col_i in df.columns and y_col in df.columns:
#                         x_data = df[x_col_i].values
#                         y_data = df[y_col].values
#                         ax.plot(x_data, y_data, label=trace_name, linewidth=overrides.get('linewidth', 1.0))
#             else:
#                 for y_col in y_cols:
#                     if y_col in df.columns:
#                         y = df[y_col].values
#                         ax.plot(x, y, label=y_col, linewidth=overrides.get('linewidth', 1.0))
#
#         elif plot_type == 'step':
#             if xy_pairs:
#                 for x_col_i, y_col, trace_name in xy_pairs:
#                     if x_col_i in df.columns and y_col in df.columns:
#                         x_data = df[x_col_i].values
#                         y_data = df[y_col].values
#                         ax.step(x_data, y_data, label=trace_name, linewidth=overrides.get('linewidth', 1.0))
#             else:
#                 for y_col in y_cols:
#                     if y_col in df.columns:
#                         y = df[y_col].values
#                         ax.step(x, y, label=y_col, linewidth=overrides.get('linewidth', 1.0))
#
#         elif plot_type == 'stx_shaded_line':
#             if xy_pairs:
#                 for x_col_i, y_col, trace_name in xy_pairs:
#                     if x_col_i in df.columns and y_col in df.columns:
#                         x_data = df[x_col_i].values
#                         y_data = df[y_col].values
#                         ax.plot(x_data, y_data, label=trace_name)
#                         ax.fill_between(x_data, y_data, alpha=0.3)
#             else:
#                 for y_col in y_cols:
#                     if y_col in df.columns:
#                         y = df[y_col].values
#                         ax.plot(x, y, label=y_col)
#                         ax.fill_between(x, y, alpha=0.3)
#
#         # Scatter plots
#         elif plot_type == 'scatter':
#             if xy_pairs:
#                 for x_col_i, y_col, trace_name in xy_pairs:
#                     if x_col_i in df.columns and y_col in df.columns:
#                         x_data = df[x_col_i].values
#                         y_data = df[y_col].values
#                         ax.scatter(x_data, y_data, label=trace_name, s=overrides.get('marker_size', 20))
#             else:
#                 for y_col in y_cols:
#                     if y_col in df.columns:
#                         y = df[y_col].values
#                         ax.scatter(x, y, label=y_col, s=overrides.get('marker_size', 20))
#
#         elif plot_type == 'stx_scatter':
#             for y_col in y_cols:
#                 if y_col in df.columns:
#                     y = df[y_col].values
#                     # Use actual stx_scatter method if available
#                     if hasattr(ax, 'stx_scatter'):
#                         ax.stx_scatter(x, y, label=y_col, s=overrides.get('marker_size', 20))
#                     else:
#                         ax.scatter(x, y, label=y_col, s=overrides.get('marker_size', 20))
#
#         # Bar plots
#         elif plot_type == 'bar':
#             if len(y_cols) > 0 and y_cols[0] in df.columns:
#                 y = df[y_cols[0]].values
#                 ax.bar(x, y)
#
#         elif plot_type == 'stx_bar':
#             if len(y_cols) > 0 and y_cols[0] in df.columns:
#                 y = df[y_cols[0]].values
#                 if hasattr(ax, 'stx_bar'):
#                     ax.stx_bar(x, y)
#                 else:
#                     ax.bar(x, y)
#
#         elif plot_type == 'barh':
#             if len(y_cols) > 0 and y_cols[0] in df.columns:
#                 y = df[y_cols[0]].values
#                 ax.barh(x, y)
#
#         # Histogram
#         elif plot_type in ['hist', 'histogram']:
#             if len(y_cols) > 0 and y_cols[0] in df.columns:
#                 y = df[y_cols[0]].values
#                 bins = overrides.get('bins', 10)
#                 ax.hist(y, bins=bins, alpha=0.7)
#
#         # Box plot
#         elif plot_type in ['box', 'boxplot']:
#             data_to_plot = [df[col].values for col in y_cols if col in df.columns]
#             if data_to_plot:
#                 ax.boxplot(data_to_plot, labels=y_cols)
#
#         # Violin plot
#         elif plot_type == 'violin':
#             data_to_plot = [df[col].values for col in y_cols if col in df.columns]
#             if data_to_plot:
#                 positions = list(range(1, len(data_to_plot) + 1))
#                 ax.violinplot(data_to_plot, positions=positions, showmeans=True)
#                 ax.set_xticks(positions)
#                 ax.set_xticklabels(y_cols)
#
#         # Heatmap
#         elif plot_type == 'heatmap':
#             # Use numeric columns only
#             numeric_df = df.select_dtypes(include=[np.number])
#             if not numeric_df.empty:
#                 import matplotlib.pyplot as plt
#                 im = ax.imshow(numeric_df.T, aspect='auto', cmap='viridis')
#                 ax.set_yticks(range(len(numeric_df.columns)))
#                 ax.set_yticklabels(numeric_df.columns)
#                 plt.colorbar(im, ax=ax)
#
#     @staticmethod
#     def apply_plot_styling(ax, overrides: dict):
#         """
#         Apply common styling from overrides.
#
#         Args:
#             ax: Matplotlib axes object
#             overrides: Style override dictionary
#         """
#         # Labels
#         if overrides.get('title'):
#             ax.set_title(overrides['title'], fontsize=overrides.get('title_fontsize', 10))
#         if overrides.get('xlabel'):
#             ax.set_xlabel(overrides['xlabel'], fontsize=overrides.get('axis_fontsize', 9))
#         if overrides.get('ylabel'):
#             ax.set_ylabel(overrides['ylabel'], fontsize=overrides.get('axis_fontsize', 9))
#
#         # Axis limits
#         if overrides.get('xlim'):
#             ax.set_xlim(overrides['xlim'])
#         if overrides.get('ylim'):
#             ax.set_ylim(overrides['ylim'])
#
#         # Grid
#         if overrides.get('grid', False):
#             ax.grid(True, alpha=0.3)
#
#         # Spines
#         if overrides.get('hide_top_spine', True):
#             ax.spines['top'].set_visible(False)
#         if overrides.get('hide_right_spine', True):
#             ax.spines['right'].set_visible(False)
#
#         # Tick styling
#         tick_fontsize = overrides.get('tick_fontsize', 8)
#         ax.tick_params(axis='both', labelsize=tick_fontsize)
#
#     @staticmethod
#     def render_gallery_plot(
#         plot_type: str,
#         category: str,
#         csv_data: List[List],
#         overrides: dict
#     ) -> Dict:
#         """
#         Render a plot from gallery template with CSV data.
#
#         Args:
#             plot_type: Plot type (e.g., 'plot', 'scatter', 'bar')
#             category: Category (e.g., 'line', 'scatter')
#             csv_data: 2D array of data with header row
#             overrides: Style overrides
#
#         Returns:
#             Dictionary with success, image (base64), width, height, element_bboxes, column_mapping
#
#         Raises:
#             ImportError: If required packages not available
#         """
#         # Set matplotlib backend
#         os.environ['MPLBACKEND'] = 'Agg'
#
#         try:
#             import scitex as stx
#         except ImportError as e:
#             raise ImportError(f'scitex not available: {e}')
#
#         # Convert CSV data to DataFrame
#         df = PlotsService.prepare_dataframe(csv_data)
#
#         # Get figure size from overrides or defaults
#         fig_width = overrides.get('fig_width', 4)
#         fig_height = overrides.get('fig_height', 3)
#         dpi = overrides.get('dpi', 150)
#
#         # Create figure with scitex
#         fig, ax = stx.plt.subplots(figsize=(fig_width, fig_height))
#
#         # Plot based on type
#         PlotsService.render_plot_by_type(ax, df, plot_type, category, overrides)
#
#         # Apply common styling
#         PlotsService.apply_plot_styling(ax, overrides)
#
#         fig.tight_layout()
#
#         # Draw figure to get accurate renderer
#         fig.canvas.draw()
#         renderer = fig.canvas.get_renderer()
#
#         # Save to buffer first to get actual image dimensions
#         # Use transparent background - works on both light and dark canvases
#         buf = io.BytesIO()
#         fig.savefig(buf, format='png', dpi=dpi, bbox_inches='tight',
#                     transparent=True, facecolor='none', edgecolor='none')
#         buf.seek(0)
#
#         # Get actual image dimensions
#         from PIL import Image
#         img = Image.open(buf)
#         width, height = img.size
#         buf.seek(0)
#
#         # Extract element bboxes for element-level selection
#         from apps.workspace.vis_app.services.plot_renderer.element_bboxes import extract_element_bboxes
#         element_bboxes = extract_element_bboxes(fig, ax, renderer, width, height)
#
#         # Generate hitmap for fast element picking (optional enhancement)
#         hitmap_data = None
#         hitmap_color_map = None
#         try:
#             from scitex.plt.utils._hitmap import generate_hitmap_id_colors, save_hitmap_png
#             hitmap, color_map = generate_hitmap_id_colors(fig, dpi=dpi)
#             # Convert hitmap to base64 PNG
#             hitmap_buf = io.BytesIO()
#             from PIL import Image as PILImage
#             # Convert 24-bit IDs back to RGB
#             h, w = hitmap.shape
#             rgb = np.zeros((h, w, 3), dtype=np.uint8)
#             rgb[:, :, 0] = (hitmap >> 16) & 0xFF
#             rgb[:, :, 1] = (hitmap >> 8) & 0xFF
#             rgb[:, :, 2] = hitmap & 0xFF
#             hitmap_img = PILImage.fromarray(rgb, mode='RGB')
#             hitmap_img.save(hitmap_buf, format='PNG')
#             hitmap_buf.seek(0)
#             hitmap_data = f'data:image/png;base64,{base64.b64encode(hitmap_buf.getvalue()).decode("utf-8")}'
#             hitmap_color_map = {str(k): v for k, v in color_map.items()}
#             logger.info(f'[PlotsService] Generated hitmap with {len(color_map)} elements')
#         except Exception as e:
#             logger.debug(f'[PlotsService] Hitmap generation skipped: {e}')
#
#         # Add column mapping to data elements (for CSV column highlighting)
#         cols = df.columns.tolist()
#         xy_pairs = PlotsService.detect_xy_column_pairs(cols)
#
#         if xy_pairs:
#             x_col = xy_pairs[0][0]
#             y_cols = [pair[1] for pair in xy_pairs]
#         else:
#             x_col = overrides.get('x_column', cols[0] if len(cols) > 0 else None)
#             y_cols = overrides.get('y_columns', cols[1:] if len(cols) > 1 else [])
#
#         if isinstance(y_cols, str):
#             y_cols = [y_cols]
#
#         # Map element names to their CSV columns
#         column_mapping = PlotsService._map_elements_to_columns(
#             element_bboxes, y_cols, xy_pairs
#         )
#
#         # Convert to base64
#         b64_data = base64.b64encode(buf.getvalue()).decode('utf-8')
#
#         result = {
#             'success': True,
#             'image': f'data:image/png;base64,{b64_data}',
#             'width': width,
#             'height': height,
#             'element_bboxes': element_bboxes,
#             'column_mapping': column_mapping,
#         }
#
#         # Add hitmap data if available
#         if hitmap_data and hitmap_color_map:
#             result['hitmap'] = hitmap_data
#             result['hitmap_color_map'] = hitmap_color_map
#
#         return result
#
#     @staticmethod
#     def _map_elements_to_columns(
#         element_bboxes: Dict,
#         y_cols: List[str],
#         xy_pairs: List[Tuple[str, str, str]]
#     ) -> Dict[str, str]:
#         """
#         Map element names to their CSV columns.
#
#         Args:
#             element_bboxes: Element bounding boxes dictionary
#             y_cols: List of Y column names
#             xy_pairs: List of (x_col, y_col, trace_name) tuples
#
#         Returns:
#             Dictionary mapping element names to column names
#         """
#         column_mapping = {}
#
#         for element_name, bbox in element_bboxes.items():
#             element_type = bbox.get('element_type', '')
#             label = bbox.get('label', '')
#
#             if element_type in ['line', 'scatter']:
#                 # For traces, use trace_idx if available, otherwise try label matching
#                 trace_idx = bbox.get('trace_idx')
#                 matched_y_col = None
#                 matched_y_idx = None
#
#                 if trace_idx is not None and trace_idx < len(y_cols):
#                     # Direct mapping by trace index
#                     matched_y_col = y_cols[trace_idx]
#                     matched_y_idx = trace_idx
#                 elif label:
#                     # Try to match by label
#                     for idx, y_col in enumerate(y_cols):
#                         if label == y_col or (xy_pairs and label == xy_pairs[idx][2]):
#                             matched_y_col = y_col
#                             matched_y_idx = idx
#                             break
#
#                 if matched_y_col:
#                     column_mapping[element_name] = matched_y_col
#
#         return column_mapping
#
#     @staticmethod
#     def save_uploaded_file(uploaded_file) -> Dict[str, any]:
#         """
#         Save uploaded data file to temporary directory.
#
#         Args:
#             uploaded_file: Django UploadedFile object
#
#         Returns:
#             Dictionary with file_path, filename, size
#
#         Raises:
#             ValueError: If file type is invalid
#         """
#         # Validate file extension
#         allowed_extensions = ['.csv', '.xlsx', '.xls']
#         file_ext = '.' + uploaded_file.name.split('.')[-1].lower()
#
#         if file_ext not in allowed_extensions:
#             raise ValueError(f'Invalid file type. Allowed: {", ".join(allowed_extensions)}')
#
#         # Create temp directory for uploaded plot data
#         temp_dir = Path(tempfile.gettempdir()) / 'scitex_plot_data'
#         temp_dir.mkdir(exist_ok=True)
#
#         # Generate unique filename
#         unique_filename = f"{uuid.uuid4()}{file_ext}"
#         file_path = temp_dir / unique_filename
#
#         # Save file
#         with open(file_path, 'wb+') as destination:
#             for chunk in uploaded_file.chunks():
#                 destination.write(chunk)
#
#         return {
#             'success': True,
#             'file_path': str(file_path),
#             'filename': uploaded_file.name,
#             'size': uploaded_file.size
#         }
#
#     @staticmethod
#     def extract_image_metadata_from_base64(image_data: str) -> Dict:
#         """
#         Extract scitex metadata from base64 image data.
#
#         Args:
#             image_data: Base64 string or data URL
#
#         Returns:
#             Dictionary with success, has_metadata, metadata, axes_bbox_px, figure_size_px
#
#         Raises:
#             ValueError: If image data is invalid
#         """
#         import tempfile
#         import json as json_module
#
#         # Remove data URL prefix if present
#         if image_data.startswith('data:'):
#             # Extract base64 part: data:image/png;base64,XXXXX
#             try:
#                 image_data = image_data.split(',', 1)[1]
#             except IndexError:
#                 raise ValueError('Invalid data URL format')
#
#         # Decode base64 to bytes
#         try:
#             image_bytes = base64.b64decode(image_data)
#         except Exception as e:
#             raise ValueError(f'Invalid base64 data: {e}')
#
#         # Save to temp file to use scitex.io.read_metadata
#         with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
#             tmp.write(image_bytes)
#             tmp_path = tmp.name
#
#         try:
#             # Try to use scitex.io to read metadata
#             metadata = None
#             try:
#                 from scitex.io._metadata import read_metadata
#                 metadata = read_metadata(tmp_path)
#             except ImportError:
#                 # Fall back to PIL if scitex not available
#                 from PIL import Image
#                 img = Image.open(tmp_path)
#                 if hasattr(img, 'info') and 'scitex_metadata' in img.info:
#                     try:
#                         metadata = json_module.loads(img.info['scitex_metadata'])
#                     except:
#                         pass
#                 img.close()
#
#             if not metadata:
#                 return {
#                     'success': True,
#                     'has_metadata': False,
#                     'message': 'No scitex metadata found in image'
#                 }
#
#             # Extract axes_bbox_px from metadata
#             result = PlotsService._extract_metadata_fields(metadata)
#             result['success'] = True
#             result['has_metadata'] = True
#             result['metadata'] = metadata
#
#             return result
#
#         finally:
#             # Clean up temp file
#             try:
#                 os.unlink(tmp_path)
#             except:
#                 pass
#
#     @staticmethod
#     def _extract_metadata_fields(metadata: Dict) -> Dict:
#         """
#         Extract axes_bbox_px and figure_size_px from metadata.
#
#         Args:
#             metadata: Raw metadata dictionary
#
#         Returns:
#             Dictionary with axes_bbox_px and figure_size_px
#         """
#         axes_bbox_px = None
#         figure_size_px = None
#
#         # Check for axes metadata
#         if 'axes' in metadata and len(metadata['axes']) > 0:
#             ax_meta = metadata['axes'][0]
#             if 'bbox_px' in ax_meta:
#                 bbox = ax_meta['bbox_px']
#                 # Convert from x_left/y_top format to x0/y0 format
#                 axes_bbox_px = {
#                     'x0': bbox.get('x_left', 0),
#                     'y0': bbox.get('y_top', 0),
#                     'x1': bbox.get('x_right', 0),
#                     'y1': bbox.get('y_bottom', 0),
#                     'width': bbox.get('width', 0),
#                     'height': bbox.get('height', 0),
#                 }
#
#         # Check for figure dimensions
#         if 'dimensions' in metadata:
#             dims = metadata['dimensions']
#             if 'figure_size_px' in dims:
#                 size = dims['figure_size_px']
#                 if isinstance(size, list):
#                     figure_size_px = {'width': size[0], 'height': size[1]}
#                 else:
#                     figure_size_px = size
#
#         # Also check top-level axes_bbox_px (older format)
#         if not axes_bbox_px and 'axes_bbox_px' in metadata:
#             axes_bbox_px = metadata['axes_bbox_px']
#
#         return {
#             'axes_bbox_px': axes_bbox_px,
#             'figure_size_px': figure_size_px
#         }

# --------------------------------------------------------------------------------
# End of Source Code from: apps/vis_app/services/plots_service.py
# --------------------------------------------------------------------------------
