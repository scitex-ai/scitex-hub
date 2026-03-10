#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Seaborn integration demos for publication gallery."""

import os

import numpy as np
import pandas as pd
import scitex as stx
from scitex.plt.presets import SCITEX_STYLE

from ._demo_utils import OUTPUT_DIR_SEABORN, save_multi_format


def demo_publication_sns_boxplot():
    """Publication-ready seaborn boxplot."""
    print("\n" + "=" * 70)
    print("Demo: Publication Seaborn Boxplot")
    print("=" * 70)
    fig, ax = stx.plt.subplots(**SCITEX_STYLE)
    np.random.seed(42)
    df = pd.DataFrame(
        {
            "category": np.repeat(["A", "B", "C"], 50),
            "value": np.concatenate(
                [
                    np.random.normal(0, 1, 50),
                    np.random.normal(2, 1, 50),
                    np.random.normal(4, 1.5, 50),
                ]
            ),
        }
    )
    ax.sns_boxplot(x="category", y="value", data=df, id="sns_box")
    ax.set_xlabel(stx.plt.ax.format_label("Category", ""))
    ax.set_ylabel(stx.plt.ax.format_label("Value", "a.u."))
    ax.set_title("Group Distributions")
    save_path = os.path.join(OUTPUT_DIR_SEABORN, "01_sns_boxplot.png")
    png_path, _, _ = save_multi_format(fig, save_path, dpi=300)
    fig.close()
    print(f"- Saved: {png_path}, .pdf, .jpg")


def demo_publication_sns_violinplot():
    """Publication-ready seaborn violinplot."""
    print("\n" + "=" * 70)
    print("Demo: Publication Seaborn Violinplot")
    print("=" * 70)
    fig, ax = stx.plt.subplots(**SCITEX_STYLE)
    np.random.seed(42)
    df = pd.DataFrame(
        {
            "category": np.repeat(["A", "B", "C"], 50),
            "value": np.concatenate(
                [
                    np.random.normal(0, 1, 50),
                    np.random.normal(2, 1, 50),
                    np.random.normal(4, 1.5, 50),
                ]
            ),
        }
    )
    ax.sns_violinplot(x="category", y="value", data=df, id="sns_violin")
    ax.set_xlabel(stx.plt.ax.format_label("Category", ""))
    ax.set_ylabel(stx.plt.ax.format_label("Value", "a.u."))
    ax.set_title("Distribution Shapes")
    save_path = os.path.join(OUTPUT_DIR_SEABORN, "02_sns_violinplot.png")
    png_path, _, _ = save_multi_format(fig, save_path, dpi=300)
    fig.close()
    print(f"- Saved: {png_path}, .pdf, .jpg")


def demo_publication_sns_scatterplot():
    """Publication-ready seaborn scatterplot."""
    print("\n" + "=" * 70)
    print("Demo: Publication Seaborn Scatterplot")
    print("=" * 70)
    fig, ax = stx.plt.subplots(**SCITEX_STYLE)
    np.random.seed(42)
    n = 100
    df = pd.DataFrame(
        {
            "x": np.random.normal(0, 1, n),
            "y": np.random.normal(0, 1, n),
            "category": np.random.choice(["A", "B", "C"], n),
        }
    )
    df["y"] = df["x"] * 2 + df["y"]
    ax.sns_scatterplot(x="x", y="y", hue="category", data=df, id="sns_scatter")
    ax.set_xlabel(stx.plt.ax.format_label("Predictor", "a.u."))
    ax.set_ylabel(stx.plt.ax.format_label("Response", "a.u."))
    ax.set_title("Categorical Scatter")
    ax.legend(frameon=False, title="")
    save_path = os.path.join(OUTPUT_DIR_SEABORN, "03_sns_scatterplot.png")
    png_path, _, _ = save_multi_format(fig, save_path, dpi=300)
    fig.close()
    print(f"- Saved: {png_path}, .pdf, .jpg")


def demo_publication_sns_lineplot():
    """Publication-ready seaborn lineplot."""
    print("\n" + "=" * 70)
    print("Demo: Publication Seaborn Lineplot")
    print("=" * 70)
    fig, ax = stx.plt.subplots(**SCITEX_STYLE)
    np.random.seed(42)
    x = np.linspace(0, 10, 50)
    df = pd.DataFrame(
        {
            "x": np.tile(x, 3),
            "y": np.concatenate(
                [
                    np.sin(x) + np.random.normal(0, 0.1, len(x)),
                    np.cos(x) + np.random.normal(0, 0.1, len(x)),
                    -np.sin(x) + np.random.normal(0, 0.1, len(x)),
                ]
            ),
            "group": np.repeat(["A", "B", "C"], len(x)),
        }
    )
    ax.sns_lineplot(x="x", y="y", hue="group", data=df, id="sns_line")
    ax.set_xlabel(stx.plt.ax.format_label("Time", "s"))
    ax.set_ylabel(stx.plt.ax.format_label("Signal", "a.u."))
    ax.set_title("Time Series Comparison")
    ax.legend(frameon=False, title="")
    save_path = os.path.join(OUTPUT_DIR_SEABORN, "04_sns_lineplot.png")
    png_path, _, _ = save_multi_format(fig, save_path, dpi=300)
    fig.close()
    print(f"- Saved: {png_path}, .pdf, .jpg")


def demo_publication_sns_histplot():
    """Publication-ready seaborn histplot."""
    print("\n" + "=" * 70)
    print("Demo: Publication Seaborn Histplot")
    print("=" * 70)
    fig, ax = stx.plt.subplots(**SCITEX_STYLE)
    np.random.seed(42)
    df = pd.DataFrame(
        {
            "value": np.concatenate(
                [np.random.normal(0, 1, 200), np.random.normal(3, 1, 150)]
            ),
            "category": np.repeat(["A", "B"], [200, 150]),
        }
    )
    ax.sns_histplot(
        x="value", hue="category", data=df, kde=True, alpha=0.6, id="sns_hist"
    )
    ax.set_xlabel(stx.plt.ax.format_label("Value", "a.u."))
    ax.set_ylabel(stx.plt.ax.format_label("Count", ""))
    ax.set_title("Distribution with KDE")
    ax.legend(frameon=False, title="")
    save_path = os.path.join(OUTPUT_DIR_SEABORN, "05_sns_histplot.png")
    png_path, _, _ = save_multi_format(fig, save_path, dpi=300)
    fig.close()
    print(f"- Saved: {png_path}, .pdf, .jpg")


def demo_publication_sns_barplot():
    """Publication-ready seaborn barplot."""
    print("\n" + "=" * 70)
    print("Demo: Publication Seaborn Barplot")
    print("=" * 70)
    fig, ax = stx.plt.subplots(**SCITEX_STYLE)
    np.random.seed(42)
    df = pd.DataFrame(
        {
            "category": np.repeat(["A", "B", "C"], 50),
            "value": np.concatenate(
                [
                    np.random.normal(20, 5, 50),
                    np.random.normal(35, 7, 50),
                    np.random.normal(28, 6, 50),
                ]
            ),
        }
    )
    ax.sns_barplot(x="category", y="value", data=df, id="sns_bar")
    ax.set_xlabel(stx.plt.ax.format_label("Category", ""))
    ax.set_ylabel(stx.plt.ax.format_label("Value", "a.u."))
    ax.set_title("Mean Values by Category")
    save_path = os.path.join(OUTPUT_DIR_SEABORN, "06_sns_barplot.png")
    png_path, _, _ = save_multi_format(fig, save_path, dpi=300)
    fig.close()
    print(f"- Saved: {png_path}, .pdf, .jpg")


def demo_publication_sns_stripplot():
    """Publication-ready seaborn stripplot."""
    print("\n" + "=" * 70)
    print("Demo: Publication Seaborn Stripplot")
    print("=" * 70)
    fig, ax = stx.plt.subplots(**SCITEX_STYLE)
    np.random.seed(42)
    df = pd.DataFrame(
        {
            "category": np.repeat(["A", "B", "C"], 30),
            "value": np.concatenate(
                [
                    np.random.normal(0, 1, 30),
                    np.random.normal(2, 1, 30),
                    np.random.normal(4, 1.5, 30),
                ]
            ),
        }
    )
    ax.sns_stripplot(x="category", y="value", data=df, alpha=0.6, id="sns_strip")
    ax.set_xlabel(stx.plt.ax.format_label("Category", ""))
    ax.set_ylabel(stx.plt.ax.format_label("Value", "a.u."))
    ax.set_title("Strip Plot")
    save_path = os.path.join(OUTPUT_DIR_SEABORN, "07_sns_stripplot.png")
    png_path, _, _ = save_multi_format(fig, save_path, dpi=300)
    fig.close()
    print(f"- Saved: {png_path}, .pdf, .jpg")


def demo_publication_sns_kdeplot():
    """Publication-ready seaborn kdeplot."""
    print("\n" + "=" * 70)
    print("Demo: Publication Seaborn KDE Plot")
    print("=" * 70)
    fig, ax = stx.plt.subplots(**SCITEX_STYLE)
    np.random.seed(42)
    df = pd.DataFrame(
        {
            "value": np.concatenate(
                [np.random.normal(0, 1, 200), np.random.normal(3, 1, 150)]
            ),
            "category": np.repeat(["A", "B"], [200, 150]),
        }
    )
    ax.sns_kdeplot(x="value", hue="category", data=df)
    ax.set_xlabel(stx.plt.ax.format_label("Value", "a.u."))
    ax.set_ylabel(stx.plt.ax.format_label("Density", ""))
    ax.set_title("Kernel Density Estimate")
    ax.legend(frameon=False, title="")
    save_path = os.path.join(OUTPUT_DIR_SEABORN, "08_sns_kdeplot.png")
    png_path, _, _ = save_multi_format(fig, save_path, dpi=300)
    fig.close()
    print(f"- Saved: {png_path}, .pdf, .jpg")


SEABORN_DEMOS = [
    demo_publication_sns_boxplot,
    demo_publication_sns_violinplot,
    demo_publication_sns_scatterplot,
    demo_publication_sns_lineplot,
    demo_publication_sns_histplot,
    demo_publication_sns_barplot,
    demo_publication_sns_stripplot,
    demo_publication_sns_kdeplot,
]

# EOF
