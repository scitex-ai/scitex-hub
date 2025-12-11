"""
Plot Type Gallery API - Serves plot templates and thumbnails from scitex examples.

Provides:
- List of available plot types with thumbnails
- Template JSON for creating new plots
- Categorized plot types (matplotlib, scitex, seaborn)
"""

import base64
import json
import logging
import os
import traceback
from pathlib import Path

from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.conf import settings

logger = logging.getLogger(__name__)


# Base path to scitex-code examples
SCITEX_CODE_PATH = Path(os.environ.get(
    'SCITEX_CODE_PATH',
    '/home/ywatanabe/proj/scitex-code'
))
EXAMPLES_PATH = SCITEX_CODE_PATH / 'examples' / 'plt'


def _get_plot_galleries():
    """Get all plot galleries from examples directory."""
    galleries = []

    # Matplotlib basic plots
    mpl_out = EXAMPLES_PATH / 'demo_matplotlib_basic_out'
    if mpl_out.exists():
        galleries.append({
            'id': 'matplotlib',
            'name': 'Matplotlib',
            'description': 'Standard matplotlib plot types',
            'path': mpl_out,
            'plots': _scan_gallery(mpl_out, 'mpl')
        })

    # SciTeX wrapper plots
    stx_out = EXAMPLES_PATH / 'demo_scitex_wrappers_out'
    if stx_out.exists():
        galleries.append({
            'id': 'scitex',
            'name': 'SciTeX',
            'description': 'SciTeX enhanced plot wrappers',
            'path': stx_out,
            'plots': _scan_gallery(stx_out, 'stx')
        })

    # Seaborn wrapper plots
    sns_out = EXAMPLES_PATH / 'demo_seaborn_wrappers_out'
    if sns_out.exists():
        galleries.append({
            'id': 'seaborn',
            'name': 'Seaborn',
            'description': 'Seaborn statistical plots',
            'path': sns_out,
            'plots': _scan_gallery(sns_out, 'sns')
        })

    return galleries


def _scan_gallery(base_path: Path, prefix: str):
    """Scan gallery directory for plot types."""
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
        category = _categorize_plot(name_part)

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


def _categorize_plot(name: str):
    """Categorize plot by type."""
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


@require_http_methods(["GET"])
def get_plot_galleries(request):
    """
    Get all available plot galleries.

    GET /vis/api/gallery/

    Response:
    {
        "galleries": [
            {
                "id": "matplotlib",
                "name": "Matplotlib",
                "description": "...",
                "plots": [...]
            },
            ...
        ]
    }
    """
    try:
        galleries = _get_plot_galleries()

        # Remove file paths from response (for security)
        for gallery in galleries:
            if 'path' in gallery:
                del gallery['path']

        return JsonResponse({
            'galleries': galleries,
            'total_plots': sum(len(g['plots']) for g in galleries)
        })

    except Exception as e:
        return JsonResponse({
            'error': f'Failed to load galleries: {str(e)}'
        }, status=500)


@require_http_methods(["GET"])
def get_plot_thumbnail(request, gallery_id: str, plot_id: str):
    """
    Get plot thumbnail as base64 or binary.

    GET /vis/api/gallery/<gallery_id>/<plot_id>/thumbnail/

    Query params:
    - format: 'base64' (default) or 'binary'
    - size: 'small' (64px), 'medium' (128px), 'large' (256px)

    Response (base64):
    {
        "thumbnail": "data:image/png;base64,..."
    }

    Response (binary):
    Binary PNG image
    """
    try:
        output_format = request.GET.get('format', 'base64')
        size = request.GET.get('size', 'medium')

        galleries = _get_plot_galleries()
        gallery = next((g for g in galleries if g['id'] == gallery_id), None)

        if not gallery:
            return JsonResponse({'error': f'Gallery not found: {gallery_id}'}, status=404)

        plot = next((p for p in gallery['plots'] if p['id'] == f'{gallery_id[:3]}_{plot_id}'), None)

        if not plot:
            # Try direct match
            plot = next((p for p in gallery['plots'] if plot_id in p['id']), None)

        if not plot or not plot['files']['png']:
            return JsonResponse({'error': f'Plot not found: {plot_id}'}, status=404)

        png_path = Path(plot['files']['png'])
        if not png_path.exists():
            return JsonResponse({'error': 'Thumbnail file not found'}, status=404)

        # Read image
        with open(png_path, 'rb') as f:
            image_data = f.read()

        if output_format == 'binary':
            response = HttpResponse(image_data, content_type='image/png')
            response['Content-Disposition'] = f'inline; filename="{png_path.name}"'
            return response
        else:
            # Base64
            b64_data = base64.b64encode(image_data).decode('utf-8')
            return JsonResponse({
                'thumbnail': f'data:image/png;base64,{b64_data}',
                'name': plot['name'],
                'category': plot['category']
            })

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@require_http_methods(["GET"])
def get_plot_template(request, gallery_id: str, plot_id: str):
    """
    Get plot JSON template for creating new plots.

    GET /vis/api/gallery/<gallery_id>/<plot_id>/template/

    Response:
    {
        "metadata": {...},
        "csv_columns": [...],
        "boilerplate_code": "..."
    }
    """
    try:
        galleries = _get_plot_galleries()
        gallery = next((g for g in galleries if g['id'] == gallery_id), None)

        if not gallery:
            return JsonResponse({'error': f'Gallery not found: {gallery_id}'}, status=404)

        plot = next((p for p in gallery['plots'] if plot_id in p['id']), None)

        if not plot:
            return JsonResponse({'error': f'Plot not found: {plot_id}'}, status=404)

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

        # Generate boilerplate code
        result['boilerplate_code'] = _generate_boilerplate(plot, gallery_id)

        return JsonResponse(result)

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def _generate_boilerplate(plot: dict, gallery_id: str):
    """Generate Python boilerplate code for the plot type."""
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


@require_http_methods(["GET"])
def get_categories(request):
    """
    Get available plot categories.

    GET /vis/api/gallery/categories/

    Response:
    {
        "categories": [
            {"id": "line", "name": "Line Plots", "count": 8},
            ...
        ]
    }
    """
    try:
        galleries = _get_plot_galleries()

        # Count plots by category
        category_counts = {}
        for gallery in galleries:
            for plot in gallery['plots']:
                cat = plot['category']
                if cat not in category_counts:
                    category_counts[cat] = 0
                category_counts[cat] += 1

        # Format categories
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

        return JsonResponse({'categories': categories})

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# =============================================================================
# Project-Based Gallery API (uses stx.plt.gallery.generate)
# =============================================================================

@require_http_methods(["POST"])
def generate_project_gallery(request):
    """
    Generate gallery plots into project's scitex/vis/gallery directory.

    POST /vis/api/gallery/generate/

    Request body:
    {
        "category": "line",  // optional: generate specific category
        "plot_type": "scatter",  // optional: generate specific plot
        "force": false,  // optional: regenerate even if exists
        "figsize": [4, 3],  // optional
        "dpi": 150  // optional
    }

    Response:
    {
        "success": true,
        "path": "/path/to/gallery",
        "png": [...],
        "csv": [...],
        "json": [...]
    }
    """
    import json as json_module
    from apps.project_app.services.project_utils import get_current_project
    from ...services.gallery_generator import generate_gallery

    try:
        # Get current project
        project = get_current_project(request, user=request.user)
        if not project:
            return JsonResponse({
                'error': 'No project selected. Please select a project first.'
            }, status=400)

        # Get project path
        project_path = project.get_local_path()
        if not project_path.exists():
            return JsonResponse({
                'error': f'Project workspace not found: {project_path}'
            }, status=404)

        # Parse request body
        try:
            body = json_module.loads(request.body) if request.body else {}
        except json_module.JSONDecodeError:
            body = {}

        category = body.get('category')
        plot_type = body.get('plot_type')
        force = body.get('force', False)
        figsize = tuple(body.get('figsize', [4, 3]))
        dpi = body.get('dpi', 150)

        # Generate gallery
        result = generate_gallery(
            project_path=project_path,
            category=category,
            plot_type=plot_type,
            figsize=figsize,
            dpi=dpi,
            force=force,
        )

        if result.get('success'):
            return JsonResponse(result)
        else:
            return JsonResponse(result, status=500)

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@require_http_methods(["GET"])
def get_project_gallery(request):
    """
    Get contents of project's gallery.

    GET /vis/api/gallery/project/

    Response:
    {
        "success": true,
        "exists": true,
        "path": "/path/to/gallery",
        "categories": {
            "line": {
                "name": "Line",
                "plots": [...],
                "count": 4
            },
            ...
        },
        "total_plots": 46
    }
    """
    from apps.project_app.services.project_utils import get_current_project
    from ...services.gallery_generator import get_gallery_contents, get_template_gallery_path

    try:
        project = get_current_project(request, user=request.user) if request.user.is_authenticated else None
        if project:
            project_path = project.get_local_path()
            result = get_gallery_contents(project_path, fallback_to_template=True)
        else:
            # No project - use template gallery directly
            template_path = get_template_gallery_path()
            if template_path.exists():
                result = get_gallery_contents(template_path.parent.parent.parent, fallback_to_template=False)
                result['using_template'] = True
            else:
                return JsonResponse({
                    'success': False,
                    'error': 'No gallery available'
                }, status=404)

        return JsonResponse(result)

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@require_http_methods(["GET"])
def get_project_gallery_image(request, category: str, plot_name: str):
    """
    Get a specific plot image from project gallery.

    GET /vis/api/gallery/project/<category>/<plot_name>/image/

    Query params:
    - format: 'base64' (default), 'binary', or 'svg'
    - type: 'png' (default) or 'svg'

    Response (base64):
    {
        "image": "data:image/png;base64,...",
        "name": "plot",
        "category": "line"
    }

    Response (binary):
    Binary PNG image

    Response (svg):
    SVG XML content
    """
    from apps.project_app.services.project_utils import get_current_project
    from ...services.gallery_generator import get_gallery_path, get_template_gallery_path

    try:
        output_format = request.GET.get('format', 'base64')
        image_type = request.GET.get('type', 'svg' if output_format == 'svg' else 'png')

        # Don't pass request.user explicitly - let get_current_project handle anonymous users
        project = get_current_project(request) if request.user.is_authenticated else None
        gallery_path = None

        if project:
            project_path = project.get_local_path()
            gallery_path = get_gallery_path(project_path)

        # For SVG, try SVG file first
        if image_type == 'svg':
            svg_path = None
            if gallery_path:
                svg_path = gallery_path / category / f"{plot_name}.svg"
            if not svg_path or not svg_path.exists():
                gallery_path = get_template_gallery_path()
                svg_path = gallery_path / category / f"{plot_name}.svg"
            if svg_path.exists():
                with open(svg_path, 'r') as f:
                    svg_content = f.read()
                response = HttpResponse(svg_content, content_type='image/svg+xml')
                response['Content-Disposition'] = f'inline; filename="{plot_name}.svg"'
                return response
            # Fall back to PNG if SVG doesn't exist
            image_type = 'png'

        # PNG path
        png_path = None
        if project:
            project_path = project.get_local_path()
            gallery_path = get_gallery_path(project_path)
            png_path = gallery_path / category / f"{plot_name}.png"

        # Fallback to template gallery
        if not png_path or not png_path.exists():
            gallery_path = get_template_gallery_path()
            png_path = gallery_path / category / f"{plot_name}.png"
            if not png_path.exists():
                return JsonResponse({'error': 'Image not found'}, status=404)

        with open(png_path, 'rb') as f:
            image_data = f.read()

        if output_format == 'binary':
            response = HttpResponse(image_data, content_type='image/png')
            response['Content-Disposition'] = f'inline; filename="{png_path.name}"'
            return response
        else:
            b64_data = base64.b64encode(image_data).decode('utf-8')
            result = {
                'image': f'data:image/png;base64,{b64_data}',
                'name': plot_name,
                'category': category
            }
            # Try to load axes_bbox_px from companion JSON
            json_path = png_path.with_suffix('.json')
            if json_path.exists():
                try:
                    with open(json_path, 'r') as f:
                        metadata = json.load(f)
                    if 'axes_bbox_px' in metadata:
                        result['axes_bbox_px'] = metadata['axes_bbox_px']
                except Exception:
                    pass
            return JsonResponse(result)

    except Exception as e:
        logger.error(f"get_project_gallery_image error for {category}/{plot_name}: {e}\n{traceback.format_exc()}")
        return JsonResponse({'error': str(e)}, status=500)


@require_http_methods(["GET"])
def get_project_gallery_csv(request, category: str, plot_name: str):
    """
    Get CSV data for a specific plot from project gallery.

    GET /vis/api/gallery/project/<category>/<plot_name>/csv/

    Response:
    CSV text content
    """
    from apps.project_app.services.project_utils import get_current_project
    from ...services.gallery_generator import get_gallery_path, get_template_gallery_path

    try:
        csv_path = None
        # Don't pass request.user explicitly - let get_current_project handle anonymous users
        project = get_current_project(request) if request.user.is_authenticated else None

        if project:
            project_path = project.get_local_path()
            gallery_path = get_gallery_path(project_path)
            csv_path = gallery_path / category / f"{plot_name}.csv"

        # Fallback to template gallery
        if not csv_path or not csv_path.exists():
            gallery_path = get_template_gallery_path()
            csv_path = gallery_path / category / f"{plot_name}.csv"
            if not csv_path.exists():
                return JsonResponse({'error': 'CSV not found'}, status=404)

        with open(csv_path, 'r') as f:
            csv_content = f.read()

        response = HttpResponse(csv_content, content_type='text/csv')
        response['Content-Disposition'] = f'inline; filename="{csv_path.name}"'
        return response

    except Exception as e:
        logger.error(f"get_project_gallery_csv error for {category}/{plot_name}: {e}\n{traceback.format_exc()}")
        return JsonResponse({'error': str(e)}, status=500)


@require_http_methods(["GET"])
def list_gallery_categories_available(request):
    """
    List available categories from stx.plt.gallery (not project-specific).

    GET /vis/api/gallery/available/

    Response:
    {
        "success": true,
        "categories": {
            "line": {"name": "Line Plots", "plots": [...], "description": "..."},
            ...
        },
        "total_plots": 46
    }
    """
    from ...services.gallery_generator import list_gallery_categories

    try:
        result = list_gallery_categories()
        return JsonResponse(result)

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@require_http_methods(["GET"])
def get_plot_metadata(request, category: str, plot_name: str):
    """
    Get axis metadata (axes_bbox_px) for a plot from gallery.
    Used for snap/align by axis position.

    GET /vis/api/gallery/metadata/<category>/<plot_name>/

    Response:
    {
        "success": true,
        "axes_bbox_px": {"x0": 236, "y0": 236, "x1": 708, "y1": 566, ...},
        "figure_size_px": {"width": 944, "height": 803}
    }
    """
    from ...services.gallery_generator import get_template_gallery_path

    try:
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
            return JsonResponse({
                'success': False,
                'error': f'Metadata not found for {category}/{plot_name}'
            }, status=404)

        # Load JSON metadata
        with open(json_path, 'r') as f:
            metadata = json.load(f)

        # Extract axes_bbox_px and figure_size_px - support both old and new schema formats
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
            return JsonResponse({
                'success': False,
                'error': 'No axes_bbox_px in metadata'
            }, status=404)

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

        return JsonResponse(response_data)

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)
