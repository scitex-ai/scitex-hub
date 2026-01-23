#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Multi-panel Plot Rendering
"""

import io
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt

from .constants import mm_to_inch, mm_to_pt
from .single_plot import render_single_plot


def render_multipanel_from_spec(spec):
    """
    Render a multi-panel figure from JSON specification.

    Args:
        spec: Dictionary containing:
            - figure: {width_mm, height_mm, dpi}
            - style: {tick_length_mm, tick_thickness_mm, ...}
            - panels: [{id, x_mm, y_mm, width_mm, height_mm, plot: {...}}, ...]

    Returns:
        BytesIO buffer containing SVG data
    """
    # Extract specifications
    figure_spec = spec.get('figure', {})
    style_spec = spec.get('style', {})
    panels_spec = spec.get('panels', [])

    if not panels_spec:
        raise ValueError("No panels specified for multi-panel figure")

    # Figure dimensions
    width_mm = figure_spec.get('width_mm', 89)
    height_mm = figure_spec.get('height_mm', 60)
    dpi = figure_spec.get('dpi', 300)

    # Convert to inches for matplotlib
    width_inch = mm_to_inch(width_mm)
    height_inch = mm_to_inch(height_mm)

    # Create empty figure
    fig = plt.figure(figsize=(width_inch, height_inch), dpi=dpi)

    # Apply global style to rcParams
    tick_length_pt = mm_to_pt(style_spec.get('tick_length_mm', 0.8))
    tick_width_pt = mm_to_pt(style_spec.get('tick_thickness_mm', 0.2))
    axis_width_pt = mm_to_pt(style_spec.get('axis_thickness_mm', 0.2))
    trace_width_pt = mm_to_pt(style_spec.get('trace_thickness_mm', 0.12))
    axis_font_size = style_spec.get('axis_font_size_pt', 8)
    tick_font_size = style_spec.get('tick_font_size_pt', 7)
    title_font_size = style_spec.get('title_font_size_pt', 8)

    plt.rcParams.update({
        'font.family': 'Arial',
        'font.size': tick_font_size,
        'axes.linewidth': axis_width_pt,
        'axes.labelsize': axis_font_size,
        'axes.titlesize': title_font_size,
        'xtick.major.size': tick_length_pt,
        'ytick.major.size': tick_length_pt,
        'xtick.major.width': tick_width_pt,
        'ytick.major.width': tick_width_pt,
        'xtick.labelsize': tick_font_size,
        'ytick.labelsize': tick_font_size,
        'lines.linewidth': trace_width_pt,
    })

    # Render each panel
    for panel_spec in panels_spec:
        render_single_plot(fig, panel_spec, style_spec)

    # Save to buffer as SVG with transparent background
    buf = io.BytesIO()
    fig.savefig(buf, format='svg', bbox_inches='tight', dpi=dpi, transparent=True)
    plt.close(fig)

    buf.seek(0)
    return buf


# EOF
