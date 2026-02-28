#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Matplotlib basic plot demos for publication gallery."""

import os

import numpy as np
import scitex as stx
from scitex.plt.presets import SCITEX_STYLE

from ._demo_utils import OUTPUT_DIR_BASIC, save_multi_format


def demo_publication_plot():
    """Publication-ready line plot using SCITEX_STYLE."""
    print("\n" + "=" * 70)
    print("Demo: Publication Line Plot (SciTeX Style)")
    print("=" * 70)
    fig, ax = stx.plt.subplots(**SCITEX_STYLE)
    x = np.linspace(0, 2 * np.pi, 100)
    ax.plot(x, np.sin(x), "b-", label="sin(x)", id="sine")
    ax.plot(x, np.cos(x), "r-", label="cos(x)", id="cosine")
    ax.set_xlabel(stx.plt.ax.format_label("Time", "s"))
    ax.set_ylabel(stx.plt.ax.format_label("Amplitude", "a.u."))
    ax.set_title("Oscillatory Response")
    ax.legend(frameon=False)
    save_path = os.path.join(OUTPUT_DIR_BASIC, "01_plot.png")
    png_path, _, _ = save_multi_format(
        fig, save_path, dpi=300, plot_type="line", style_name="SCITEX_STYLE"
    )
    fig.close()
    print(f"- Saved: {png_path}, .pdf, .jpg")


def demo_publication_scatter():
    """Publication-ready scatter plot using SCITEX_STYLE."""
    print("\n" + "=" * 70)
    print("Demo: Publication Scatter Plot (SciTeX Style)")
    print("=" * 70)
    fig, ax = stx.plt.subplots(**SCITEX_STYLE)
    np.random.seed(42)
    n = 100
    x = np.random.normal(0, 1, n)
    y = 2 * x + np.random.normal(0, 0.5, n)
    scatter = ax.scatter(
        x, y, alpha=0.6, c="steelblue", id="scatter_data", label="Data"
    )
    stx.plt.ax.style_scatter(scatter, size_mm=0.8)
    z = np.polyfit(x, y, 1)
    x_line = np.linspace(x.min(), x.max(), 100)
    ax.plot(x_line, np.poly1d(z)(x_line), "r-", alpha=0.8, label="Fit", id="regression")
    ax.set_xlabel(stx.plt.ax.format_label("Predictor", "a.u."))
    ax.set_ylabel(stx.plt.ax.format_label("Response", "a.u."))
    ax.set_title("Correlation Analysis")
    ax.legend(frameon=False)
    save_path = os.path.join(OUTPUT_DIR_BASIC, "02_scatter.png")
    png_path, _, _ = save_multi_format(
        fig, save_path, dpi=300, plot_type="scatter", style_name="SCITEX_STYLE"
    )
    fig.close()
    print(f"- Saved: {png_path}, .pdf, .jpg")


def demo_publication_bar():
    """Publication-ready bar plot using SCITEX_STYLE."""
    print("\n" + "=" * 70)
    print("Demo: Publication Bar Plot (SciTeX Style)")
    print("=" * 70)
    fig, ax = stx.plt.subplots(**SCITEX_STYLE)
    categories = ["Control", "Treatment A", "Treatment B", "Treatment C"]
    values = [45, 67, 52, 71]
    errors = [5, 7, 6, 8]
    x_pos = np.arange(len(categories))
    bars = ax.bar(
        x_pos, values, alpha=0.7, color="steelblue", id="bar_data", label="Response"
    )
    stx.plt.ax.style_barplot(bars, edge_thickness_mm=0.2, edgecolor="black")
    eb = ax.errorbar(x_pos, values, yerr=errors, fmt="none", capsize=3, id="error_bars")
    stx.plt.ax.style_errorbar(eb, thickness_mm=0.2, cap_width_mm=0.8)
    ax.set_xticks(x_pos)
    ax.set_xticklabels(categories, rotation=15, ha="right")
    ax.set_xlabel(stx.plt.ax.format_label("Treatment", ""))
    ax.set_ylabel(stx.plt.ax.format_label("Response", "%"))
    ax.set_title("Treatment Effect Comparison")
    ax.legend(frameon=False)
    save_path = os.path.join(OUTPUT_DIR_BASIC, "03_bar.png")
    png_path, _, _ = save_multi_format(fig, save_path, dpi=300)
    fig.close()
    print(f"- Saved: {png_path}, .pdf, .jpg")


def demo_publication_hist():
    """Publication-ready histogram with KDE overlay."""
    print("\n" + "=" * 70)
    print("Demo: Publication Histogram (SciTeX Style)")
    print("=" * 70)
    from scipy import stats

    fig, ax = stx.plt.subplots(**SCITEX_STYLE)
    np.random.seed(42)
    data = np.concatenate([np.random.normal(0, 1, 500), np.random.normal(4, 1, 300)])
    ax.hist(
        data,
        bins=40,
        alpha=0.7,
        density=True,
        color="steelblue",
        label="Data",
        id="histogram",
    )
    kde = stats.gaussian_kde(data)
    x_range = np.linspace(data.min(), data.max(), 200)
    ax.plot(x_range, kde(x_range), color="steelblue", label="KDE", id="kde")
    ax.set_xlabel(stx.plt.ax.format_label("Value", "a.u."))
    ax.set_ylabel(stx.plt.ax.format_label("Probability Density", ""))
    ax.set_title("Distribution Analysis")
    ax.legend(frameon=False)
    save_path = os.path.join(OUTPUT_DIR_BASIC, "04_hist.png")
    png_path, _, _ = save_multi_format(fig, save_path, dpi=300)
    fig.close()
    print(f"- Saved: {png_path}, .pdf, .jpg")


def demo_publication_boxplot():
    """Publication-ready boxplot using SCITEX_STYLE."""
    print("\n" + "=" * 70)
    print("Demo: Publication Boxplot (SciTeX Style)")
    print("=" * 70)
    fig, ax = stx.plt.subplots(**SCITEX_STYLE)
    np.random.seed(42)
    data = [
        np.random.normal(0, 1, 100),
        np.random.normal(2, 1, 100),
        np.random.normal(4, 1.5, 100),
    ]
    bp = ax.boxplot(data, labels=["Group A", "Group B", "Group C"], id="boxplot")
    stx.plt.ax.style_boxplot(bp, linewidth_mm=0.2)
    ax.set_xlabel(stx.plt.ax.format_label("Group", ""))
    ax.set_ylabel(stx.plt.ax.format_label("Value", "a.u."))
    ax.set_title("Group Comparison")
    save_path = os.path.join(OUTPUT_DIR_BASIC, "05_boxplot.png")
    png_path, _, _ = save_multi_format(fig, save_path, dpi=300)
    fig.close()
    print(f"- Saved: {png_path}, .pdf, .jpg")


def demo_publication_errorbar():
    """Publication-ready error bar plot."""
    print("\n" + "=" * 70)
    print("Demo: Publication Error Bar Plot (SciTeX Style)")
    print("=" * 70)
    fig, ax = stx.plt.subplots(**SCITEX_STYLE)
    np.random.seed(42)
    time = np.arange(0, 10, 0.5)
    mean_values = 10 * np.exp(-time / 5)
    errors = 0.1 * mean_values + np.random.uniform(0, 0.5, len(time))
    eb = ax.errorbar(
        time,
        mean_values,
        yerr=errors,
        fmt="o-",
        capsize=3,
        alpha=0.8,
        color="steelblue",
        label="Measured",
        id="errorbar_data",
    )
    stx.plt.ax.style_errorbar(eb, thickness_mm=0.2, cap_width_mm=0.8)
    ax.set_xlabel(stx.plt.ax.format_label("Time", "min"))
    ax.set_ylabel(stx.plt.ax.format_label("Concentration", "\u00b5M"))
    ax.set_title("Decay Kinetics")
    ax.legend(frameon=False)
    save_path = os.path.join(OUTPUT_DIR_BASIC, "06_errorbar.png")
    png_path, _, _ = save_multi_format(fig, save_path, dpi=300)
    fig.close()
    print(f"- Saved: {png_path}, .pdf, .jpg")


def demo_publication_barh():
    """Publication-ready horizontal bar plot."""
    print("\n" + "=" * 70)
    print("Demo: Publication Horizontal Bar Plot (SciTeX Style)")
    print("=" * 70)
    fig, ax = stx.plt.subplots(**SCITEX_STYLE)
    categories = ["Method A", "Method B", "Method C", "Method D"]
    values = [45, 67, 52, 71]
    bars = ax.barh(categories, values, alpha=0.7, color="steelblue", id="barh_data")
    stx.plt.ax.style_barplot(bars, edge_thickness_mm=0.2, edgecolor="black")
    ax.set_xlabel(stx.plt.ax.format_label("Score", ""))
    ax.set_ylabel(stx.plt.ax.format_label("Method", ""))
    ax.set_title("Performance Comparison")
    save_path = os.path.join(OUTPUT_DIR_BASIC, "07_barh.png")
    png_path, _, _ = save_multi_format(fig, save_path, dpi=300)
    fig.close()
    print(f"- Saved: {png_path}, .pdf, .jpg")


def demo_publication_fill_between():
    """Publication-ready fill_between plot."""
    print("\n" + "=" * 70)
    print("Demo: Publication Fill Between (SciTeX Style)")
    print("=" * 70)
    fig, ax = stx.plt.subplots(**SCITEX_STYLE)
    x = np.linspace(0, 2 * np.pi, 100)
    y1 = np.sin(x)
    y2 = np.sin(x) + 0.5
    ax.fill_between(
        x, y1, y2, alpha=0.3, color="steelblue", label="Confidence", id="fill"
    )
    ax.plot(x, (y1 + y2) / 2, "b-", label="Mean", id="mean_line")
    ax.set_xlabel(stx.plt.ax.format_label("Time", "s"))
    ax.set_ylabel(stx.plt.ax.format_label("Signal", "a.u."))
    ax.set_title("Signal with Confidence")
    ax.legend(frameon=False)
    save_path = os.path.join(OUTPUT_DIR_BASIC, "08_fill_between.png")
    png_path, _, _ = save_multi_format(fig, save_path, dpi=300)
    fig.close()
    print(f"- Saved: {png_path}, .pdf, .jpg")


def demo_publication_imshow():
    """Publication-ready imshow plot."""
    print("\n" + "=" * 70)
    print("Demo: Publication Imshow (SciTeX Style)")
    print("=" * 70)
    style = SCITEX_STYLE.copy()
    style["ax_width_mm"] = 40
    style["ax_height_mm"] = 30
    fig, ax = stx.plt.subplots(**style)
    np.random.seed(42)
    data = np.random.rand(20, 30)
    im = ax.imshow(data, cmap="viridis", aspect="auto", id="imshow")
    ax.spines[:].set_visible(True)
    cbar = fig.colorbar(im, ax=ax)
    cbar.set_label(stx.plt.ax.format_label("Intensity", ""))
    ax.set_xlabel(stx.plt.ax.format_label("X", ""))
    ax.set_ylabel(stx.plt.ax.format_label("Y", ""))
    ax.set_title("Image Data")
    save_path = os.path.join(OUTPUT_DIR_BASIC, "09_imshow.png")
    png_path, _, _ = save_multi_format(fig, save_path, dpi=300)
    fig.close()
    print(f"- Saved: {png_path}, .pdf, .jpg")


def demo_publication_contour():
    """Publication-ready contour plot."""
    print("\n" + "=" * 70)
    print("Demo: Publication Contour (SciTeX Style)")
    print("=" * 70)
    fig, ax = stx.plt.subplots(**SCITEX_STYLE)
    delta = 0.5
    x = np.arange(-3.0, 3.0, delta)
    y = np.arange(-2.0, 2.0, delta)
    X, Y = np.meshgrid(x, y)
    Z = np.sin(X) * np.cos(Y)
    contour = ax.contour(X, Y, Z, levels=8, id="contour")
    ax.clabel(contour, inline=True, fontsize=6)
    ax.set_xlabel(stx.plt.ax.format_label("X", ""))
    ax.set_ylabel(stx.plt.ax.format_label("Y", ""))
    ax.set_title("Contour Map")
    save_path = os.path.join(OUTPUT_DIR_BASIC, "10_contour.png")
    png_path, _, _ = save_multi_format(fig, save_path, dpi=300)
    fig.close()
    print(f"- Saved: {png_path}, .pdf, .jpg")


def demo_publication_violinplot():
    """Publication-ready violinplot using matplotlib."""
    print("\n" + "=" * 70)
    print("Demo: Publication Violinplot (SciTeX Style)")
    print("=" * 70)
    fig, ax = stx.plt.subplots(**SCITEX_STYLE)
    np.random.seed(42)
    data = [np.random.normal(i, 1, 100) for i in range(4)]
    ax.violinplot(data, positions=[1, 2, 3, 4], id="violinplot")
    ax.set_xlabel(stx.plt.ax.format_label("Group", ""))
    ax.set_ylabel(stx.plt.ax.format_label("Value", "a.u."))
    ax.set_title("Violin Plot")
    ax.set_xticks([1, 2, 3, 4])
    ax.set_xticklabels(["A", "B", "C", "D"])
    save_path = os.path.join(OUTPUT_DIR_BASIC, "11_violinplot.png")
    png_path, _, _ = save_multi_format(fig, save_path, dpi=300)
    fig.close()
    print(f"- Saved: {png_path}, .pdf, .jpg")


BASIC_DEMOS = [
    demo_publication_plot,
    demo_publication_scatter,
    demo_publication_bar,
    demo_publication_hist,
    demo_publication_boxplot,
    demo_publication_errorbar,
    demo_publication_barh,
    demo_publication_fill_between,
    demo_publication_imshow,
    demo_publication_contour,
    demo_publication_violinplot,
]

# EOF
