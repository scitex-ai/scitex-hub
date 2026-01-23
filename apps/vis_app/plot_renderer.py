#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Backend Plot Renderer
Uses matplotlib/scitex.plt to render scientific plots from JSON specifications.

BACKWARD COMPATIBILITY MODULE:
This module now imports from the refactored services/plot_renderer/ package.
All functionality has been preserved for backward compatibility.
"""

from .services.plot_renderer import (
    # Constants
    MM_PER_INCH,
    PT_PER_INCH,
    mm_to_inch,
    mm_to_pt,
    pt_to_mm,
    # Style
    apply_nature_style,
    # Plot types
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
    # Main renderers
    render_single_plot,
    render_multipanel_from_spec,
    render_plot_from_spec,
)

__all__ = [
    # Constants
    'MM_PER_INCH',
    'PT_PER_INCH',
    'mm_to_inch',
    'mm_to_pt',
    'pt_to_mm',
    # Style
    'apply_nature_style',
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
    # Main renderers
    'render_single_plot',
    'render_multipanel_from_spec',
    'render_plot_from_spec',
]


# EOF
