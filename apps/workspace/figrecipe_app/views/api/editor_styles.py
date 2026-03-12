"""SciTeX Editor Styles - Style defaults and metadata extraction."""

import hashlib


def get_scitex_defaults():
    """Get SciTeX publication style defaults based on SCITEX_STYLE."""
    return {
        # Axes dimensions
        "axes_width_mm": 40,
        "axes_height_mm": 28,
        "axes_thickness_mm": 0.2,
        # Margins
        "margin_left_mm": 20,
        "margin_right_mm": 20,
        "margin_bottom_mm": 20,
        "margin_top_mm": 20,
        # Fonts
        "font_family": "Arial",
        "axis_font_size_pt": 7,
        "tick_font_size_pt": 7,
        "title_font_size_pt": 8,
        "legend_font_size_pt": 6,
        # Lines and ticks
        "trace_thickness_mm": 0.2,
        "tick_length_mm": 0.8,
        "tick_thickness_mm": 0.2,
        "n_ticks": 4,
        # Output
        "dpi": 300,
        "transparent": True,
        "auto_crop": False,
        # Legacy compatibility
        "fontsize": 7,
        "title_fontsize": 8,
        "axis_fontsize": 7,
        "tick_fontsize": 7,
        "linewidth": 0.57,
        "axis_width": 0.2,
        "tick_length": 0.8,
        "tick_width": 0.2,
        "tick_direction": "out",
        "hide_top_spine": True,
        "hide_right_spine": True,
        "legend_visible": True,
        "legend_frameon": False,
        "legend_loc": "best",
        "grid": False,
    }


def extract_defaults_from_metadata(metadata):
    """Extract style settings from figure metadata."""
    defaults = {}

    if "title" in metadata:
        defaults["title"] = metadata["title"]

    axes = metadata.get("axes", {})
    x_axis = axes.get("x", {})
    y_axis = axes.get("y", {})

    x_label, x_unit = x_axis.get("label", ""), x_axis.get("unit", "")
    y_label, y_unit = y_axis.get("label", ""), y_axis.get("unit", "")

    if x_label:
        defaults["xlabel"] = f"{x_label} [{x_unit}]" if x_unit else x_label
    if y_label:
        defaults["ylabel"] = f"{y_label} [{y_unit}]" if y_unit else y_label

    if "lim" in x_axis:
        defaults["xlim"] = x_axis["lim"]
    if "lim" in y_axis:
        defaults["ylim"] = y_axis["lim"]

    if "traces" in metadata:
        defaults["traces"] = metadata["traces"]

    dims = metadata.get("dimensions", {})
    if "figure_size_inch" in dims:
        defaults["fig_size"] = dims["figure_size_inch"]
    if "dpi" in dims:
        defaults["dpi"] = dims["dpi"]

    scitex_meta = metadata.get("scitex", {})
    style_mm = scitex_meta.get("style_mm", {})

    style_mappings = [
        ("axis_font_size_pt", "axis_fontsize"),
        ("tick_font_size_pt", "tick_fontsize"),
        ("title_font_size_pt", "title_fontsize"),
        ("legend_font_size_pt", "legend_fontsize"),
        ("n_ticks", "n_ticks"),
    ]
    for src, dst in style_mappings:
        if src in style_mm:
            defaults[dst] = style_mm[src]

    legend = metadata.get("legend", {})
    if "visible" in legend:
        defaults["legend_visible"] = legend["visible"]
    if "frameon" in legend:
        defaults["legend_frameon"] = legend["frameon"]

    return defaults


def compute_file_hash(path):
    """Compute SHA256 hash of file."""
    sha256 = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return f"sha256:{sha256.hexdigest()}"
