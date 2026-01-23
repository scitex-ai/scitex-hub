#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Timestamp: "2025-12-02 03:35:00 (ywatanabe)"
# File: /home/ywatanabe/proj/scitex-cloud/apps/public_app/views/status/chart_renderer.py

"""
Chart renderer following demo_matplotlib_basic.py pattern STRICTLY.
Uses @stx.session with SCITEX_STYLE.
"""

import scitex as stx
from scitex.plt.styles.presets import SCITEX_STYLE


@stx.session
def render_chart(
    timestamps,
    data,
    config,
    output_path,
    width_mm=80,
    height_mm=50,
    plt=stx.INJECTED,
    logger=stx.INJECTED,
):
    """Render a single chart to file."""
    STYLE = SCITEX_STYLE.copy()
    STYLE['axes_width_mm'] = width_mm
    STYLE['axes_height_mm'] = height_mm

    fig, ax = stx.plt.subplots(**STYLE)

    # Plot
    if isinstance(data, dict):
        colors = config.get('colors', ['#4BC0C0', '#FF9F40'])
        labels = config.get('labels', list(data.keys()))
        for i, (key, values) in enumerate(data.items()):
            y = values[:len(timestamps)]
            ax.plot(timestamps[:len(y)], y, color=colors[i % len(colors)],
                   linewidth=1, label=labels[i] if i < len(labels) else key)
        ax.legend(fontsize=6, loc='upper right', frameon=False)
    else:
        color = config.get('color', '#36A2EB')
        y = data[:len(timestamps)]
        ax.plot(timestamps[:len(y)], y, color=color, linewidth=1)
        if config.get('fill', False):
            ax.fill_between(timestamps[:len(y)], y, alpha=0.2, color=color)

    # Y limits
    if 'y_max' in config:
        ax.set_ylim(0, config['y_max'])
    else:
        ax.set_ylim(bottom=0)

    # Format x-axis
    import matplotlib.dates as mdates
    ax_mpl = ax._axis_mpl if hasattr(ax, '_axis_mpl') else ax
    ax_mpl.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
    ax_mpl.xaxis.set_major_locator(mdates.AutoDateLocator(minticks=3, maxticks=5))

    stx.io.save(fig, output_path)
    fig.close()

    return 0


# EOF
