#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Plot Type Dispatcher
Imports all plot renderers and provides a unified dispatcher.
"""

from .plot_types_basic import (
    render_line_plot,
    render_scatter_plot,
    render_bar_plot,
    render_barh_plot,
    render_errorbar_plot,
    render_fill_between_plot,
)
from .plot_types_statistical import (
    render_hist_plot,
    render_boxplot_plot,
    render_violin_plot,
    render_raster_plot,
)


# Plot type dispatcher
PLOT_RENDERERS = {
    'line': render_line_plot,
    'scatter': render_scatter_plot,
    'bar': render_bar_plot,
    'barh': render_barh_plot,
    'errorbar': render_errorbar_plot,
    'fill_between': render_fill_between_plot,
    'hist': render_hist_plot,
    'boxplot': render_boxplot_plot,
    'violin': render_violin_plot,
    'raster': render_raster_plot,
}


def render_plot_by_type(ax, df, plot_spec, style_spec):
    """
    Render a plot based on its type.

    Args:
        ax: Matplotlib axis
        df: DataFrame with data
        plot_spec: Plot specification
        style_spec: Style specification

    Returns:
        ax: Modified axis
    """
    plot_kind = plot_spec.get('kind', 'line')

    if plot_kind not in PLOT_RENDERERS:
        supported_types = ', '.join(PLOT_RENDERERS.keys())
        raise ValueError(
            f"Unsupported plot kind: {plot_kind}. "
            f"Supported types: {supported_types}"
        )

    renderer = PLOT_RENDERERS[plot_kind]
    return renderer(ax, df, plot_spec, style_spec)


# EOF
