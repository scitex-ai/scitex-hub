#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Style Application for Scientific Plots
"""

import matplotlib.pyplot as plt
from .constants import mm_to_pt


def apply_nature_style(fig, ax, style):
    """
    Apply Nature journal style specifications with scientific plotting defaults.

    Args:
        fig: Matplotlib figure
        ax: Matplotlib axis
        style: Style dictionary with parameters in mm/pt
    """
    # Convert mm to pt
    tick_length_pt = mm_to_pt(style.get('tick_length_mm', 0.8))
    tick_width_pt = mm_to_pt(style.get('tick_thickness_mm', 0.2))
    axis_width_pt = mm_to_pt(style.get('axis_thickness_mm', 0.2))
    trace_width_pt = mm_to_pt(style.get('trace_thickness_mm', 0.12))

    # Font sizes
    axis_font_size = style.get('axis_font_size_pt', 8)
    tick_font_size = style.get('tick_font_size_pt', 7)
    title_font_size = style.get('title_font_size_pt', 8)

    # Apply to rcParams
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
        'savefig.transparent': True,  # Transparent background by default
        'figure.facecolor': 'none',   # No figure background
        'axes.facecolor': 'none',     # No axes background
    })

    # Hide top and right spines (scientific plot style)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)

    return fig, ax


# EOF
