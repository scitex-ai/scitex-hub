"""
Gallery Service - Business logic for plot gallery operations.

Handles:
- Scanning gallery directories for plot files
- Categorizing plots by type
- Loading plot thumbnails and templates
- Generating boilerplate code
- Loading plot metadata
"""

import base64
import json
import logging
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from django.conf import settings

logger = logging.getLogger(__name__)


# Base path to scitex-code examples
SCITEX_CODE_PATH = Path(os.environ.get(
    'SCITEX_CODE_PATH',
    '/home/ywatanabe/proj/scitex-code'
))
EXAMPLES_PATH = SCITEX_CODE_PATH / 'examples' / 'plt'


class GalleryService:
    """Service for gallery-related operations."""

    @staticmethod
    def get_plot_galleries() -> List[Dict]:
        """
        Get all plot galleries from examples directory.

        Returns:
            List of gallery dictionaries with id, name, description, path, and plots
        """
        galleries = []

        # Matplotlib basic plots
        mpl_out = EXAMPLES_PATH / 'demo_matplotlib_basic_out'
        if mpl_out.exists():
            galleries.append({
                'id': 'matplotlib',
                'name': 'Matplotlib',
                'description': 'Standard matplotlib plot types',
                'path': mpl_out,
                'plots': GalleryService._scan_gallery(mpl_out, 'mpl')
            })

        # SciTeX wrapper plots
        stx_out = EXAMPLES_PATH / 'demo_scitex_wrappers_out'
        if stx_out.exists():
            galleries.append({
                'id': 'scitex',
                'name': 'SciTeX',
                'description': 'SciTeX enhanced plot wrappers',
                'path': stx_out,
                'plots': GalleryService._scan_gallery(stx_out, 'stx')
            })

        # Seaborn wrapper plots
        sns_out = EXAMPLES_PATH / 'demo_seaborn_wrappers_out'
        if sns_out.exists():
            galleries.append({
                'id': 'seaborn',
                'name': 'Seaborn',
                'description': 'Seaborn statistical plots',
                'path': sns_out,
                'plots': GalleryService._scan_gallery(sns_out, 'sns')
            })

        return galleries

    @staticmethod
    def _scan_gallery(base_path: Path, prefix: str) -> List[Dict]:
        """
        Scan gallery directory for plot types.

        Args:
            base_path: Base directory to scan
            prefix: Prefix for plot IDs (e.g., 'mpl', 'stx', 'sns')

        Returns:
            List of plot info dictionaries
        """
        plots = []

        png_dir = base_path / 'png'
        json_dir = base_path / 'json'
        csv_dir = base_path / 'csv'

        if not png_dir.exists():
            return plots

        for png_file in sorted(png_dir.glob('*.png')):
            stem = png_file.stem
            json_file = json_dir / f'{stem}.json'
            csv_file = csv_dir / f'{stem}.csv'

            # Parse plot name from filename (e.g., "01_plot" -> "Plot")
            parts = stem.split('_', 1)
            number = parts[0] if len(parts) > 1 else ''
            name_part = parts[1] if len(parts) > 1 else stem

            # Clean up name
            display_name = name_part.replace('_', ' ').title()

            # Categorize by plot type
            category = GalleryService._categorize_plot(name_part)

            plot_info = {
                'id': f'{prefix}_{stem}',
                'name': display_name,
                'category': category,
                'number': number,
                'files': {
                    'png': str(png_file),
                    'json': str(json_file) if json_file.exists() else None,
                    'csv': str(csv_file) if csv_file.exists() else None,
                }
            }

            plots.append(plot_info)

        return plots

    @staticmethod
    def _categorize_plot(name: str) -> str:
        """
        Categorize plot by type based on name.

        Args:
            name: Plot name to categorize

        Returns:
            Category string
        """
        name_lower = name.lower()

        if any(x in name_lower for x in ['line', 'plot', 'step', 'mean', 'median', 'shaded']):
            return 'line'
        elif any(x in name_lower for x in ['scatter']):
            return 'scatter'
        elif any(x in name_lower for x in ['bar', 'barh']):
            return 'bar'
        elif any(x in name_lower for x in ['hist', 'kde', 'ecdf']):
            return 'distribution'
        elif any(x in name_lower for x in ['box', 'violin', 'strip', 'swarm', 'joyplot']):
            return 'statistical'
        elif any(x in name_lower for x in ['heatmap', 'imshow', 'matshow', 'conf_mat', 'image']):
            return 'heatmap'
        elif any(x in name_lower for x in ['contour', 'hexbin', 'fill']):
            return 'contour'
        elif any(x in name_lower for x in ['pie']):
            return 'pie'
        elif any(x in name_lower for x in ['quiver', 'stream', 'raster']):
            return 'vector'
        elif any(x in name_lower for x in ['errorbar']):
            return 'error'
        elif any(x in name_lower for x in ['stem']):
            return 'stem'
        else:
            return 'other'

    @staticmethod
    def find_plot_in_galleries(gallery_id: str, plot_id: str) -> Optional[Tuple[Dict, Dict]]:
        """
        Find a plot in galleries.

        Args:
            gallery_id: Gallery identifier
            plot_id: Plot identifier

        Returns:
            Tuple of (gallery, plot) or None if not found
        """
        galleries = GalleryService.get_plot_galleries()
        gallery = next((g for g in galleries if g['id'] == gallery_id), None)

        if not gallery:
            return None

        plot = next((p for p in gallery['plots'] if p['id'] == f'{gallery_id[:3]}_{plot_id}'), None)

        if not plot:
            # Try direct match
            plot = next((p for p in gallery['plots'] if plot_id in p['id']), None)

        if not plot:
            return None

        return gallery, plot

    @staticmethod
    def load_thumbnail(png_path: Path) -> bytes:
        """
        Load thumbnail image data.

        Args:
            png_path: Path to PNG file

        Returns:
            Binary image data

        Raises:
            FileNotFoundError: If file doesn't exist
        """
        if not png_path.exists():
            raise FileNotFoundError(f'Thumbnail file not found: {png_path}')

        with open(png_path, 'rb') as f:
            return f.read()

    @staticmethod
    def encode_thumbnail_base64(image_data: bytes) -> str:
        """
        Encode image data as base64 data URL.

        Args:
            image_data: Binary image data

        Returns:
            Base64 data URL string
        """
        b64_data = base64.b64encode(image_data).decode('utf-8')
        return f'data:image/png;base64,{b64_data}'

    @staticmethod
    def load_plot_template(plot: Dict) -> Dict:
        """
        Load plot template data (JSON metadata and CSV columns).

        Args:
            plot: Plot info dictionary

        Returns:
            Dictionary with metadata and CSV columns
        """
        result = {
            'id': plot['id'],
            'name': plot['name'],
            'category': plot['category'],
        }

        # Load JSON metadata if exists
        if plot['files']['json']:
            json_path = Path(plot['files']['json'])
            if json_path.exists():
                with open(json_path, 'r') as f:
                    result['metadata'] = json.load(f)
                # Extract axes_bbox_px for easy access
                if 'axes_bbox_px' in result['metadata']:
                    result['axes_bbox_px'] = result['metadata']['axes_bbox_px']

        # Load CSV columns if exists
        if plot['files']['csv']:
            csv_path = Path(plot['files']['csv'])
            if csv_path.exists():
                with open(csv_path, 'r') as f:
                    header = f.readline().strip()
                    result['csv_columns'] = header.split(',')

        return result

    @staticmethod
    def generate_boilerplate(plot: dict, gallery_id: str) -> str:
        """
        Generate Python boilerplate code for the plot type.

        Args:
            plot: Plot info dictionary
            gallery_id: Gallery identifier

        Returns:
            Python code string
        """
        name = plot['name'].lower().replace(' ', '_')

        if gallery_id == 'matplotlib':
            return f'''import scitex as stx

fig, ax = stx.plt.subplots()
# ax.{name}(x, y)
stx.io.save(fig, "output/{name}.png")
'''
        elif gallery_id == 'scitex':
            # SciTeX wrappers use stx_xxx naming (e.g., stx_line, stx_bar)
            method = name.replace('stx_', '').replace('plot_', '')
            return f'''import scitex as stx

fig, ax = stx.plt.subplots()
# ax.stx_{method}(x, y)
stx.io.save(fig, "output/stx_{method}.png")
'''
        elif gallery_id == 'seaborn':
            method = name.replace('sns_', '')
            return f'''import scitex as stx

fig, ax = stx.plt.subplots()
# ax.sns_{method}(data=df, x="x", y="y")
stx.io.save(fig, "output/sns_{method}.png")
'''
        else:
            return '# Plot code here'

    @staticmethod
    def get_category_counts() -> Dict[str, int]:
        """
        Count plots by category across all galleries.

        Returns:
            Dictionary mapping category ID to count
        """
        galleries = GalleryService.get_plot_galleries()

        category_counts = {}
        for gallery in galleries:
            for plot in gallery['plots']:
                cat = plot['category']
                if cat not in category_counts:
                    category_counts[cat] = 0
                category_counts[cat] += 1

        return category_counts

    @staticmethod
    def format_categories(category_counts: Dict[str, int]) -> List[Dict]:
        """
        Format category counts into display-ready list.

        Args:
            category_counts: Dictionary mapping category ID to count

        Returns:
            List of category dictionaries with id, name, and count
        """
        category_names = {
            'line': 'Line Plots',
            'scatter': 'Scatter Plots',
            'bar': 'Bar Charts',
            'distribution': 'Distributions',
            'statistical': 'Statistical',
            'heatmap': 'Heatmaps',
            'contour': 'Contours',
            'pie': 'Pie Charts',
            'vector': 'Vector Fields',
            'error': 'Error Bars',
            'stem': 'Stem Plots',
            'other': 'Other',
        }

        categories = [
            {
                'id': cat_id,
                'name': category_names.get(cat_id, cat_id.title()),
                'count': count
            }
            for cat_id, count in sorted(category_counts.items(), key=lambda x: -x[1])
        ]

        return categories

    @staticmethod
    def load_plot_metadata(category: str, plot_name: str) -> Optional[Dict]:
        """
        Load plot metadata (axes_bbox_px, figure_size_px, element_bboxes).

        Args:
            category: Plot category
            plot_name: Plot name

        Returns:
            Dictionary with metadata or None if not found
        """
        from .gallery_generator import get_template_gallery_path

        # Try to find JSON metadata in original gallery
        gallery_path = get_template_gallery_path()
        json_path = gallery_path / category / f"{plot_name}.json"

        if not json_path.exists():
            # Try alternate paths in the vis_app static gallery
            alt_paths = [
                Path(settings.BASE_DIR) / 'apps' / 'vis_app' / 'static' / 'vis_app' / 'img' / 'plot_gallery' / '01_matplotlib_basic',
                Path(settings.BASE_DIR) / 'apps' / 'vis_app' / 'static' / 'vis_app' / 'img' / 'plot_gallery' / '02_custom_scitex',
                Path(settings.BASE_DIR) / 'apps' / 'vis_app' / 'static' / 'vis_app' / 'img' / 'plot_gallery' / '04_seaborn',
            ]

            for alt_path in alt_paths:
                if not alt_path.exists():
                    continue
                # Try different naming patterns
                for json_file in alt_path.glob('*.json'):
                    # Check if plot_name is in the filename (e.g., 02_scatter.json contains "scatter")
                    stem = json_file.stem.split('_', 1)[-1] if '_' in json_file.stem else json_file.stem
                    if stem.lower() == plot_name.lower() or plot_name.lower() in json_file.stem.lower():
                        json_path = json_file
                        break
                if json_path.exists():
                    break

        if not json_path.exists():
            return None

        # Load JSON metadata
        with open(json_path, 'r') as f:
            metadata = json.load(f)

        return GalleryService._extract_metadata_fields(metadata)

    @staticmethod
    def _extract_metadata_fields(metadata: Dict) -> Dict:
        """
        Extract axes_bbox_px, figure_size_px, and element_bboxes from metadata.
        Supports both old and new schema formats.

        Args:
            metadata: Raw metadata dictionary

        Returns:
            Extracted fields dictionary
        """
        # Old format: axes_bbox_px, dimensions.figure_size_px, element_bboxes
        # New format (v0.3.0): axes.ax_00.bbox_px, figure.size_px, elements.*.geometry_px.bbox
        axes_bbox_px = metadata.get('axes_bbox_px')
        dimensions = metadata.get('dimensions', {})
        figure_size_px = dimensions.get('figure_size_px')
        element_bboxes = metadata.get('element_bboxes')

        # Try new schema format (scitex.plt.figure.editable v0.3.0)
        if not axes_bbox_px and 'axes' in metadata:
            # Get first axes bbox_px
            axes_data = metadata.get('axes', {})
            for ax_id, ax_info in axes_data.items():
                if 'bbox_px' in ax_info:
                    axes_bbox_px = ax_info['bbox_px']
                    break

        if not figure_size_px and 'figure' in metadata:
            fig_data = metadata.get('figure', {})
            size_px = fig_data.get('size_px')
            if size_px and isinstance(size_px, list) and len(size_px) == 2:
                figure_size_px = size_px

        # Extract element bboxes from new schema
        # Get all axes bboxes for coordinate transformation
        axes_bboxes = {}
        if 'axes' in metadata:
            for ax_id, ax_info in metadata['axes'].items():
                if 'bbox_px' in ax_info:
                    axes_bboxes[ax_id] = ax_info['bbox_px']

        if not element_bboxes and 'elements' in metadata:
            element_bboxes = {}
            elements_data = metadata.get('elements', {})
            for elem_id, elem_info in elements_data.items():
                geometry = elem_info.get('geometry_px', {})
                bbox = geometry.get('bbox')
                if bbox:
                    coord_space = geometry.get('coord_space', 'figure')
                    axes_id = elem_info.get('axes_id')
                    path_simplified = geometry.get('path_simplified')

                    # Transform coordinates from axes-local to figure-local
                    if coord_space == 'axes' and axes_id and axes_id in axes_bboxes:
                        ax_bbox = axes_bboxes[axes_id]
                        ax_x0 = ax_bbox.get('x0', 0)
                        ax_y0 = ax_bbox.get('y0', 0)

                        # Transform bbox
                        bbox = {
                            'x0': bbox['x0'] + ax_x0,
                            'y0': bbox['y0'] + ax_y0,
                            'x1': bbox['x1'] + ax_x0,
                            'y1': bbox['y1'] + ax_y0,
                        }

                        # Transform path_simplified
                        if path_simplified:
                            path_simplified = [
                                [pt[0] + ax_x0, pt[1] + ax_y0]
                                for pt in path_simplified
                            ]

                    element_bboxes[elem_id] = {
                        'bbox': bbox,
                        'element_type': elem_info.get('element_type'),
                        'label': elem_info.get('label'),
                        'axes_id': axes_id,
                        'path_simplified': path_simplified,
                    }

        if not axes_bbox_px:
            return None

        response_data = {
            'success': True,
            'axes_bbox_px': axes_bbox_px,
            'figure_size_px': {
                'width': figure_size_px[0] if isinstance(figure_size_px, list) else figure_size_px.get('width'),
                'height': figure_size_px[1] if isinstance(figure_size_px, list) else figure_size_px.get('height')
            } if figure_size_px else None
        }

        # Include element_bboxes if available (for element-level selection)
        if element_bboxes:
            response_data['element_bboxes'] = element_bboxes

        return response_data
