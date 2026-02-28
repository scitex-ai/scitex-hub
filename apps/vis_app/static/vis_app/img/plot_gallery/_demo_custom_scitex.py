#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Custom scitex plot demos for publication gallery."""

import os

import numpy as np
import scitex as stx
from scitex.plt.presets import SCITEX_STYLE

from ._demo_utils import OUTPUT_DIR_CUSTOM, OUTPUT_DIR_FUNCTIONAL, save_multi_format


def demo_publication_plot_heatmap():
    """Publication-ready heatmap using plot_heatmap."""
    print("\n" + "=" * 70)
    print("Demo: Publication Heatmap (Custom Scitex)")
    print("=" * 70)
    style = SCITEX_STYLE.copy()
    style["ax_width_mm"] = 45
    style["ax_height_mm"] = 30
    fig, ax = stx.plt.subplots(**style)
    np.random.seed(42)
    data = np.random.rand(8, 12)
    x_labels = [f"X{i + 1}" for i in range(8)]
    y_labels = [f"Y{i + 1}" for i in range(12)]
    ax.plot_heatmap(
        data,
        x_labels=x_labels,
        y_labels=y_labels,
        cbar_label="Values",
        show_annot=True,
        value_format="{x:.2f}",
        cmap="viridis",
        id="heatmap",
    )
    ax.set_title("Data Matrix")
    save_path = os.path.join(OUTPUT_DIR_CUSTOM, "01_plot_heatmap.png")
    png_path, _, _ = save_multi_format(fig, save_path, dpi=300)
    fig.close()
    print(f"- Saved: {png_path}, .pdf, .jpg")


def demo_publication_plot_line():
    """Publication-ready line using plot_line."""
    print("\n" + "=" * 70)
    print("Demo: Publication Line (Custom Scitex)")
    print("=" * 70)
    fig, ax = stx.plt.subplots(**SCITEX_STYLE)
    x = np.linspace(0, 10, 100)
    ax.plot_line(np.sin(x), label="Signal", id="line")
    ax.set_xlabel(stx.plt.ax.format_label("Sample", ""))
    ax.set_ylabel(stx.plt.ax.format_label("Amplitude", "a.u."))
    ax.set_title("Signal Trace")
    ax.legend(frameon=False)
    save_path = os.path.join(OUTPUT_DIR_CUSTOM, "02_plot_line.png")
    png_path, _, _ = save_multi_format(fig, save_path, dpi=300)
    fig.close()
    print(f"- Saved: {png_path}, .pdf, .jpg")


def demo_publication_plot_shaded_line():
    """Publication-ready shaded line plot."""
    print("\n" + "=" * 70)
    print("Demo: Publication Shaded Line (Custom Scitex)")
    print("=" * 70)
    fig, ax = stx.plt.subplots(**SCITEX_STYLE)
    np.random.seed(42)
    x = np.linspace(0, 10, 50)
    y_middle = np.sin(x)
    ax.plot_shaded_line(
        x, y_middle - 0.2, y_middle, y_middle + 0.2, label="Mean \u00b1 SD", id="shaded"
    )
    ax.set_xlabel(stx.plt.ax.format_label("Time", "s"))
    ax.set_ylabel(stx.plt.ax.format_label("Signal", "a.u."))
    ax.set_title("Time Series with Uncertainty")
    ax.legend(frameon=False)
    save_path = os.path.join(OUTPUT_DIR_CUSTOM, "03_plot_shaded_line.png")
    png_path, _, _ = save_multi_format(fig, save_path, dpi=300)
    fig.close()
    print(f"- Saved: {png_path}, .pdf, .jpg")


def demo_publication_plot_violin():
    """Publication-ready violin plot using plot_violin."""
    print("\n" + "=" * 70)
    print("Demo: Publication Violin (Custom Scitex)")
    print("=" * 70)
    fig, ax = stx.plt.subplots(**SCITEX_STYLE)
    np.random.seed(42)
    data = [
        np.random.normal(0, 1, 100),
        np.random.normal(2, 1.5, 100),
        np.random.normal(5, 0.8, 100),
    ]
    ax.plot_violin(
        data,
        labels=["Group A", "Group B", "Group C"],
        colors=["steelblue", "coral", "mediumseagreen"],
        id="violin",
    )
    ax.set_xlabel(stx.plt.ax.format_label("Group", ""))
    ax.set_ylabel(stx.plt.ax.format_label("Value", "a.u."))
    ax.set_title("Distribution Comparison")
    save_path = os.path.join(OUTPUT_DIR_CUSTOM, "04_plot_violin.png")
    png_path, _, _ = save_multi_format(fig, save_path, dpi=300)
    fig.close()
    print(f"- Saved: {png_path}, .pdf, .jpg")


def demo_publication_plot_ecdf():
    """Publication-ready ECDF plot."""
    print("\n" + "=" * 70)
    print("Demo: Publication ECDF (Custom Scitex)")
    print("=" * 70)
    fig, ax = stx.plt.subplots(**SCITEX_STYLE)
    np.random.seed(42)
    data = np.random.normal(0, 1, 1000)
    ax.plot_ecdf(data, label="Distribution", id="ecdf")
    ax.set_xlabel(stx.plt.ax.format_label("Value", "a.u."))
    ax.set_ylabel(stx.plt.ax.format_label("Cumulative Probability", ""))
    ax.set_title("Empirical CDF")
    ax.legend(frameon=False)
    save_path = os.path.join(OUTPUT_DIR_CUSTOM, "05_plot_ecdf.png")
    png_path, _, _ = save_multi_format(fig, save_path, dpi=300)
    fig.close()
    print(f"- Saved: {png_path}, .pdf, .jpg")


def demo_publication_plot_box():
    """Publication-ready box plot using plot_box."""
    print("\n" + "=" * 70)
    print("Demo: Publication Box (Custom Scitex)")
    print("=" * 70)
    fig, ax = stx.plt.subplots(**SCITEX_STYLE)
    np.random.seed(42)
    data = np.random.normal(0, 1, 100)
    ax.plot_box(data, label="Data", id="box")
    ax.set_ylabel(stx.plt.ax.format_label("Value", "a.u."))
    ax.set_title("Box Plot")
    save_path = os.path.join(OUTPUT_DIR_CUSTOM, "06_plot_box.png")
    png_path, _, _ = save_multi_format(fig, save_path, dpi=300)
    fig.close()
    print(f"- Saved: {png_path}, .pdf, .jpg")


def demo_publication_plot_mean_std():
    """Publication-ready mean+/-std plot."""
    print("\n" + "=" * 70)
    print("Demo: Publication Mean\u00b1Std (Custom Scitex)")
    print("=" * 70)
    fig, ax = stx.plt.subplots(**SCITEX_STYLE)
    np.random.seed(42)
    x = np.linspace(0, 10, 20)
    y_mean = np.sin(x)
    ax.plot_mean_std(y_mean, xx=x, sd=0.2, label="Mean\u00b1SD", id="mean_std")
    ax.set_xlabel(stx.plt.ax.format_label("Time", "s"))
    ax.set_ylabel(stx.plt.ax.format_label("Signal", "a.u."))
    ax.set_title("Mean with Standard Deviation")
    ax.legend(frameon=False)
    save_path = os.path.join(OUTPUT_DIR_CUSTOM, "07_plot_mean_std.png")
    png_path, _, _ = save_multi_format(fig, save_path, dpi=300)
    fig.close()
    print(f"- Saved: {png_path}, .pdf, .jpg")


def demo_publication_plot_kde():
    """Publication-ready KDE plot."""
    print("\n" + "=" * 70)
    print("Demo: Publication KDE (Functional)")
    print("=" * 70)
    fig, ax = stx.plt.subplots(**SCITEX_STYLE)
    np.random.seed(42)
    data = np.concatenate([np.random.normal(0, 1, 500), np.random.normal(5, 1, 300)])
    ax.plot_kde(data, label="Density", id="kde")
    ax.set_xlabel(stx.plt.ax.format_label("Value", "a.u."))
    ax.set_ylabel(stx.plt.ax.format_label("Density", ""))
    ax.set_title("Kernel Density Estimate")
    ax.legend(frameon=False)
    stx.plt.ax.auto_scale_axis(ax, axis="y")
    save_path = os.path.join(OUTPUT_DIR_FUNCTIONAL, "01_plot_kde.png")
    png_path, _, _ = save_multi_format(fig, save_path, dpi=300)
    fig.close()
    print(f"- Saved: {png_path}, .pdf, .jpg")


CUSTOM_DEMOS = [
    demo_publication_plot_heatmap,
    demo_publication_plot_line,
    demo_publication_plot_shaded_line,
    demo_publication_plot_violin,
    demo_publication_plot_ecdf,
    demo_publication_plot_box,
    demo_publication_plot_mean_std,
    demo_publication_plot_kde,
]

# EOF
