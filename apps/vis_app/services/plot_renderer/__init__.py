#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Backend Plot Renderer
Uses matplotlib/scitex.plt to render scientific plots from JSON specifications.

This module provides backward compatibility with the original plot_renderer.py
by re-exporting the main rendering function and utilities.
"""

from .constants import MM_PER_INCH, PT_PER_INCH, mm_to_inch, mm_to_pt, pt_to_mm
from .style import apply_nature_style
from .data_loader import load_data_from_spec
from .plot_types import (
    render_line_plot,
    render_scatter_plot,
    render_bar_plot,
    render_barh_plot,
    render_errorbar_plot,
    render_fill_between_plot,
    render_hist_plot,
    render_boxplot_plot,
    render_violin_plot,
    render_raster_plot,
    render_plot_by_type,
)
from .single_plot import render_single_plot, render_single_plot_figure
from .multipanel import render_multipanel_from_spec


def render_plot_from_spec(spec):
    """
    Main renderer function that creates a plot from JSON specification.
    Supports both single plot and multi-panel layouts.

    Args:
        spec: Dictionary containing either:
            Single plot:
                - figure: {width_mm, height_mm, dpi}
                - style: {tick_length_mm, tick_thickness_mm, ...}
                - plot: {kind, csv_path, x_column, y_column, ...}
            Multi-panel:
                - figure: {width_mm, height_mm, dpi}
                - style: {tick_length_mm, tick_thickness_mm, ...}
                - panels: [{id, x_mm, y_mm, width_mm, height_mm, plot: {...}}, ...]

    Returns:
        BytesIO buffer containing SVG data
    """
    # Check if multi-panel or single plot
    if 'panels' in spec:
        return render_multipanel_from_spec(spec)
    else:
        return render_single_plot_figure(spec)


# Backward compatibility exports
__all__ = [
    # Constants
    'MM_PER_INCH',
    'PT_PER_INCH',
    'mm_to_inch',
    'mm_to_pt',
    'pt_to_mm',
    # Style
    'apply_nature_style',
    # Data loading
    'load_data_from_spec',
    # Plot types
    'render_line_plot',
    'render_scatter_plot',
    'render_bar_plot',
    'render_barh_plot',
    'render_errorbar_plot',
    'render_fill_between_plot',
    'render_hist_plot',
    'render_boxplot_plot',
    'render_violin_plot',
    'render_raster_plot',
    'render_plot_by_type',
    # Main renderers
    'render_single_plot',
    'render_multipanel_from_spec',
    'render_plot_from_spec',
]


# EOF
