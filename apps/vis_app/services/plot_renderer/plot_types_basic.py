#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Basic Plot Type Renderers
Line, scatter, bar, and error bar plots.
"""

from .constants import mm_to_pt


def render_line_plot(ax, df, plot_spec, style):
    """Render a line plot."""
    x_col = plot_spec.get('x_column', 'x')
    y_col = plot_spec.get('y_column', 'y')
    color = plot_spec.get('color', 'blue')

    x = df[x_col] if x_col in df.columns else range(len(df))
    y = df[y_col] if y_col in df.columns else df.iloc[:, 0]

    # Convert line width from mm to pt
    linewidth = mm_to_pt(style.get('trace_thickness_mm', 0.12))

    ax.plot(x, y, color=color, linewidth=linewidth)

    if plot_spec.get('xlabel'):
        ax.set_xlabel(plot_spec['xlabel'])
    if plot_spec.get('ylabel'):
        ax.set_ylabel(plot_spec['ylabel'])
    if plot_spec.get('title'):
        ax.set_title(plot_spec['title'])

    return ax


def render_scatter_plot(ax, df, plot_spec, style):
    """Render a scatter plot."""
    x_col = plot_spec.get('x_column', 'x')
    y_col = plot_spec.get('y_column', 'y')
    color = plot_spec.get('color', 'blue')

    x = df[x_col] if x_col in df.columns else range(len(df))
    y = df[y_col] if y_col in df.columns else df.iloc[:, 0]

    # Marker size in mm to pt
    marker_size_mm = style.get('dot_size_mm', 0.8)
    marker_size_pt = mm_to_pt(marker_size_mm)

    ax.scatter(x, y, color=color, s=marker_size_pt**2)

    if plot_spec.get('xlabel'):
        ax.set_xlabel(plot_spec['xlabel'])
    if plot_spec.get('ylabel'):
        ax.set_ylabel(plot_spec['ylabel'])
    if plot_spec.get('title'):
        ax.set_title(plot_spec['title'])

    return ax


def render_bar_plot(ax, df, plot_spec, style):
    """Render a bar plot."""
    x_col = plot_spec.get('x_column', 'x')
    y_col = plot_spec.get('y_column', 'y')
    color = plot_spec.get('color', 'blue')

    x = df[x_col] if x_col in df.columns else range(len(df))
    y = df[y_col] if y_col in df.columns else df.iloc[:, 0]

    # Bar width
    width = plot_spec.get('bar_width', 0.8)

    ax.bar(x, y, color=color, width=width)

    if plot_spec.get('xlabel'):
        ax.set_xlabel(plot_spec['xlabel'])
    if plot_spec.get('ylabel'):
        ax.set_ylabel(plot_spec['ylabel'])
    if plot_spec.get('title'):
        ax.set_title(plot_spec['title'])

    return ax


def render_barh_plot(ax, df, plot_spec, style):
    """Render a horizontal bar plot."""
    x_col = plot_spec.get('x_column', 'x')
    y_col = plot_spec.get('y_column', 'y')
    color = plot_spec.get('color', 'blue')

    x = df[x_col] if x_col in df.columns else range(len(df))
    y = df[y_col] if y_col in df.columns else df.iloc[:, 0]

    width = plot_spec.get('bar_width', 0.8)
    ax.barh(x, y, color=color, height=width)

    if plot_spec.get('xlabel'):
        ax.set_xlabel(plot_spec['xlabel'])
    if plot_spec.get('ylabel'):
        ax.set_ylabel(plot_spec['ylabel'])
    if plot_spec.get('title'):
        ax.set_title(plot_spec['title'])

    return ax


def render_errorbar_plot(ax, df, plot_spec, style):
    """Render an error bar plot."""
    x_col = plot_spec.get('x_column', 'x')
    y_col = plot_spec.get('y_column', 'y')
    yerr_col = plot_spec.get('yerr_column', 'yerr')
    color = plot_spec.get('color', 'blue')

    x = df[x_col] if x_col in df.columns else range(len(df))
    y = df[y_col] if y_col in df.columns else df.iloc[:, 0]
    yerr = df[yerr_col] if yerr_col in df.columns else None

    linewidth = mm_to_pt(style.get('trace_thickness_mm', 0.12))

    ax.errorbar(x, y, yerr=yerr, color=color, linewidth=linewidth,
                capsize=3, capthick=linewidth)

    if plot_spec.get('xlabel'):
        ax.set_xlabel(plot_spec['xlabel'])
    if plot_spec.get('ylabel'):
        ax.set_ylabel(plot_spec['ylabel'])
    if plot_spec.get('title'):
        ax.set_title(plot_spec['title'])

    return ax


def render_fill_between_plot(ax, df, plot_spec, style):
    """Render a fill_between plot for confidence intervals."""
    x_col = plot_spec.get('x_column', 'x')
    y_col = plot_spec.get('y_column', 'y')
    y_lower_col = plot_spec.get('y_lower_column', 'y_lower')
    y_upper_col = plot_spec.get('y_upper_column', 'y_upper')
    color = plot_spec.get('color', 'blue')

    x = df[x_col] if x_col in df.columns else range(len(df))
    y = df[y_col] if y_col in df.columns else df.iloc[:, 0]

    # Draw center line
    linewidth = mm_to_pt(style.get('trace_thickness_mm', 0.12))
    ax.plot(x, y, color=color, linewidth=linewidth)

    # Fill confidence interval if available
    if y_lower_col in df.columns and y_upper_col in df.columns:
        y_lower = df[y_lower_col]
        y_upper = df[y_upper_col]
        ax.fill_between(x, y_lower, y_upper, color=color, alpha=0.2)

    if plot_spec.get('xlabel'):
        ax.set_xlabel(plot_spec['xlabel'])
    if plot_spec.get('ylabel'):
        ax.set_ylabel(plot_spec['ylabel'])
    if plot_spec.get('title'):
        ax.set_title(plot_spec['title'])

    return ax


# EOF
