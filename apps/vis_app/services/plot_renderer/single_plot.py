#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Single Plot Rendering
"""

import io
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt

from .constants import mm_to_inch, mm_to_pt
from .style import apply_nature_style
from .data_loader import load_data_from_spec
from .plot_types import render_plot_by_type


def extract_axis_metadata(fig, ax, dpi):
    """
    Extract axis bounding box and spine positions in pixels.
    Used for snap/align by axis in the canvas editor.

    Args:
        fig: Matplotlib figure
        ax: Matplotlib axes
        dpi: DPI of the figure

    Returns:
        dict: Axis metadata including spine positions in pixels
    """
    # Force a draw to get accurate positions
    fig.canvas.draw()

    # Get figure dimensions in pixels
    fig_width_px = fig.get_figwidth() * dpi
    fig_height_px = fig.get_figheight() * dpi

    # Get axes bounding box in figure coordinates (0-1)
    bbox_norm = ax.get_position()

    # Convert to pixels (origin at top-left for web/canvas)
    axes_bbox_px = {
        'left': bbox_norm.x0 * fig_width_px,
        'right': bbox_norm.x1 * fig_width_px,
        'top': (1 - bbox_norm.y1) * fig_height_px,  # Flip Y for web
        'bottom': (1 - bbox_norm.y0) * fig_height_px,
        'width': bbox_norm.width * fig_width_px,
        'height': bbox_norm.height * fig_height_px,
    }

    # Get spine positions in pixels (display coordinates)
    spines_px = {}
    for spine_name, spine in ax.spines.items():
        if spine.get_visible():
            try:
                # Get the spine's window extent (display pixels)
                bbox_display = spine.get_window_extent(fig.canvas.get_renderer())
                # Convert Y coordinate (matplotlib Y=0 is bottom, web Y=0 is top)
                spines_px[spine_name] = {
                    'x0': bbox_display.x0,
                    'y0': fig_height_px - bbox_display.y1,  # Flip Y
                    'x1': bbox_display.x1,
                    'y1': fig_height_px - bbox_display.y0,  # Flip Y
                    'visible': True
                }
            except Exception:
                pass

    # Get axis limits (data coordinates)
    xlim = ax.get_xlim()
    ylim = ax.get_ylim()

    return {
        'dpi': dpi,
        'figure_size_px': {
            'width': fig_width_px,
            'height': fig_height_px
        },
        'axes_bbox_px': axes_bbox_px,
        'spines_px': spines_px,
        'xlim': list(xlim),
        'ylim': list(ylim),
    }


def render_single_plot(fig, panel_spec, style_spec):
    """
    Render a single plot on a specific axes within a figure.

    Args:
        fig: Matplotlib figure
        panel_spec: Panel specification with position and plot details
        style_spec: Style specifications

    Returns:
        ax: The created axes
    """
    # Get panel position in mm
    x_mm = panel_spec.get('x_mm', 0)
    y_mm = panel_spec.get('y_mm', 0)
    width_mm = panel_spec.get('width_mm', 35)
    height_mm = panel_spec.get('height_mm', 24.5)

    # Get figure dimensions
    fig_width_inch, fig_height_inch = fig.get_size_inches()

    # Convert mm to normalized figure coordinates (0-1)
    # Note: matplotlib origin is bottom-left
    x_norm = mm_to_inch(x_mm) / fig_width_inch
    y_norm = mm_to_inch(y_mm) / fig_height_inch
    width_norm = mm_to_inch(width_mm) / fig_width_inch
    height_norm = mm_to_inch(height_mm) / fig_height_inch

    # Create axes at specified position
    ax = fig.add_axes([x_norm, y_norm, width_norm, height_norm])

    # Apply style (but don't apply to figure again)
    tick_length_pt = mm_to_pt(style_spec.get('tick_length_mm', 0.8))
    tick_width_pt = mm_to_pt(style_spec.get('tick_thickness_mm', 0.2))
    axis_width_pt = mm_to_pt(style_spec.get('axis_thickness_mm', 0.2))

    ax.tick_params(
        axis='both',
        which='both',
        length=tick_length_pt,
        width=tick_width_pt,
    )

    # Set spine width and hide top/right spines (scientific style)
    for spine_name, spine in ax.spines.items():
        spine.set_linewidth(axis_width_pt)
        if spine_name in ['top', 'right']:
            spine.set_visible(False)

    # Get plot specification
    plot_spec = panel_spec.get('plot', {})

    # Load data
    df = load_data_from_spec(plot_spec)

    # Render plot based on kind
    ax = render_plot_by_type(ax, df, plot_spec, style_spec)

    # Add panel ID label if provided
    panel_id = panel_spec.get('id')
    if panel_id:
        # Place label at top-left corner
        ax.text(
            -0.15, 1.05, panel_id,
            transform=ax.transAxes,
            fontsize=style_spec.get('title_font_size_pt', 8),
            fontweight='bold',
            va='bottom'
        )

    return ax


def render_single_plot_figure(spec, return_metadata=False):
    """
    Render a single plot as a complete figure.

    Args:
        spec: Dictionary containing:
            - figure: {width_mm, height_mm, dpi}
            - style: {tick_length_mm, tick_thickness_mm, ...}
            - plot: {kind, csv_path, x_column, y_column, ...}
        return_metadata: If True, also return axis metadata for snap/align

    Returns:
        BytesIO buffer containing SVG data
        (optionally) tuple of (buffer, metadata) if return_metadata=True
    """
    # Extract specifications
    figure_spec = spec.get('figure', {})
    style_spec = spec.get('style', {})
    plot_spec = spec.get('plot', {})

    # Figure dimensions
    width_mm = figure_spec.get('width_mm', 35)
    height_mm = figure_spec.get('height_mm', 24.5)
    dpi = figure_spec.get('dpi', 300)

    # Convert to inches for matplotlib
    width_inch = mm_to_inch(width_mm)
    height_inch = mm_to_inch(height_mm)

    # Create figure
    fig, ax = plt.subplots(figsize=(width_inch, height_inch), dpi=dpi)

    # Apply Nature style
    fig, ax = apply_nature_style(fig, ax, style_spec)

    # Load data
    df = load_data_from_spec(plot_spec)

    # Render plot based on kind
    ax = render_plot_by_type(ax, df, plot_spec, style_spec)

    # Adjust layout
    fig.tight_layout()

    # Extract metadata before saving (if requested)
    metadata = None
    if return_metadata:
        metadata = extract_axis_metadata(fig, ax, dpi)

    # Save to buffer as SVG with transparent background
    buf = io.BytesIO()
    fig.savefig(buf, format='svg', bbox_inches='tight', dpi=dpi, transparent=True)
    plt.close(fig)

    buf.seek(0)

    if return_metadata:
        return buf, metadata
    return buf


# EOF
