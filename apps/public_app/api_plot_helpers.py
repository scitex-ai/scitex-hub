#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Plot API helpers — build figrecipe specs from query params and render figures."""

import io
import logging

import numpy as np

logger = logging.getLogger("scitex")

__all__ = ["build_spec_from_query", "build_spec_from_csv", "render_figure"]

# Plot kinds that use x/y data
XY_KINDS = {"line", "scatter", "step", "errorbar", "stem", "bar", "barh"}
# Plot kinds that use flat data arrays (data, data2, ...)
DATA_KINDS = {"hist", "box", "boxplot", "violin", "violinplot"}
# Plot kinds that use data + labels
LABEL_KINDS = {"pie"}
# Plot kinds that reshape data into a 2D matrix
MATRIX_KINDS = {"heatmap", "imshow"}


def _parse_floats(s: str) -> list:
    """Parse comma-separated string into list of floats."""
    return [float(x.strip()) for x in s.split(",") if x.strip()]


def _parse_strings(s: str) -> list:
    """Parse comma-separated string into list of strings."""
    return [x.strip() for x in s.split(",") if x.strip()]


def _try_parse_floats(s: str) -> list:
    """Try to parse as floats; fall back to strings."""
    try:
        return _parse_floats(s)
    except ValueError:
        return _parse_strings(s)


def build_spec_from_query(params: dict) -> dict:
    """Convert GET query parameters to a figrecipe spec dict.

    Parameters
    ----------
    params : dict
        Query parameter dict from request.GET.

    Returns
    -------
    dict
        Figrecipe-compatible spec.

    Raises
    ------
    ValueError
        If required parameters are missing or invalid.
    """
    kind = params.get("kind", "").lower()
    if not kind:
        raise ValueError("'kind' parameter is required")

    # Normalize aliases
    kind_map = {"box": "boxplot", "violin": "violinplot"}
    plot_kind = kind_map.get(kind, kind)

    # Figure dimensions (only override if explicitly provided; SCITEX style defaults apply)
    figure = {"style": "SCITEX"}
    if "width" in params:
        figure["width_mm"] = int(params["width"])
    if "height" in params:
        figure["height_mm"] = int(params["height"])

    spec = {
        "figure": figure,
        "plots": [],
    }

    plot_entry = {"type": plot_kind}

    # --- XY kinds ---
    if kind in XY_KINDS:
        y_str = params.get("y", "")
        if not y_str:
            raise ValueError(f"'y' parameter is required for kind={kind}")
        plot_entry["y"] = _parse_floats(y_str)

        x_str = params.get("x", "")
        if x_str:
            x_vals = _try_parse_floats(x_str)
            if isinstance(x_vals[0], str):
                # Categorical x-axis (bar chart with labels)
                spec["xticks"] = {
                    "positions": list(range(len(x_vals))),
                    "labels": x_vals,
                }
                plot_entry["x"] = list(range(len(x_vals)))
            else:
                plot_entry["x"] = x_vals

        # Error bars
        yerr_str = params.get("yerr", "")
        if yerr_str:
            plot_entry["yerr"] = _parse_floats(yerr_str)
            if kind != "errorbar":
                plot_entry["type"] = "errorbar"

    # --- Distribution kinds (data, data2, ...) ---
    elif kind in DATA_KINDS or plot_kind in DATA_KINDS:
        groups = []
        group_labels = []

        data_str = params.get("data", "")
        if not data_str:
            raise ValueError(f"'data' parameter is required for kind={kind}")
        groups.append(_parse_floats(data_str))
        group_labels.append("Group 1")

        for i in range(2, 7):
            extra = params.get(f"data{i}", "")
            if extra:
                groups.append(_parse_floats(extra))
                group_labels.append(f"Group {i}")

        labels_str = params.get("labels", "")
        if labels_str:
            group_labels = _parse_strings(labels_str)

        if plot_kind in ("boxplot", "violinplot"):
            plot_entry["data"] = groups
            plot_entry["positions"] = list(range(len(groups)))
            spec["xticks"] = {
                "positions": list(range(len(groups))),
                "labels": group_labels[: len(groups)],
            }
        else:
            # Histogram: single or multiple datasets
            if len(groups) == 1:
                plot_entry["x"] = groups[0]
            else:
                plot_entry["x"] = groups

    # --- Pie ---
    elif kind in LABEL_KINDS:
        data_str = params.get("data", "")
        if not data_str:
            raise ValueError("'data' parameter is required for kind=pie")
        plot_entry["x"] = _parse_floats(data_str)

        labels_str = params.get("labels", "")
        if labels_str:
            plot_entry["labels"] = _parse_strings(labels_str)

    # --- Heatmap / imshow ---
    elif kind in MATRIX_KINDS:
        data_str = params.get("data", "")
        if not data_str:
            raise ValueError(f"'data' parameter is required for kind={kind}")
        flat = _parse_floats(data_str)
        nrows = int(params.get("nrows", 0))
        ncols = int(params.get("ncols", 0))

        if nrows and ncols:
            if len(flat) != nrows * ncols:
                raise ValueError(
                    f"data length {len(flat)} != nrows*ncols ({nrows}*{ncols})"
                )
            matrix = np.array(flat).reshape(nrows, ncols).tolist()
        else:
            # Auto square
            n = len(flat)
            side = int(np.ceil(np.sqrt(n)))
            padded = flat + [0] * (side * side - n)
            matrix = np.array(padded).reshape(side, side).tolist()

        plot_entry["data"] = matrix
        plot_entry["type"] = "imshow"

    else:
        raise ValueError(
            f"Unsupported kind: '{kind}'. "
            "Use: line, scatter, bar, barh, hist, box, violin, pie, "
            "heatmap, step, errorbar, stem"
        )

    # Optional styling
    color = params.get("color", "")
    if color:
        plot_entry["color"] = color

    spec["plots"].append(plot_entry)

    # Axes decorations
    for key in ("title", "xlabel", "ylabel"):
        val = params.get(key, "")
        if val:
            spec[key] = val

    return spec


def build_spec_from_csv(csv_path, params: dict) -> dict:
    """Build figrecipe spec from uploaded CSV + form parameters.

    Leverages figrecipe's native data_file + column name resolution.

    Parameters
    ----------
    csv_path : Path
        Path to the uploaded CSV temp file.
    params : dict
        Form fields: kind, x_col, y_col, data_col, color, title, etc.

    Returns
    -------
    dict
        Figrecipe-compatible spec.
    """
    kind = params.get("kind", "").lower()
    if not kind:
        raise ValueError("'kind' parameter is required")

    kind_map = {"box": "boxplot", "violin": "violinplot"}
    plot_kind = kind_map.get(kind, kind)

    # Figure dimensions (only override if explicitly provided; SCITEX style defaults apply)
    figure = {"style": "SCITEX"}
    if "width" in params:
        figure["width_mm"] = int(params["width"])
    if "height" in params:
        figure["height_mm"] = int(params["height"])

    spec = {
        "figure": figure,
        "plots": [],
    }

    plot_entry = {"type": plot_kind, "data_file": str(csv_path)}

    if kind in XY_KINDS:
        # x_col and y_col become column name strings for figrecipe
        y_col = params.get("y_col", "")
        if not y_col:
            raise ValueError("'y_col' is required for XY plot kinds")
        plot_entry["y"] = y_col

        x_col = params.get("x_col", "")
        if x_col:
            plot_entry["x"] = x_col

    elif kind in DATA_KINDS or plot_kind in DATA_KINDS:
        data_col = params.get("data_col", "")
        if not data_col:
            raise ValueError("'data_col' is required for distribution plots")
        plot_entry["x"] = data_col

    elif kind in LABEL_KINDS:
        data_col = params.get("data_col", "")
        if not data_col:
            raise ValueError("'data_col' is required for pie charts")
        plot_entry["x"] = data_col

        labels_col = params.get("labels_col", "")
        if labels_col:
            plot_entry["labels"] = labels_col

    elif kind in MATRIX_KINDS:
        data_col = params.get("data_col", "")
        if not data_col:
            raise ValueError("'data_col' is required for heatmaps")
        plot_entry["data"] = data_col
        plot_entry["type"] = "imshow"

    else:
        raise ValueError(
            f"Unsupported kind: '{kind}'. "
            "Use: line, scatter, bar, barh, hist, box, violin, pie, "
            "heatmap, step, errorbar, stem"
        )

    color = params.get("color", "")
    if color:
        plot_entry["color"] = color

    spec["plots"].append(plot_entry)

    for key in ("title", "xlabel", "ylabel"):
        val = params.get(key, "")
        if val:
            spec[key] = val

    return spec


def render_figure(spec: dict) -> bytes:
    """Render a figrecipe spec to PNG bytes.

    Parameters
    ----------
    spec : dict
        Figrecipe-compatible spec dict.

    Returns
    -------
    bytes
        PNG image bytes.
    """
    import scitex as stx

    stx.plt.load_style()

    from figrecipe._api._plot import create_figure_from_spec

    result = create_figure_from_spec(spec)
    fig = result["figure"]

    # Apply deferred SCITEX tick limits (MaxNLocator) — not called by
    # create_figure_from_spec, only by figrecipe's own save pipeline.
    from figrecipe.styles._finalize import finalize_ticks

    for ax in fig.get_axes():
        finalize_ticks(ax)

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=300, facecolor="white", bbox_inches="tight")
    buf.seek(0)
    png_bytes = buf.read()

    stx.plt.close("all")

    return png_bytes


# EOF
