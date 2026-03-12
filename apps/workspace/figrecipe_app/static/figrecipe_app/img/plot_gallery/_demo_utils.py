#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Shared utilities for publication demo plots."""

import scitex as stx

OUTPUT_DIR = "publication"
OUTPUT_DIR_BASIC = "publication/01_matplotlib_basic"
OUTPUT_DIR_CUSTOM = "publication/02_custom_scitex"
OUTPUT_DIR_FUNCTIONAL = "publication/03_functional"
OUTPUT_DIR_SEABORN = "publication/04_seaborn"
OUTPUT_DIR_MULTI = "publication/05_multi_panel"


def get_linewidth_from_style(style_dict):
    """Get proper linewidth in points from mm-based style dict."""
    from scitex.plt.utils import mm_to_pt

    trace_mm = style_dict.get("trace_thickness_mm", 0.12)
    return mm_to_pt(trace_mm)


def set_ticks(ax, n=4):
    """Set number of ticks on both axes."""
    from matplotlib.ticker import MaxNLocator

    ax.xaxis.set_major_locator(MaxNLocator(n))
    ax.yaxis.set_major_locator(MaxNLocator(n))


def save_multi_format(
    fig, base_path, dpi=300, *, plot_type=None, style_name=None, style_overrides=None
):
    """Save figure in PNG, PDF, and JPEG formats with metadata.

    Parameters
    ----------
    fig : matplotlib.figure.Figure or scitex wrapper
    base_path : str
        Base path ending with .png
    dpi : int
        DPI for raster formats. Default 300.
    plot_type : str, optional
    style_name : str, optional
    style_overrides : dict, optional

    Returns
    -------
    tuple : (png_path, pdf_path, jpg_path)
    """
    metadata_extra = {}
    if plot_type is not None:
        metadata_extra["plot_type"] = plot_type
    if style_name is not None or style_overrides is not None:
        metadata_extra["style"] = {
            "name": style_name,
            "overrides": style_overrides or {},
        }

    png_path = base_path if base_path.endswith(".png") else base_path
    stx.io.save(
        fig,
        png_path,
        dpi=dpi,
        auto_crop=True,
        crop_margin_mm=1.0,
        metadata_extra=metadata_extra,
    )

    pdf_path = png_path.replace(".png", ".pdf")
    stx.io.save(fig, pdf_path, metadata_extra=metadata_extra)

    jpg_path = png_path.replace(".png", ".jpg")
    stx.io.save(
        fig,
        jpg_path,
        dpi=600,
        auto_crop=True,
        crop_margin_mm=1.0,
        metadata_extra=metadata_extra,
    )

    return png_path, pdf_path, jpg_path


# EOF
