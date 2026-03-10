#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for apps/vis_app/services/gallery_service.py"""

import pytest

# from apps.workspace.vis_app.services.gallery_service import ...


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
# Start of Source Code from: apps/vis_app/services/gallery_service.py
# --------------------------------------------------------------------------------
# """
# Gallery Service - Business logic for plot gallery operations.
#
# Handles:
# - Scanning gallery directories for plot files
# - Categorizing plots by type
# - Loading plot thumbnails and templates
# - Generating boilerplate code
# - Loading plot metadata
# - Loading pltz bundles from gallery
# """
#
# import base64
# import json
# import logging
# import os
# from pathlib import Path
# from typing import Dict, List, Optional, Tuple, Union
#
# from django.conf import settings
#
# from .pltz_service import PltzService
#
# logger = logging.getLogger(__name__)
#
#
# # Base path to scitex-code examples
# SCITEX_CODE_PATH = Path(os.environ.get(
#     'SCITEX_CODE_PATH',
#     '/home/ywatanabe/proj/scitex-code'
# ))
# EXAMPLES_PATH = SCITEX_CODE_PATH / 'examples' / 'plt'
#
#
# class GalleryService:
#     """Service for gallery-related operations."""
#
#     @staticmethod
#     def get_plot_galleries() -> List[Dict]:
#         """
#         Get all plot galleries from examples directory.
#
#         Returns:
#             List of gallery dictionaries with id, name, description, path, and plots
#         """
#         galleries = []
#
#         # Matplotlib basic plots
#         mpl_out = EXAMPLES_PATH / 'demo_matplotlib_basic_out'
#         if mpl_out.exists():
#             galleries.append({
#                 'id': 'matplotlib',
#                 'name': 'Matplotlib',
#                 'description': 'Standard matplotlib plot types',
#                 'path': mpl_out,
#                 'plots': GalleryService._scan_gallery(mpl_out, 'mpl')
#             })
#
#         # SciTeX wrapper plots
#         stx_out = EXAMPLES_PATH / 'demo_scitex_wrappers_out'
#         if stx_out.exists():
#             galleries.append({
#                 'id': 'scitex',
#                 'name': 'SciTeX',
#                 'description': 'SciTeX enhanced plot wrappers',
#                 'path': stx_out,
#                 'plots': GalleryService._scan_gallery(stx_out, 'stx')
#             })
#
#         # Seaborn wrapper plots
#         sns_out = EXAMPLES_PATH / 'demo_seaborn_wrappers_out'
#         if sns_out.exists():
#             galleries.append({
#                 'id': 'seaborn',
#                 'name': 'Seaborn',
#                 'description': 'Seaborn statistical plots',
#                 'path': sns_out,
#                 'plots': GalleryService._scan_gallery(sns_out, 'sns')
#             })
#
#         return galleries
#
#     @staticmethod
#     def _scan_gallery(base_path: Path, prefix: str) -> List[Dict]:
#         """
#         Scan gallery directory for plot types.
#
#         Args:
#             base_path: Base directory to scan
#             prefix: Prefix for plot IDs (e.g., 'mpl', 'stx', 'sns')
#
#         Returns:
#             List of plot info dictionaries
#         """
#         plots = []
#
#         png_dir = base_path / 'png'
#         json_dir = base_path / 'json'
#         csv_dir = base_path / 'csv'
#
#         if not png_dir.exists():
#             return plots
#
#         for png_file in sorted(png_dir.glob('*.png')):
#             stem = png_file.stem
#             json_file = json_dir / f'{stem}.json'
#             csv_file = csv_dir / f'{stem}.csv'
#
#             # Parse plot name from filename (e.g., "01_plot" -> "Plot")
#             parts = stem.split('_', 1)
#             number = parts[0] if len(parts) > 1 else ''
#             name_part = parts[1] if len(parts) > 1 else stem
#
#             # Clean up name
#             display_name = name_part.replace('_', ' ').title()
#
#             # Categorize by plot type
#             category = GalleryService._categorize_plot(name_part)
#
#             plot_info = {
#                 'id': f'{prefix}_{stem}',
#                 'name': display_name,
#                 'category': category,
#                 'number': number,
#                 'files': {
#                     'png': str(png_file),
#                     'json': str(json_file) if json_file.exists() else None,
#                     'csv': str(csv_file) if csv_file.exists() else None,
#                 }
#             }
#
#             plots.append(plot_info)
#
#         return plots
#
#     @staticmethod
#     def _categorize_plot(name: str) -> str:
#         """
#         Categorize plot by type based on name.
#
#         Args:
#             name: Plot name to categorize
#
#         Returns:
#             Category string
#         """
#         name_lower = name.lower()
#
#         if any(x in name_lower for x in ['line', 'plot', 'step', 'mean', 'median', 'shaded']):
#             return 'line'
#         elif any(x in name_lower for x in ['scatter']):
#             return 'scatter'
#         elif any(x in name_lower for x in ['bar', 'barh']):
#             return 'bar'
#         elif any(x in name_lower for x in ['hist', 'kde', 'ecdf']):
#             return 'distribution'
#         elif any(x in name_lower for x in ['box', 'violin', 'strip', 'swarm', 'joyplot']):
#             return 'statistical'
#         elif any(x in name_lower for x in ['heatmap', 'imshow', 'matshow', 'conf_mat', 'image']):
#             return 'heatmap'
#         elif any(x in name_lower for x in ['contour', 'hexbin', 'fill']):
#             return 'contour'
#         elif any(x in name_lower for x in ['pie']):
#             return 'pie'
#         elif any(x in name_lower for x in ['quiver', 'stream', 'raster']):
#             return 'vector'
#         elif any(x in name_lower for x in ['errorbar']):
#             return 'error'
#         elif any(x in name_lower for x in ['stem']):
#             return 'stem'
#         else:
#             return 'other'
#
#     @staticmethod
#     def find_plot_in_galleries(gallery_id: str, plot_id: str) -> Optional[Tuple[Dict, Dict]]:
#         """
#         Find a plot in galleries.
#
#         Args:
#             gallery_id: Gallery identifier
#             plot_id: Plot identifier
#
#         Returns:
#             Tuple of (gallery, plot) or None if not found
#         """
#         galleries = GalleryService.get_plot_galleries()
#         gallery = next((g for g in galleries if g['id'] == gallery_id), None)
#
#         if not gallery:
#             return None
#
#         plot = next((p for p in gallery['plots'] if p['id'] == f'{gallery_id[:3]}_{plot_id}'), None)
#
#         if not plot:
#             # Try direct match
#             plot = next((p for p in gallery['plots'] if plot_id in p['id']), None)
#
#         if not plot:
#             return None
#
#         return gallery, plot
#
#     @staticmethod
#     def load_thumbnail(png_path: Path) -> bytes:
#         """
#         Load thumbnail image data.
#
#         Args:
#             png_path: Path to PNG file
#
#         Returns:
#             Binary image data
#
#         Raises:
#             FileNotFoundError: If file doesn't exist
#         """
#         if not png_path.exists():
#             raise FileNotFoundError(f'Thumbnail file not found: {png_path}')
#
#         with open(png_path, 'rb') as f:
#             return f.read()
#
#     @staticmethod
#     def encode_thumbnail_base64(image_data: bytes) -> str:
#         """
#         Encode image data as base64 data URL.
#
#         Args:
#             image_data: Binary image data
#
#         Returns:
#             Base64 data URL string
#         """
#         b64_data = base64.b64encode(image_data).decode('utf-8')
#         return f'data:image/png;base64,{b64_data}'
#
#     @staticmethod
#     def load_plot_template(plot: Dict) -> Dict:
#         """
#         Load plot template data (JSON metadata and CSV columns).
#
#         Args:
#             plot: Plot info dictionary
#
#         Returns:
#             Dictionary with metadata and CSV columns
#         """
#         result = {
#             'id': plot['id'],
#             'name': plot['name'],
#             'category': plot['category'],
#         }
#
#         # Load JSON metadata if exists
#         if plot['files']['json']:
#             json_path = Path(plot['files']['json'])
#             if json_path.exists():
#                 with open(json_path, 'r') as f:
#                     result['metadata'] = json.load(f)
#                 # Extract axes_bbox_px for easy access
#                 if 'axes_bbox_px' in result['metadata']:
#                     result['axes_bbox_px'] = result['metadata']['axes_bbox_px']
#
#         # Load CSV columns if exists
#         if plot['files']['csv']:
#             csv_path = Path(plot['files']['csv'])
#             if csv_path.exists():
#                 with open(csv_path, 'r') as f:
#                     header = f.readline().strip()
#                     result['csv_columns'] = header.split(',')
#
#         return result
#
#     @staticmethod
#     def generate_boilerplate(plot: dict, gallery_id: str) -> str:
#         """
#         Generate Python boilerplate code for the plot type.
#
#         Args:
#             plot: Plot info dictionary
#             gallery_id: Gallery identifier
#
#         Returns:
#             Python code string
#         """
#         name = plot['name'].lower().replace(' ', '_')
#
#         if gallery_id == 'matplotlib':
#             return f'''import scitex as stx
#
# fig, ax = stx.plt.subplots()
# # ax.{name}(x, y)
# stx.io.save(fig, "output/{name}.png")
# '''
#         elif gallery_id == 'scitex':
#             # SciTeX wrappers use stx_xxx naming (e.g., stx_line, stx_bar)
#             method = name.replace('stx_', '').replace('plot_', '')
#             return f'''import scitex as stx
#
# fig, ax = stx.plt.subplots()
# # ax.stx_{method}(x, y)
# stx.io.save(fig, "output/stx_{method}.png")
# '''
#         elif gallery_id == 'seaborn':
#             method = name.replace('sns_', '')
#             return f'''import scitex as stx
#
# fig, ax = stx.plt.subplots()
# # ax.sns_{method}(data=df, x="x", y="y")
# stx.io.save(fig, "output/sns_{method}.png")
# '''
#         else:
#             return '# Plot code here'
#
#     @staticmethod
#     def get_category_counts() -> Dict[str, int]:
#         """
#         Count plots by category across all galleries.
#
#         Returns:
#             Dictionary mapping category ID to count
#         """
#         galleries = GalleryService.get_plot_galleries()
#
#         category_counts = {}
#         for gallery in galleries:
#             for plot in gallery['plots']:
#                 cat = plot['category']
#                 if cat not in category_counts:
#                     category_counts[cat] = 0
#                 category_counts[cat] += 1
#
#         return category_counts
#
#     @staticmethod
#     def format_categories(category_counts: Dict[str, int]) -> List[Dict]:
#         """
#         Format category counts into display-ready list.
#
#         Args:
#             category_counts: Dictionary mapping category ID to count
#
#         Returns:
#             List of category dictionaries with id, name, and count
#         """
#         category_names = {
#             'line': 'Line Plots',
#             'scatter': 'Scatter Plots',
#             'bar': 'Bar Charts',
#             'distribution': 'Distributions',
#             'statistical': 'Statistical',
#             'heatmap': 'Heatmaps',
#             'contour': 'Contours',
#             'pie': 'Pie Charts',
#             'vector': 'Vector Fields',
#             'error': 'Error Bars',
#             'stem': 'Stem Plots',
#             'other': 'Other',
#         }
#
#         categories = [
#             {
#                 'id': cat_id,
#                 'name': category_names.get(cat_id, cat_id.title()),
#                 'count': count
#             }
#             for cat_id, count in sorted(category_counts.items(), key=lambda x: -x[1])
#         ]
#
#         return categories
#
#     @staticmethod
#     def load_plot_metadata(category: str, plot_name: str) -> Optional[Dict]:
#         """
#         Load plot metadata (axes_bbox_px, figure_size_px, element_bboxes).
#
#         Args:
#             category: Plot category
#             plot_name: Plot name
#
#         Returns:
#             Dictionary with metadata or None if not found
#         """
#         from .gallery_generator import get_template_gallery_path
#
#         # First try temp gallery with element_bboxes (generated by stx.plt.gallery.generate)
#         temp_gallery_path = Path('/tmp/scitex_gallery_with_bboxes')
#         json_path = temp_gallery_path / category / f"{plot_name}.json"
#         logger.info(f'[GalleryService] Checking temp gallery: {json_path} (exists: {json_path.exists()})')
#         if not json_path.exists():
#             # Fallback to original gallery
#             gallery_path = get_template_gallery_path()
#             json_path = gallery_path / category / f"{plot_name}.json"
#             logger.info(f'[GalleryService] Fallback to template gallery: {json_path} (exists: {json_path.exists()})')
#
#         if not json_path.exists():
#             # Try alternate paths in the vis_app static gallery
#             alt_paths = [
#                 Path(settings.BASE_DIR) / 'apps' / 'vis_app' / 'static' / 'vis_app' / 'img' / 'plot_gallery' / '01_matplotlib_basic',
#                 Path(settings.BASE_DIR) / 'apps' / 'vis_app' / 'static' / 'vis_app' / 'img' / 'plot_gallery' / '02_custom_scitex',
#                 Path(settings.BASE_DIR) / 'apps' / 'vis_app' / 'static' / 'vis_app' / 'img' / 'plot_gallery' / '04_seaborn',
#             ]
#
#             for alt_path in alt_paths:
#                 if not alt_path.exists():
#                     continue
#                 # Try different naming patterns
#                 for json_file in alt_path.glob('*.json'):
#                     # Check if plot_name is in the filename (e.g., 02_scatter.json contains "scatter")
#                     stem = json_file.stem.split('_', 1)[-1] if '_' in json_file.stem else json_file.stem
#                     if stem.lower() == plot_name.lower() or plot_name.lower() in json_file.stem.lower():
#                         json_path = json_file
#                         break
#                 if json_path.exists():
#                     break
#
#         if not json_path.exists():
#             return None
#
#         # Load JSON metadata
#         logger.info(f'[GalleryService] Loading JSON: {json_path}')
#         with open(json_path, 'r') as f:
#             metadata = json.load(f)
#
#         logger.info(f'[GalleryService] Metadata keys: {list(metadata.keys())}')
#         logger.info(f'[GalleryService] hitmap_file in metadata: {metadata.get("hitmap_file")}')
#         logger.info(f'[GalleryService] hitmap_color_map in metadata: {"hitmap_color_map" in metadata}')
#
#         result = GalleryService._extract_metadata_fields(metadata)
#         logger.info(f'[GalleryService] Result keys after extract: {list(result.keys()) if result else "None"}')
#
#         # Load hitmap PNG if available and convert to base64
#         if result and result.get('hitmap_file'):
#             hitmap_path = json_path.parent / result['hitmap_file']
#             logger.info(f'[GalleryService] Checking hitmap: {hitmap_path} (exists: {hitmap_path.exists()})')
#             if hitmap_path.exists():
#                 try:
#                     with open(hitmap_path, 'rb') as f:
#                         hitmap_data = f.read()
#                     hitmap_b64 = base64.b64encode(hitmap_data).decode('utf-8')
#                     result['hitmap'] = f'data:image/png;base64,{hitmap_b64}'
#                     logger.info(f'[GalleryService] Loaded hitmap successfully')
#                 except Exception as e:
#                     logger.warning(f'Failed to load hitmap: {e}')
#
#         return result
#
#     @staticmethod
#     def _extract_metadata_fields(metadata: Dict) -> Dict:
#         """
#         Extract axes_bbox_px, figure_size_px, and element_bboxes from metadata.
#         Supports both old and new schema formats.
#
#         Args:
#             metadata: Raw metadata dictionary
#
#         Returns:
#             Extracted fields dictionary
#         """
#         # Old format: axes_bbox_px, dimensions.figure_size_px, element_bboxes
#         # New format (v0.3.0): axes.ax_00.bbox_px, figure.size_px, elements.*.geometry_px.bbox
#         axes_bbox_px = metadata.get('axes_bbox_px')
#         dimensions = metadata.get('dimensions', {})
#         figure_size_px = dimensions.get('figure_size_px')
#         element_bboxes = metadata.get('element_bboxes')
#
#         # Try new schema format (scitex.plt.figure.editable v0.3.0)
#         if not axes_bbox_px and 'axes' in metadata:
#             # Get first axes bbox_px
#             axes_data = metadata.get('axes', {})
#             for ax_id, ax_info in axes_data.items():
#                 if 'bbox_px' in ax_info:
#                     axes_bbox_px = ax_info['bbox_px']
#                     break
#
#         if not figure_size_px and 'figure' in metadata:
#             fig_data = metadata.get('figure', {})
#             size_px = fig_data.get('size_px')
#             if size_px and isinstance(size_px, list) and len(size_px) == 2:
#                 figure_size_px = size_px
#
#         # Extract element bboxes from new schema
#         # Get all axes bboxes for coordinate transformation
#         axes_bboxes = {}
#         if 'axes' in metadata:
#             for ax_id, ax_info in metadata['axes'].items():
#                 if 'bbox_px' in ax_info:
#                     axes_bboxes[ax_id] = ax_info['bbox_px']
#
#         if not element_bboxes and 'elements' in metadata:
#             element_bboxes = {}
#             elements_data = metadata.get('elements', {})
#             for elem_id, elem_info in elements_data.items():
#                 geometry = elem_info.get('geometry_px', {})
#                 bbox = geometry.get('bbox')
#                 if bbox:
#                     coord_space = geometry.get('coord_space', 'figure')
#                     axes_id = elem_info.get('axes_id')
#                     path_simplified = geometry.get('path_simplified')
#
#                     # Transform coordinates from axes-local to figure-local
#                     if coord_space == 'axes' and axes_id and axes_id in axes_bboxes:
#                         ax_bbox = axes_bboxes[axes_id]
#                         ax_x0 = ax_bbox.get('x0', 0)
#                         ax_y0 = ax_bbox.get('y0', 0)
#
#                         # Transform bbox
#                         bbox = {
#                             'x0': bbox['x0'] + ax_x0,
#                             'y0': bbox['y0'] + ax_y0,
#                             'x1': bbox['x1'] + ax_x0,
#                             'y1': bbox['y1'] + ax_y0,
#                         }
#
#                         # Transform path_simplified
#                         if path_simplified:
#                             path_simplified = [
#                                 [pt[0] + ax_x0, pt[1] + ax_y0]
#                                 for pt in path_simplified
#                             ]
#
#                     element_bboxes[elem_id] = {
#                         'bbox': bbox,
#                         'element_type': elem_info.get('element_type'),
#                         'label': elem_info.get('label'),
#                         'axes_id': axes_id,
#                         'path_simplified': path_simplified,
#                     }
#
#         if not axes_bbox_px:
#             return None
#
#         response_data = {
#             'success': True,
#             'axes_bbox_px': axes_bbox_px,
#             'figure_size_px': {
#                 'width': figure_size_px[0] if isinstance(figure_size_px, list) else figure_size_px.get('width'),
#                 'height': figure_size_px[1] if isinstance(figure_size_px, list) else figure_size_px.get('height')
#             } if figure_size_px else None
#         }
#
#         # Include element_bboxes if available (for element-level selection)
#         if element_bboxes:
#             response_data['element_bboxes'] = element_bboxes
#
#         # Include hitmap data if available (for fast element picking)
#         hitmap_color_map = metadata.get('hitmap_color_map')
#         hitmap_file = metadata.get('hitmap_file')
#         if hitmap_color_map:
#             response_data['hitmap_color_map'] = hitmap_color_map
#         if hitmap_file:
#             response_data['hitmap_file'] = hitmap_file
#
#         return response_data
#
#     # =========================================================================
#     # Pltz Bundle Integration Methods
#     # =========================================================================
#
#     @staticmethod
#     def get_pltz_galleries() -> List[Dict]:
#         """
#         Get plot galleries that include pltz bundles.
#
#         Scans for both legacy (png/json/csv) and modern (pltz.d) formats.
#
#         Returns:
#             List of gallery dictionaries with plots in both formats
#         """
#         galleries = GalleryService.get_plot_galleries()
#
#         # Scan for pltz bundles in additional locations
#         pltz_gallery_paths = [
#             SCITEX_CODE_PATH / 'examples' / 'scitex' / 'fig',
#             SCITEX_CODE_PATH / 'examples' / 'scitex' / 'plt',
#         ]
#
#         for gallery_path in pltz_gallery_paths:
#             if not gallery_path.exists():
#                 continue
#
#             pltz_plots = GalleryService._scan_pltz_gallery(gallery_path)
#             if pltz_plots:
#                 galleries.append({
#                     'id': f'pltz_{gallery_path.name}',
#                     'name': f'SciTeX {gallery_path.name.title()}',
#                     'description': f'Pltz bundles from {gallery_path.name}',
#                     'path': gallery_path,
#                     'plots': pltz_plots,
#                     'format': 'pltz',
#                 })
#
#         return galleries
#
#     @staticmethod
#     def _scan_pltz_gallery(base_path: Path) -> List[Dict]:
#         """
#         Scan directory for pltz bundles.
#
#         Args:
#             base_path: Directory to scan
#
#         Returns:
#             List of pltz bundle info dictionaries
#         """
#         bundles = []
#
#         # Find all .pltz.d directories
#         for pltz_dir in sorted(base_path.glob('**/*.pltz.d')):
#             if not PltzService.is_pltz_bundle(pltz_dir):
#                 continue
#
#             try:
#                 bundle_data = PltzService.load_bundle(pltz_dir)
#                 spec = bundle_data.get('spec', {})
#                 style = bundle_data.get('style', {})
#
#                 # Get display name from spec or directory name
#                 plot_id = spec.get('plot_id', pltz_dir.stem.replace('.pltz', ''))
#                 display_name = plot_id.replace('_', ' ').title()
#
#                 # Categorize
#                 category = PltzService.categorize_plot(spec)
#
#                 bundle_info = {
#                     'id': f'pltz_{plot_id}',
#                     'name': display_name,
#                     'category': category,
#                     'format': 'pltz',
#                     'bundle_path': str(pltz_dir),
#                     'spec': spec,
#                     'style': style,
#                     'files': {
#                         'pltz': str(pltz_dir),
#                         'png': bundle_data.get('exports', {}).get('png'),
#                         'csv': str(pltz_dir / 'data.csv') if (pltz_dir / 'data.csv').exists() else None,
#                     }
#                 }
#
#                 bundles.append(bundle_info)
#
#             except Exception as e:
#                 logger.warning(f"Failed to load pltz bundle {pltz_dir}: {e}")
#
#         return bundles
#
#     @staticmethod
#     def load_pltz_from_gallery(
#         category: str,
#         plot_name: str
#     ) -> Optional[Dict]:
#         """
#         Load a pltz bundle from the gallery.
#
#         Args:
#             category: Plot category
#             plot_name: Plot name
#
#         Returns:
#             Full pltz bundle data or None if not found
#         """
#         from .gallery_generator import get_template_gallery_path
#
#         # Check template gallery for pltz bundles
#         gallery_path = get_template_gallery_path()
#         pltz_path = gallery_path / category / f"{plot_name}.pltz.d"
#
#         if pltz_path.exists() and PltzService.is_pltz_bundle(pltz_path):
#             return PltzService.load_bundle(pltz_path)
#
#         # Check temp gallery
#         temp_gallery = Path('/tmp/scitex_gallery_with_bboxes')
#         pltz_path = temp_gallery / category / f"{plot_name}.pltz.d"
#
#         if pltz_path.exists() and PltzService.is_pltz_bundle(pltz_path):
#             return PltzService.load_bundle(pltz_path)
#
#         return None
#
#     @staticmethod
#     def get_pltz_preview_base64(
#         category: str,
#         plot_name: str
#     ) -> Optional[str]:
#         """
#         Get pltz bundle preview as base64 data URL.
#
#         Args:
#             category: Plot category
#             plot_name: Plot name
#
#         Returns:
#             Base64 data URL or None
#         """
#         from .gallery_generator import get_template_gallery_path
#
#         # Check template gallery
#         gallery_path = get_template_gallery_path()
#         pltz_path = gallery_path / category / f"{plot_name}.pltz.d"
#
#         if pltz_path.exists():
#             return PltzService.get_preview_base64(pltz_path)
#
#         # Fallback to temp gallery
#         temp_gallery = Path('/tmp/scitex_gallery_with_bboxes')
#         pltz_path = temp_gallery / category / f"{plot_name}.pltz.d"
#
#         if pltz_path.exists():
#             return PltzService.get_preview_base64(pltz_path)
#
#         return None
#
#     @staticmethod
#     def convert_legacy_to_pltz(
#         png_path: Union[str, Path],
#         json_path: Optional[Union[str, Path]] = None,
#         csv_path: Optional[Union[str, Path]] = None,
#         output_dir: Optional[Union[str, Path]] = None,
#     ) -> Optional[Dict]:
#         """
#         Convert legacy gallery format (png/json/csv) to pltz bundle.
#
#         Args:
#             png_path: Path to PNG file
#             json_path: Path to JSON metadata (optional)
#             csv_path: Path to CSV data (optional)
#             output_dir: Output directory for pltz bundle
#
#         Returns:
#             Created pltz bundle data or None on failure
#         """
#         png_path = Path(png_path)
#         plot_name = png_path.stem
#
#         # Determine output path
#         if output_dir:
#             pltz_path = Path(output_dir) / f"{plot_name}.pltz.d"
#         else:
#             pltz_path = png_path.parent / f"{plot_name}.pltz.d"
#
#         # Load existing metadata if available
#         spec = {}
#         style = {}
#
#         if json_path:
#             json_path = Path(json_path)
#             if json_path.exists():
#                 with open(json_path, 'r') as f:
#                     metadata = json.load(f)
#
#                 # Extract spec from metadata
#                 spec = {
#                     'plot_id': plot_name,
#                     'data': {
#                         'csv': 'data.csv',
#                         'format': 'wide',
#                     },
#                     'axes': [],
#                     'traces': [],
#                 }
#
#                 # Extract axes info if available
#                 if 'axes_bbox_px' in metadata:
#                     spec['axes'].append({
#                         'id': 'ax0',
#                         'role': 'main',
#                         'labels': {},
#                     })
#
#                 # Extract style from metadata
#                 if 'dimensions' in metadata:
#                     dims = metadata['dimensions']
#                     style['size'] = {
#                         'width_mm': dims.get('width_mm', 80),
#                         'height_mm': dims.get('height_mm', 60),
#                     }
#
#         # Load CSV data
#         csv_data = None
#         if csv_path:
#             csv_path = Path(csv_path)
#             if csv_path.exists():
#                 with open(csv_path, 'r') as f:
#                     csv_data = f.read()
#
#         try:
#             # Create pltz bundle
#             result = PltzService.save_bundle(
#                 spec=spec or {'plot_id': plot_name},
#                 style=style or {},
#                 data_csv=csv_data,
#                 output_path=pltz_path,
#                 generate_exports=False,  # Copy existing PNG instead
#             )
#
#             # Copy existing PNG to exports
#             import shutil
#             exports_dir = pltz_path / 'exports'
#             exports_dir.mkdir(exist_ok=True)
#             shutil.copy(png_path, exports_dir / f"{plot_name}.png")
#
#             return result
#
#         except Exception as e:
#             logger.exception(f"Failed to convert to pltz: {e}")
#             return None

# --------------------------------------------------------------------------------
# End of Source Code from: apps/vis_app/services/gallery_service.py
# --------------------------------------------------------------------------------
