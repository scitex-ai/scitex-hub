#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Plot API helpers — build figrecipe specs from query params and render figures."""

import io
import logging

import numpy as np

logger = logging.getLogger("scitex")

__all__ = ["build_spec_from_query", "render_figure"]

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

    # Figure dimensions
    width = int(params.get("width", 80))
    height = int(params.get("height", 60))

    spec = {
        "figure": {"width_mm": width, "height_mm": height, "style": "SCITEX"},
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
