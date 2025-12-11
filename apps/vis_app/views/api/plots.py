"""
Scientific Figure Editor - Plot Rendering API Views
REST API endpoints for backend plot rendering using matplotlib/scitex.plt
"""

import json
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt

from apps.vis_app.plot_renderer import render_plot_from_spec


@require_http_methods(["POST"])
@csrf_exempt
def render_plot(request):
    """
    Render a scientific plot from JSON specification.

    POST /api/vis/plot/

    Request body (JSON):
    {
      "figure": {"width_mm": 35, "height_mm": 24.5, "dpi": 300},
      "style": {"tick_length_mm": 0.8, ...},
      "plot": {"kind": "line", "csv_path": "...", ...}
    }

    Response:
    - Success: SVG image (Content-Type: image/svg+xml)
    - Error: JSON with error details
    """
    try:
        spec = json.loads(request.body)

        # Validate required fields
        if 'figure' not in spec:
            return JsonResponse({
                'error': 'Missing required field: figure is required'
            }, status=400)

        if 'plot' not in spec and 'panels' not in spec:
            return JsonResponse({
                'error': 'Missing required field: either plot or panels is required'
            }, status=400)

        # Render plot using matplotlib backend
        svg_buffer = render_plot_from_spec(spec)

        # Return SVG
        return HttpResponse(
            svg_buffer.getvalue(),
            content_type='image/svg+xml'
        )

    except json.JSONDecodeError:
        return JsonResponse({
            'error': 'Invalid JSON data'
        }, status=400)

    except ValueError as e:
        return JsonResponse({
            'error': str(e)
        }, status=400)

    except Exception as e:
        return JsonResponse({
            'error': f'Internal server error: {str(e)}'
        }, status=500)


@require_http_methods(["POST"])
@csrf_exempt
def render_gallery_plot(request):
    """
    Render a plot from gallery template with CSV data.

    POST /vis/api/plot/gallery/

    Request body (JSON):
    {
        "plot_type": "plot",           # e.g., plot, scatter, bar, hist
        "category": "line",            # e.g., line, scatter, categorical
        "csv_data": [[...], ...],      # 2D array of data
        "overrides": {                 # Optional style overrides
            "title": "My Plot",
            "xlabel": "X",
            "ylabel": "Y",
            "linewidth": 1.0,
            ...
        }
    }

    Response (success):
    {
        "success": true,
        "image": "data:image/png;base64,...",
        "width": 800,
        "height": 600
    }
    """
    import base64
    import io
    import os

    try:
        data = json.loads(request.body)
        plot_type = data.get('plot_type', 'plot')
        category = data.get('category', 'line')
        csv_data = data.get('csv_data', [])
        overrides = data.get('overrides', {})

        if not csv_data or len(csv_data) < 2:
            return JsonResponse({
                'success': False,
                'error': 'CSV data must have at least 2 rows (header + data)'
            }, status=400)

        # Set matplotlib backend
        os.environ['MPLBACKEND'] = 'Agg'

        try:
            import scitex as stx
            import pandas as pd
            import numpy as np
        except ImportError as e:
            return JsonResponse({
                'success': False,
                'error': f'Required package not available: {e}'
            }, status=500)

        # Convert CSV data to DataFrame
        headers = csv_data[0]
        rows = csv_data[1:]
        df = pd.DataFrame(rows, columns=headers)

        # Convert numeric columns
        for col in df.columns:
            try:
                df[col] = pd.to_numeric(df[col])
            except (ValueError, TypeError):
                pass

        # Get figure size from overrides or defaults
        fig_width = overrides.get('fig_width', 4)
        fig_height = overrides.get('fig_height', 3)
        dpi = overrides.get('dpi', 150)

        # Create figure with scitex
        fig, ax = stx.plt.subplots(figsize=(fig_width, fig_height))

        # Plot based on type
        _render_plot_by_type(ax, df, plot_type, category, overrides)

        # Apply common styling
        _apply_plot_styling(ax, overrides)

        fig.tight_layout()

        # Draw figure to get accurate renderer
        fig.canvas.draw()
        renderer = fig.canvas.get_renderer()

        # Save to buffer first to get actual image dimensions
        buf = io.BytesIO()
        fig.savefig(buf, format='png', dpi=dpi, bbox_inches='tight',
                    facecolor='white', edgecolor='none')
        buf.seek(0)

        # Get actual image dimensions
        from PIL import Image
        img = Image.open(buf)
        width, height = img.size
        buf.seek(0)

        # Extract element bboxes for element-level selection
        from apps.vis_app.services.plot_renderer.element_bboxes import extract_element_bboxes
        element_bboxes = extract_element_bboxes(fig, ax, renderer, width, height)

        # Add column mapping to data elements (for CSV column highlighting)
        cols = df.columns.tolist()
        x_col = overrides.get('x_column', cols[0] if len(cols) > 0 else None)
        y_cols = overrides.get('y_columns', cols[1:] if len(cols) > 1 else [])
        if isinstance(y_cols, str):
            y_cols = [y_cols]

        # Map element names to their CSV columns
        for element_name, bbox in element_bboxes.items():
            element_type = bbox.get('element_type', '')
            label = bbox.get('label', '')

            if element_type in ['line', 'scatter']:
                # For traces, use trace_idx if available, otherwise try label matching
                trace_idx = bbox.get('trace_idx')
                matched_y_col = None
                matched_y_idx = None

                if trace_idx is not None and trace_idx < len(y_cols):
                    # Direct mapping by trace index
                    matched_y_col = y_cols[trace_idx]
                    matched_y_idx = cols.index(matched_y_col) if matched_y_col in cols else trace_idx + 1
                else:
                    # Fallback: try to match by label
                    for idx, y_col in enumerate(y_cols):
                        if y_col in label or label == y_col:
                            matched_y_col = y_col
                            matched_y_idx = cols.index(y_col) if y_col in cols else idx + 1
                            break

                if matched_y_col:
                    x_col_idx = cols.index(x_col) if x_col in cols else 0
                    bbox['csv_columns'] = {
                        'x': {'name': x_col, 'index': x_col_idx},
                        'y': {'name': matched_y_col, 'index': matched_y_idx}
                    }

            elif element_type in ['bar', 'hist', 'boxplot', 'violin']:
                # For distribution plots (boxplot, violin), handle single-column data
                if element_type in ['boxplot', 'violin'] and len(y_cols) == 0 and len(cols) > 0:
                    # Single column case: the only column IS the data
                    data_col = cols[0]
                    data_col_idx = 0
                    bbox['csv_columns'] = {
                        'y': {'name': data_col, 'index': data_col_idx}
                    }
                elif len(y_cols) > 0 and y_cols[0] in cols:
                    # Standard case: use first y column
                    x_col_idx = cols.index(x_col) if x_col in cols else 0
                    y_col_idx = cols.index(y_cols[0])
                    bbox['csv_columns'] = {
                        'x': {'name': x_col, 'index': x_col_idx},
                        'y': {'name': y_cols[0], 'index': y_col_idx}
                    }

        # Extract axes_bbox_px (backward compatible)
        axes_bbox_px = element_bboxes.get('panel', {})
        if axes_bbox_px:
            axes_bbox_px = {
                'x0': axes_bbox_px.get('x0', 0),
                'y0': axes_bbox_px.get('y0', 0),
                'x1': axes_bbox_px.get('x1', 0),
                'y1': axes_bbox_px.get('y1', 0),
                'width': axes_bbox_px.get('x1', 0) - axes_bbox_px.get('x0', 0),
                'height': axes_bbox_px.get('y1', 0) - axes_bbox_px.get('y0', 0),
            }

        # Encode to base64
        img_base64 = base64.b64encode(buf.read()).decode('utf-8')

        # Close figure (use fig.close() for FigWrapper compatibility)
        if hasattr(fig, 'close'):
            fig.close()
        else:
            import matplotlib.pyplot as plt
            plt.close(fig)

        return JsonResponse({
            'success': True,
            'image': f'data:image/png;base64,{img_base64}',
            'width': width,
            'height': height,
            'axes_bbox_px': axes_bbox_px,
            'element_bboxes': element_bboxes
        })

    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON data'
        }, status=400)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


def _detect_xy_column_pairs(cols: list) -> list:
    """
    Detect paired X/Y columns from scitex gallery CSV format.

    Column naming convention: ax-row-X-col-Y_trace-id-NAME_variable-{x|y}

    Returns:
        List of (x_col, y_col, trace_name) tuples for each detected trace
    """
    import re

    pairs = []
    y_cols = []
    x_cols = []

    for col in cols:
        if col.endswith('_variable-y') or col.endswith('variable_y'):
            y_cols.append(col)
        elif col.endswith('_variable-x') or col.endswith('variable_x'):
            x_cols.append(col)

    # Match Y columns with their X counterparts
    for y_col in y_cols:
        # Extract trace ID from column name
        base = y_col.replace('_variable-y', '').replace('variable_y', '')

        # Find matching X column
        x_col = None
        for xc in x_cols:
            xc_base = xc.replace('_variable-x', '').replace('variable_x', '')
            if xc_base == base:
                x_col = xc
                break

        if x_col is None and x_cols:
            # Use first X column if no exact match
            x_col = x_cols[0]

        # Extract trace name for label
        match = re.search(r'trace-id-([^_]+)', y_col)
        trace_name = match.group(1).replace('-', ' ') if match else y_col

        if x_col:
            pairs.append((x_col, y_col, trace_name))

    return pairs


def _render_plot_by_type(ax, df, plot_type: str, category: str, overrides: dict):
    """Render plot based on type using scitex methods."""
    import numpy as np

    # Get column names
    cols = df.columns.tolist()

    # Detect paired X/Y columns from scitex gallery format (variable-x / variable-y suffixes)
    # Returns list of (x_col, y_col, trace_name) tuples
    xy_pairs = _detect_xy_column_pairs(cols)

    if xy_pairs:
        # Use detected X/Y pairs
        x_col = xy_pairs[0][0]  # Use first X column as default
        y_cols = [pair[1] for pair in xy_pairs]  # All Y columns
    else:
        # Fallback: Default x and y columns
        x_col = overrides.get('x_column', cols[0] if len(cols) > 0 else None)
        y_cols = overrides.get('y_columns', cols[1:] if len(cols) > 1 else [])

    if isinstance(y_cols, str):
        y_cols = [y_cols]

    # Get data
    x = df[x_col].values if x_col and x_col in df.columns else np.arange(len(df))

    # Line plots - use paired X/Y columns if available
    if plot_type in ['plot', 'line', 'stx_line']:
        if xy_pairs:
            # Use detected X/Y pairs with proper trace names
            for x_col_i, y_col, trace_name in xy_pairs:
                if x_col_i in df.columns and y_col in df.columns:
                    x_data = df[x_col_i].values
                    y_data = df[y_col].values
                    ax.plot(x_data, y_data, label=trace_name, linewidth=overrides.get('linewidth', 1.0))
        else:
            for y_col in y_cols:
                if y_col in df.columns:
                    y = df[y_col].values
                    ax.plot(x, y, label=y_col, linewidth=overrides.get('linewidth', 1.0))

    elif plot_type == 'step':
        if xy_pairs:
            for x_col_i, y_col, trace_name in xy_pairs:
                if x_col_i in df.columns and y_col in df.columns:
                    x_data = df[x_col_i].values
                    y_data = df[y_col].values
                    ax.step(x_data, y_data, label=trace_name, linewidth=overrides.get('linewidth', 1.0))
        else:
            for y_col in y_cols:
                if y_col in df.columns:
                    y = df[y_col].values
                    ax.step(x, y, label=y_col, linewidth=overrides.get('linewidth', 1.0))

    elif plot_type == 'stx_shaded_line':
        if xy_pairs:
            for x_col_i, y_col, trace_name in xy_pairs:
                if x_col_i in df.columns and y_col in df.columns:
                    x_data = df[x_col_i].values
                    y_data = df[y_col].values
                    ax.plot(x_data, y_data, label=trace_name)
                    ax.fill_between(x_data, y_data, alpha=0.3)
        else:
            for y_col in y_cols:
                if y_col in df.columns:
                    y = df[y_col].values
                    ax.plot(x, y, label=y_col)
                    ax.fill_between(x, y, alpha=0.3)

    # Scatter plots
    elif plot_type == 'scatter':
        if xy_pairs:
            for x_col_i, y_col, trace_name in xy_pairs:
                if x_col_i in df.columns and y_col in df.columns:
                    x_data = df[x_col_i].values
                    y_data = df[y_col].values
                    ax.scatter(x_data, y_data, label=trace_name, s=overrides.get('marker_size', 20))
        else:
            for y_col in y_cols:
                if y_col in df.columns:
                    y = df[y_col].values
                    ax.scatter(x, y, label=y_col, s=overrides.get('marker_size', 20))

    elif plot_type == 'stx_scatter':
        for y_col in y_cols:
            if y_col in df.columns:
                y = df[y_col].values
                # Use actual stx_scatter method if available
                if hasattr(ax, 'stx_scatter'):
                    ax.stx_scatter(x, y, label=y_col, s=overrides.get('marker_size', 20))
                else:
                    ax.scatter(x, y, label=y_col, s=overrides.get('marker_size', 20))

    # Bar plots
    elif plot_type == 'bar':
        if len(y_cols) > 0 and y_cols[0] in df.columns:
            y = df[y_cols[0]].values
            ax.bar(x, y)

    elif plot_type == 'stx_bar':
        if len(y_cols) > 0 and y_cols[0] in df.columns:
            y = df[y_cols[0]].values
            if hasattr(ax, 'stx_bar'):
                ax.stx_bar(x, y)
            else:
                ax.bar(x, y)

    elif plot_type == 'barh':
        if len(y_cols) > 0 and y_cols[0] in df.columns:
            y = df[y_cols[0]].values
            ax.barh(x, y)

    elif plot_type == 'stx_barh':
        if len(y_cols) > 0 and y_cols[0] in df.columns:
            y = df[y_cols[0]].values
            if hasattr(ax, 'stx_barh'):
                ax.stx_barh(x, y)
            else:
                ax.barh(x, y)

    # Distribution plots
    elif plot_type == 'hist':
        for y_col in y_cols:
            if y_col in df.columns:
                ax.hist(df[y_col].values, bins=overrides.get('bins', 30),
                        alpha=0.7, label=y_col)

    elif plot_type == 'stx_hist':
        for y_col in y_cols:
            if y_col in df.columns:
                if hasattr(ax, 'stx_hist'):
                    ax.stx_hist(df[y_col].values, bins=overrides.get('bins', 30), label=y_col)
                else:
                    ax.hist(df[y_col].values, bins=overrides.get('bins', 30),
                            alpha=0.7, label=y_col)

    elif plot_type == 'boxplot':
        # For distribution plots, use y_cols if available, otherwise use all columns
        plot_cols = y_cols if y_cols else cols
        data = [df[col].dropna().values for col in plot_cols if col in df.columns]
        if data:
            ax.boxplot(data, labels=[c for c in plot_cols if c in df.columns])

    elif plot_type == 'stx_boxplot':
        plot_cols = y_cols if y_cols else cols
        data = [df[col].dropna().values for col in plot_cols if col in df.columns]
        if data:
            if hasattr(ax, 'stx_boxplot'):
                ax.stx_boxplot(data, labels=[c for c in plot_cols if c in df.columns])
            else:
                ax.boxplot(data, labels=[c for c in plot_cols if c in df.columns])

    elif plot_type == 'violin':
        plot_cols = y_cols if y_cols else cols
        data = [df[col].dropna().values for col in plot_cols if col in df.columns]
        if data:
            ax.violinplot(data)

    elif plot_type == 'stx_violin':
        plot_cols = y_cols if y_cols else cols
        data = [df[col].dropna().values for col in plot_cols if col in df.columns]
        if data:
            if hasattr(ax, 'stx_violin'):
                ax.stx_violin(data)
            else:
                ax.violinplot(data)

    # Statistical plots
    elif plot_type in ['stx_mean_std', 'errorbar']:
        for y_col in y_cols:
            if y_col in df.columns:
                y = df[y_col].values
                ax.errorbar(x, y, yerr=np.std(y) * 0.1, label=y_col, capsize=3)

    # Heatmap/imshow
    elif plot_type in ['imshow', 'heatmap', 'stx_heatmap']:
        # Use numeric columns as matrix
        numeric_df = df.select_dtypes(include=[np.number])
        if not numeric_df.empty:
            ax.imshow(numeric_df.values, aspect='auto', cmap='viridis')

    # Default: try line plot
    else:
        for y_col in y_cols:
            if y_col in df.columns:
                y = df[y_col].values
                ax.plot(x, y, label=y_col)

    # Add legend if multiple series
    if len(y_cols) > 1:
        ax.legend(frameon=False)


def _apply_plot_styling(ax, overrides: dict):
    """Apply common styling from overrides."""
    # Labels
    if overrides.get('title'):
        ax.set_title(overrides['title'], fontsize=overrides.get('title_fontsize', 10))
    if overrides.get('xlabel'):
        ax.set_xlabel(overrides['xlabel'], fontsize=overrides.get('axis_fontsize', 9))
    if overrides.get('ylabel'):
        ax.set_ylabel(overrides['ylabel'], fontsize=overrides.get('axis_fontsize', 9))

    # Axis limits
    if overrides.get('xlim'):
        ax.set_xlim(overrides['xlim'])
    if overrides.get('ylim'):
        ax.set_ylim(overrides['ylim'])

    # Grid
    if overrides.get('grid', False):
        ax.grid(True, alpha=0.3)

    # Spines
    if overrides.get('hide_top_spine', True):
        ax.spines['top'].set_visible(False)
    if overrides.get('hide_right_spine', True):
        ax.spines['right'].set_visible(False)

    # Tick styling
    tick_fontsize = overrides.get('tick_fontsize', 8)
    ax.tick_params(axis='both', labelsize=tick_fontsize)


@require_http_methods(["POST"])
@csrf_exempt
def upload_plot_data(request):
    """
    Upload CSV or Excel file for plot rendering.

    POST /api/vis/upload-plot-data/

    Request: multipart/form-data with 'file' field

    Response:
    - Success: JSON with file_path
    - Error: JSON with error details
    """
    try:
        if 'file' not in request.FILES:
            return JsonResponse({
                'error': 'No file uploaded'
            }, status=400)

        uploaded_file = request.FILES['file']

        # Validate file extension
        allowed_extensions = ['.csv', '.xlsx', '.xls']
        file_ext = '.' + uploaded_file.name.split('.')[-1].lower()

        if file_ext not in allowed_extensions:
            return JsonResponse({
                'error': f'Invalid file type. Allowed: {", ".join(allowed_extensions)}'
            }, status=400)

        # Save to temporary directory
        import tempfile
        import os
        from pathlib import Path

        # Create temp directory for uploaded plot data
        temp_dir = Path(tempfile.gettempdir()) / 'scitex_plot_data'
        temp_dir.mkdir(exist_ok=True)

        # Generate unique filename
        import uuid
        unique_filename = f"{uuid.uuid4()}{file_ext}"
        file_path = temp_dir / unique_filename

        # Save file
        with open(file_path, 'wb+') as destination:
            for chunk in uploaded_file.chunks():
                destination.write(chunk)

        return JsonResponse({
            'success': True,
            'file_path': str(file_path),
            'filename': uploaded_file.name,
            'size': uploaded_file.size
        })

    except Exception as e:
        return JsonResponse({
            'error': f'Upload failed: {str(e)}'
        }, status=500)


@require_http_methods(["POST"])
@csrf_exempt
def extract_image_metadata(request):
    """
    Extract scitex metadata embedded in a PNG image.

    POST /vis/api/plot/metadata/

    Request body (JSON):
    {
        "image": "data:image/png;base64,..." or base64 string
    }

    Response (success):
    {
        "success": true,
        "has_metadata": true,
        "metadata": {...},
        "axes_bbox_px": {"x0": ..., "y0": ..., "x1": ..., "y1": ...}
    }
    """
    import base64
    import io
    import tempfile
    import os

    try:
        data = json.loads(request.body)
        image_data = data.get('image', '')

        # Remove data URL prefix if present
        if image_data.startswith('data:'):
            # Extract base64 part: data:image/png;base64,XXXXX
            try:
                image_data = image_data.split(',', 1)[1]
            except IndexError:
                return JsonResponse({
                    'success': False,
                    'error': 'Invalid data URL format'
                }, status=400)

        # Decode base64 to bytes
        try:
            image_bytes = base64.b64decode(image_data)
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': f'Invalid base64 data: {e}'
            }, status=400)

        # Save to temp file to use scitex.io.read_metadata
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
            tmp.write(image_bytes)
            tmp_path = tmp.name

        try:
            # Try to use scitex.io to read metadata
            try:
                from scitex.io._metadata import read_metadata
                metadata = read_metadata(tmp_path)
            except ImportError:
                # Fall back to PIL if scitex not available
                from PIL import Image
                img = Image.open(tmp_path)
                metadata = None
                if hasattr(img, 'info') and 'scitex_metadata' in img.info:
                    import json as json_module
                    try:
                        metadata = json_module.loads(img.info['scitex_metadata'])
                    except:
                        pass
                img.close()

            if not metadata:
                return JsonResponse({
                    'success': True,
                    'has_metadata': False,
                    'message': 'No scitex metadata found in image'
                })

            # Extract axes_bbox_px from metadata
            # SciTeX stores it in axes[0].bbox_px format
            axes_bbox_px = None
            figure_size_px = None

            # Check for axes metadata
            if 'axes' in metadata and len(metadata['axes']) > 0:
                ax_meta = metadata['axes'][0]
                if 'bbox_px' in ax_meta:
                    bbox = ax_meta['bbox_px']
                    # Convert from x_left/y_top format to x0/y0 format
                    axes_bbox_px = {
                        'x0': bbox.get('x_left', 0),
                        'y0': bbox.get('y_top', 0),
                        'x1': bbox.get('x_right', 0),
                        'y1': bbox.get('y_bottom', 0),
                        'width': bbox.get('width', 0),
                        'height': bbox.get('height', 0),
                    }

            # Check for figure dimensions
            if 'dimensions' in metadata:
                dims = metadata['dimensions']
                if 'figure_size_px' in dims:
                    size = dims['figure_size_px']
                    if isinstance(size, list):
                        figure_size_px = {'width': size[0], 'height': size[1]}
                    else:
                        figure_size_px = size

            # Also check top-level axes_bbox_px (older format)
            if not axes_bbox_px and 'axes_bbox_px' in metadata:
                axes_bbox_px = metadata['axes_bbox_px']

            return JsonResponse({
                'success': True,
                'has_metadata': True,
                'metadata': metadata,
                'axes_bbox_px': axes_bbox_px,
                'figure_size_px': figure_size_px
            })

        finally:
            # Clean up temp file
            try:
                os.unlink(tmp_path)
            except:
                pass

    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON data'
        }, status=400)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)
