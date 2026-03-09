#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Multi-panel and style override demos for publication gallery."""

import os

import numpy as np
import scitex as stx
from scitex.plt.presets import SCITEX_STYLE

from ._demo_utils import OUTPUT_DIR, OUTPUT_DIR_MULTI, save_multi_format


def demo_publication_multi_panel_2x2():
    """Publication-ready 2x2 multi-panel figure."""
    print("\n" + "=" * 70)
    print("Demo: Multi-Panel Figure 2x2 (SciTeX Style)")
    print("=" * 70)
    fig, axes = stx.plt.subplots(2, 2, **SCITEX_STYLE)
    np.random.seed(42)

    # Panel A: Line plot
    x = np.linspace(0, 2 * np.pi, 100)
    axes[0, 0].plot(x, np.sin(x), "b-", label="sin", id="panel_a")
    axes[0, 0].set_xlabel(stx.plt.ax.format_label("x", "rad"))
    axes[0, 0].set_ylabel(stx.plt.ax.format_label("sin(x)", ""))
    axes[0, 0].set_title("A. Sine Wave", loc="left", fontweight="bold")
    axes[0, 0].legend(frameon=False)

    # Panel B: Scatter
    x_s = np.random.normal(0, 1, 50)
    y_s = x_s + np.random.normal(0, 0.5, 50)
    scatter = axes[0, 1].scatter(x_s, y_s, alpha=0.6, label="Data", id="panel_b")
    stx.plt.ax.style_scatter(scatter, size_mm=0.8)
    axes[0, 1].set_xlabel(stx.plt.ax.format_label("x", "a.u."))
    axes[0, 1].set_ylabel(stx.plt.ax.format_label("y", "a.u."))
    axes[0, 1].set_title("B. Correlation", loc="left", fontweight="bold")
    axes[0, 1].legend(frameon=False)

    # Panel C: Histogram
    data = np.random.normal(0, 1, 500)
    axes[1, 0].hist(
        data, bins=20, alpha=0.7, color="steelblue", label="Data", id="panel_c"
    )
    axes[1, 0].set_xlabel(stx.plt.ax.format_label("Value", "a.u."))
    axes[1, 0].set_ylabel(stx.plt.ax.format_label("Count", ""))
    axes[1, 0].set_title("C. Distribution", loc="left", fontweight="bold")
    axes[1, 0].legend(frameon=False)

    # Panel D: Bar
    categories = ["A", "B", "C", "D"]
    values = [23, 45, 31, 52]
    bars = axes[1, 1].bar(
        categories, values, alpha=0.7, color="steelblue", label="Count", id="panel_d"
    )
    stx.plt.ax.style_barplot(bars, edge_thickness_mm=0.2, edgecolor="black")
    axes[1, 1].set_xlabel(stx.plt.ax.format_label("Category", ""))
    axes[1, 1].set_ylabel(stx.plt.ax.format_label("Count", ""))
    axes[1, 1].set_title("D. Comparison", loc="left", fontweight="bold")
    axes[1, 1].legend(frameon=False)

    save_path = os.path.join(OUTPUT_DIR_MULTI, "01_2x2_scitex.png")
    png_path, _, _ = save_multi_format(fig, save_path, dpi=300)
    fig.close()
    print(f"- Saved: {png_path}, .pdf, .jpg")
    print("  Layout: 2x2 grid")
    print(
        f"  Each panel: {SCITEX_STYLE['ax_width_mm']} x "
        f"{SCITEX_STYLE['ax_height_mm']} mm"
    )


def demo_publication_multi_panel_1x3():
    """Publication-ready 1x3 multi-panel figure with varied widths."""
    print("\n" + "=" * 70)
    print("Demo: Multi-Panel Figure 1x3 with Individual Widths")
    print("=" * 70)
    fig, axes = stx.plt.subplots(
        1,
        3,
        ax_width_mm=[25, 35, 25],
        ax_height_mm=21,
        margin_left_mm=5,
        margin_right_mm=2,
        margin_bottom_mm=5,
        margin_top_mm=2,
        space_w_mm=3,
        ax_thickness_mm=0.2,
        tick_length_mm=0.8,
        mode="publication",
        dpi=300,
    )
    np.random.seed(42)

    # Panel A: Time series
    t = np.linspace(0, 10, 100)
    axes[0, 0].plot(t, np.sin(t), "b-", label="Signal", id="ts")
    axes[0, 0].set_xlabel(stx.plt.ax.format_label("Time", "s"))
    axes[0, 0].set_ylabel(stx.plt.ax.format_label("Signal", "a.u."))
    axes[0, 0].set_title("A", loc="left", fontweight="bold")
    axes[0, 0].legend(frameon=False)

    # Panel B: Heatmap
    data = np.random.rand(10, 15)
    im = axes[0, 1].imshow(data, aspect="equal", cmap="viridis", id="heat")
    axes[0, 1].spines[:].set_visible(True)
    axes[0, 1].set_xlabel(stx.plt.ax.format_label("X", ""))
    axes[0, 1].set_ylabel(stx.plt.ax.format_label("Y", ""))
    axes[0, 1].set_title("B", loc="left", fontweight="bold")

    # Panel C: Box plot
    box_data = [np.random.normal(0, 1, 100) for _ in range(4)]
    bp = axes[0, 2].boxplot(box_data, labels=["1", "2", "3", "4"], id="box")
    stx.plt.ax.style_boxplot(bp, linewidth_mm=0.8)
    axes[0, 2].set_xlabel(stx.plt.ax.format_label("Group", ""))
    axes[0, 2].set_ylabel(stx.plt.ax.format_label("Value", "a.u."))
    axes[0, 2].set_title("C", loc="left", fontweight="bold")

    save_path = os.path.join(OUTPUT_DIR_MULTI, "02_1x3_varied_widths.png")
    png_path, _, _ = save_multi_format(fig, save_path, dpi=300)
    fig.close()
    print(f"- Saved: {png_path}, .pdf, .jpg")
    print("  Layout: 1x3 grid")
    print("  Panel widths: 25, 35, 25 mm")


def demo_publication_style_override():
    """Demonstrate style override pattern."""
    print("\n" + "=" * 70)
    print("Demo: Style Override Pattern")
    print("=" * 70)
    custom_style = SCITEX_STYLE.copy()
    custom_style["ax_width_mm"] = 40
    custom_style["ax_thickness_mm"] = 0.3
    custom_style["tick_length_mm"] = 1.0

    fig, ax = stx.plt.subplots(**custom_style)
    x = np.linspace(0, 10, 100)
    y = np.exp(-x / 5) * np.sin(2 * x)
    ax.plot(x, y, "b-", label="Oscillation", id="damped_osc")
    ax.set_xlabel(stx.plt.ax.format_label("Time", "s"))
    ax.set_ylabel(stx.plt.ax.format_label("Amplitude", "a.u."))
    ax.set_title("Damped Oscillation (Custom Style)")
    ax.legend(frameon=False)
    ax.grid(True, alpha=0.3)

    style_overrides = {
        "ax_width_mm": custom_style["ax_width_mm"],
        "ax_thickness_mm": custom_style["ax_thickness_mm"],
        "tick_length_mm": custom_style["tick_length_mm"],
    }
    save_path = os.path.join(OUTPUT_DIR, "style_override.png")
    png_path, _, _ = save_multi_format(
        fig,
        save_path,
        dpi=300,
        plot_type="line",
        style_name="SCITEX_STYLE",
        style_overrides=style_overrides,
    )
    fig.close()
    print(f"- Saved: {png_path}, .pdf, .jpg")


MULTI_DEMOS = [
    demo_publication_multi_panel_2x2,
    demo_publication_multi_panel_1x3,
    demo_publication_style_override,
]

# EOF
