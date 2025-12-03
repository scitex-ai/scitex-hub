"""
Plot Type Gallery API - Serves plot templates and thumbnails from scitex examples.

Provides:
- List of available plot types with thumbnails
- Template JSON for creating new plots
- Categorized plot types (matplotlib, scitex, seaborn)
"""

import base64
import json
import os
from pathlib import Path

from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.conf import settings


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
