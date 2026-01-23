"""
SciTeX Visual Editor API - Real-time figure editing endpoints.

Integrates scitex.vis functionality into the Django /vis/ page:
- Load figure from JSON/CSV files
- Render preview with overrides
- Save manual edits to .manual.json

Note: Uses SCITEX_STYLE-compatible defaults (defined locally to avoid import issues)
"""

import json
import base64
import io
import hashlib
from pathlib import Path

from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings


def _get_scitex_defaults():
    """
    Get SciTeX publication style defaults.
    Based on SCITEX_STYLE from scitex.plt.styles.SCITEX_STYLE.yaml
    """
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


def _extract_defaults_from_metadata(metadata):
    """Extract style settings from figure metadata."""
    defaults = {}

    # Labels
    if "title" in metadata:
        defaults["title"] = metadata["title"]

    axes = metadata.get("axes", {})
    x_axis = axes.get("x", {})
    y_axis = axes.get("y", {})

    x_label = x_axis.get("label", "")
    x_unit = x_axis.get("unit", "")
    y_label = y_axis.get("label", "")
    y_unit = y_axis.get("unit", "")

    if x_label:
        defaults["xlabel"] = f"{x_label} [{x_unit}]" if x_unit else x_label
    if y_label:
        defaults["ylabel"] = f"{y_label} [{y_unit}]" if y_unit else y_label

    # Axis limits
    if "lim" in x_axis:
        defaults["xlim"] = x_axis["lim"]
    if "lim" in y_axis:
        defaults["ylim"] = y_axis["lim"]

    # Traces
    if "traces" in metadata:
        defaults["traces"] = metadata["traces"]

    # Dimensions
    dims = metadata.get("dimensions", {})
    if "figure_size_inch" in dims:
        defaults["fig_size"] = dims["figure_size_inch"]
    if "dpi" in dims:
        defaults["dpi"] = dims["dpi"]

    # Style from scitex metadata
    scitex_meta = metadata.get("scitex", {})
    style_mm = scitex_meta.get("style_mm", {})

    if "axis_font_size_pt" in style_mm:
        defaults["axis_fontsize"] = style_mm["axis_font_size_pt"]
    if "tick_font_size_pt" in style_mm:
        defaults["tick_fontsize"] = style_mm["tick_font_size_pt"]
    if "title_font_size_pt" in style_mm:
        defaults["title_fontsize"] = style_mm["title_font_size_pt"]
    if "legend_font_size_pt" in style_mm:
        defaults["legend_fontsize"] = style_mm["legend_font_size_pt"]
    if "n_ticks" in style_mm:
        defaults["n_ticks"] = style_mm["n_ticks"]

    # Legend
    legend = metadata.get("legend", {})
    if "visible" in legend:
        defaults["legend_visible"] = legend["visible"]
    if "frameon" in legend:
        defaults["legend_frameon"] = legend["frameon"]

    return defaults


def _compute_file_hash(path):
    """Compute SHA256 hash of file."""
    sha256 = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return f"sha256:{sha256.hexdigest()}"


def _render_figure_preview(metadata, csv_data, overrides):
    """Render figure as base64 PNG with applied overrides."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.ticker import MaxNLocator
    import pandas as pd

    # mm to pt conversion
    mm_to_pt = 2.83465

    # Get values from overrides
    o = overrides

    # Dimensions
    dpi = o.get("dpi", 300)
    fig_size = o.get("fig_size", [3.15, 2.68])

    # Font sizes
    axis_fontsize = o.get("axis_fontsize", 7)
    tick_fontsize = o.get("tick_fontsize", 7)
    title_fontsize = o.get("title_fontsize", 8)
    legend_fontsize = o.get("legend_fontsize", 6)

    # Line/axis thickness
    linewidth_pt = o.get("linewidth", 0.57)
    axis_width_pt = o.get("axis_width", 0.2) * mm_to_pt
    tick_length_pt = o.get("tick_length", 0.8) * mm_to_pt
    tick_width_pt = o.get("tick_width", 0.2) * mm_to_pt
    tick_direction = o.get("tick_direction", "out")
    n_ticks = o.get("n_ticks", 4)

    # Transparent background
    transparent = o.get("transparent", True)

    # Create figure
    fig, ax = plt.subplots(figsize=fig_size, dpi=dpi)
    if transparent:
        fig.patch.set_facecolor("none")
        ax.patch.set_facecolor("none")
    elif o.get("facecolor"):
        fig.patch.set_facecolor(o["facecolor"])
        ax.patch.set_facecolor(o["facecolor"])

    # Plot from CSV data
    if csv_data is not None and not csv_data.empty:
        _plot_from_csv(ax, csv_data, o, linewidth_pt, legend_fontsize)
    else:
        ax.text(
            0.5,
            0.5,
            "No plot data available",
            ha="center",
            va="center",
            transform=ax.transAxes,
            fontsize=axis_fontsize,
        )

    # Apply labels
    if o.get("title"):
        ax.set_title(o["title"], fontsize=title_fontsize)
    if o.get("xlabel"):
        ax.set_xlabel(o["xlabel"], fontsize=axis_fontsize)
    if o.get("ylabel"):
        ax.set_ylabel(o["ylabel"], fontsize=axis_fontsize)

    # Tick styling
    ax.tick_params(
        axis="both",
        labelsize=tick_fontsize,
        length=tick_length_pt,
        width=tick_width_pt,
        direction=tick_direction,
    )

    # Number of ticks
    ax.xaxis.set_major_locator(MaxNLocator(nbins=n_ticks))
    ax.yaxis.set_major_locator(MaxNLocator(nbins=n_ticks))

    # Grid
    if o.get("grid"):
        ax.grid(True, linewidth=axis_width_pt, alpha=0.3)

    # Axis limits
    if o.get("xlim"):
        ax.set_xlim(o["xlim"])
    if o.get("ylim"):
        ax.set_ylim(o["ylim"])

    # Spines visibility
    if o.get("hide_top_spine", True):
        ax.spines["top"].set_visible(False)
    if o.get("hide_right_spine", True):
        ax.spines["right"].set_visible(False)

    # Spine line width
    for spine in ax.spines.values():
        spine.set_linewidth(axis_width_pt)

    # Annotations
    for annot in o.get("annotations", []):
        if annot.get("type") == "text":
            ax.text(
                annot.get("x", 0.5),
                annot.get("y", 0.5),
                annot.get("text", ""),
                transform=ax.transAxes,
                fontsize=annot.get("fontsize", axis_fontsize),
            )

    fig.tight_layout()

    # Convert to base64
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=dpi, bbox_inches="tight", transparent=transparent)
    buf.seek(0)
    img_data = base64.b64encode(buf.read()).decode("utf-8")
    plt.close(fig)

    return img_data


def _plot_from_csv(ax, df, overrides, linewidth, legend_fontsize):
    """Reconstruct plot from CSV data using trace info."""
    import pandas as pd

    o = overrides
    legend_visible = o.get("legend_visible", True)
    legend_frameon = o.get("legend_frameon", False)
    legend_loc = o.get("legend_loc", "best")

    traces = o.get("traces", [])

    if traces:
        for trace in traces:
            csv_cols = trace.get("csv_columns", {})
            x_col = csv_cols.get("x")
            y_col = csv_cols.get("y")

            if x_col in df.columns and y_col in df.columns:
                ax.plot(
                    df[x_col],
                    df[y_col],
                    label=trace.get("label", trace.get("id", "")),
                    color=trace.get("color"),
                    linestyle=trace.get("linestyle", "-"),
                    linewidth=trace.get("linewidth", linewidth),
                    marker=trace.get("marker", None),
                    markersize=trace.get("markersize", 6),
                )

        if legend_visible and any(t.get("label") for t in traces):
            ax.legend(fontsize=legend_fontsize, frameon=legend_frameon, loc=legend_loc)
    else:
        # Fallback: parse CSV column names
        cols = df.columns.tolist()
        trace_groups = {}

        for col in cols:
            if col.endswith("_x"):
                trace_id = col[:-2]
                y_col = trace_id + "_y"
                if y_col in cols:
                    parts = trace_id.split("_")
                    label = parts[2] if len(parts) > 2 else trace_id
                    trace_groups[trace_id] = {
                        "x_col": col,
                        "y_col": y_col,
                        "label": label,
                    }

        if trace_groups:
            for trace_id, info in trace_groups.items():
                ax.plot(
                    df[info["x_col"]],
                    df[info["y_col"]],
                    label=info["label"],
                    linewidth=linewidth,
                )
            if legend_visible:
                ax.legend(fontsize=legend_fontsize, frameon=legend_frameon, loc=legend_loc)
        elif len(cols) >= 2:
            x_col = cols[0]
            for y_col in cols[1:]:
                try:
                    ax.plot(df[x_col], df[y_col], label=str(y_col), linewidth=linewidth)
                except Exception:
                    pass
            if len(cols) > 2 and legend_visible:
                ax.legend(fontsize=legend_fontsize, frameon=legend_frameon, loc=legend_loc)


@require_http_methods(["POST"])
@csrf_exempt
def load_figure_json(request):
    """
    Load a figure from JSON file and return metadata + defaults.

    POST /vis/api/editor/load/

    Request body (JSON):
    {
        "json_path": "/path/to/figure.json",
        "csv_path": "/path/to/figure.csv"  // optional
    }

    Response:
    {
        "metadata": {...},
        "overrides": {...},  // merged defaults + metadata values
        "csv_columns": [...],
        "preview": "base64..."
    }
    """
    try:
        data = json.loads(request.body)
        json_path = Path(data.get("json_path", ""))

        if not json_path.exists():
            return JsonResponse({"error": f"JSON file not found: {json_path}"}, status=404)

        # Load JSON metadata
        with open(json_path, "r") as f:
            metadata = json.load(f)

        # Try to find CSV file
        csv_path = data.get("csv_path")
        csv_data = None
        csv_columns = []

        if csv_path:
            csv_path = Path(csv_path)
        else:
            # Auto-detect CSV path
            csv_sibling = json_path.with_suffix(".csv")
            if csv_sibling.exists():
                csv_path = csv_sibling
            elif json_path.parent.name == "json":
                csv_organized = json_path.parent.parent / "csv" / f"{json_path.stem}.csv"
                if csv_organized.exists():
                    csv_path = csv_organized

        if csv_path and csv_path.exists():
            import pandas as pd

            csv_data = pd.read_csv(csv_path)
            csv_columns = csv_data.columns.tolist()

        # Build overrides from defaults + metadata
        overrides = _get_scitex_defaults()
        overrides.update(_extract_defaults_from_metadata(metadata))

        # Check for manual overrides file
        manual_path = json_path.with_suffix(".manual.json")
        if manual_path.exists():
            with open(manual_path, "r") as f:
                manual_data = json.load(f)
            manual_overrides = manual_data.get("overrides", {})
            overrides.update(manual_overrides)

        # Generate preview
        preview = _render_figure_preview(metadata, csv_data, overrides)

        return JsonResponse(
            {
                "success": True,
                "metadata": metadata,
                "overrides": overrides,
                "csv_columns": csv_columns,
                "csv_path": str(csv_path) if csv_path else None,
                "json_path": str(json_path),
                "preview": preview,
            }
        )

    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON data"}, status=400)
    except Exception as e:
        return JsonResponse({"error": f"Failed to load figure: {str(e)}"}, status=500)


@require_http_methods(["POST"])
@csrf_exempt
def update_preview(request):
    """
    Update figure preview with new overrides.

    POST /vis/api/editor/preview/

    Request body (JSON):
    {
        "json_path": "/path/to/figure.json",
        "csv_path": "/path/to/figure.csv",
        "overrides": {...},
        "sample_data": "x,y\n0,1\n1,2\n..."  // Optional CSV string
    }

    Response:
    {
        "preview": "base64...",
        "status": "updated"
    }
    """
    try:
        data = json.loads(request.body)
        json_path_str = data.get("json_path", "")
        json_path = Path(json_path_str) if json_path_str else None
        csv_path = data.get("csv_path")
        overrides = data.get("overrides", {})
        sample_data_str = data.get("sample_data")

        # Load metadata
        metadata = {}
        if json_path and json_path.exists():
            with open(json_path, "r") as f:
                metadata = json.load(f)

        # Load CSV data
        csv_data = None
        if sample_data_str:
            # Use sample data from request
            import pandas as pd
            from io import StringIO

            csv_data = pd.read_csv(StringIO(sample_data_str))
        elif csv_path:
            # Load from file
            import pandas as pd

            csv_path = Path(csv_path)
            if csv_path.exists():
                csv_data = pd.read_csv(csv_path)

        # Merge defaults with provided overrides
        full_overrides = _get_scitex_defaults()
        full_overrides.update(_extract_defaults_from_metadata(metadata))
        full_overrides.update(overrides)

        # Generate preview
        preview = _render_figure_preview(metadata, csv_data, full_overrides)

        return JsonResponse({"preview": preview, "status": "updated"})

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@require_http_methods(["POST"])
@csrf_exempt
def save_manual_overrides(request):
    """
    Save manual overrides to .manual.json file.

    POST /vis/api/editor/save/

    Request body (JSON):
    {
        "json_path": "/path/to/figure.json",
        "overrides": {...}
    }

    Response:
    {
        "status": "saved",
        "path": "/path/to/figure.manual.json"
    }
    """
    try:
        data = json.loads(request.body)
        json_path = Path(data.get("json_path", ""))
        overrides = data.get("overrides", {})

        if not json_path.exists():
            return JsonResponse({"error": f"JSON file not found: {json_path}"}, status=404)

        # Compute hash of base file
        base_hash = _compute_file_hash(json_path)

        # Prepare manual.json content
        manual_data = {
            "base_file": json_path.name,
            "base_hash": base_hash,
            "overrides": overrides,
        }

        # Save to .manual.json
        manual_path = json_path.with_suffix(".manual.json")
        with open(manual_path, "w") as f:
            json.dump(manual_data, f, indent=2)

        return JsonResponse({"status": "saved", "path": str(manual_path)})

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@require_http_methods(["POST"])
@csrf_exempt
def export_figure(request):
    """
    Export figure in specified format.

    POST /vis/api/editor/export/

    Request body (JSON):
    {
        "json_path": "/path/to/figure.json",
        "csv_path": "/path/to/figure.csv",
        "overrides": {...},
        "format": "png|pdf|svg|tiff",
        "dpi": 300
    }

    Response: Binary file download
    """
    try:
        data = json.loads(request.body)
        json_path = Path(data.get("json_path", ""))
        csv_path = data.get("csv_path")
        overrides = data.get("overrides", {})
        export_format = data.get("format", "png").lower()
        export_dpi = data.get("dpi", 300)

        # Validate format
        valid_formats = ["png", "pdf", "svg", "tiff"]
        if export_format not in valid_formats:
            return JsonResponse(
                {"error": f"Invalid format. Valid: {', '.join(valid_formats)}"}, status=400
            )

        # Load metadata and CSV
        metadata = {}
        if json_path.exists():
            with open(json_path, "r") as f:
                metadata = json.load(f)

        csv_data = None
        if csv_path:
            import pandas as pd

            csv_path = Path(csv_path)
            if csv_path.exists():
                csv_data = pd.read_csv(csv_path)

        # Merge overrides
        full_overrides = _get_scitex_defaults()
        full_overrides.update(_extract_defaults_from_metadata(metadata))
        full_overrides.update(overrides)
        full_overrides["dpi"] = export_dpi

        # Render figure
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from matplotlib.ticker import MaxNLocator

        o = full_overrides
        mm_to_pt = 2.83465

        fig_size = o.get("fig_size", [3.15, 2.68])
        dpi = o.get("dpi", 300)

        fig, ax = plt.subplots(figsize=fig_size, dpi=dpi)

        # Set white background for export (publication)
        fig.patch.set_facecolor("white")
        ax.patch.set_facecolor("white")

        # Plot data
        if csv_data is not None and not csv_data.empty:
            _plot_from_csv(ax, csv_data, o, o.get("linewidth", 0.57), o.get("legend_fontsize", 6))

        # Apply styling
        if o.get("title"):
            ax.set_title(o["title"], fontsize=o.get("title_fontsize", 8))
        if o.get("xlabel"):
            ax.set_xlabel(o["xlabel"], fontsize=o.get("axis_fontsize", 7))
        if o.get("ylabel"):
            ax.set_ylabel(o["ylabel"], fontsize=o.get("axis_fontsize", 7))

        ax.tick_params(
            axis="both",
            labelsize=o.get("tick_fontsize", 7),
            length=o.get("tick_length", 0.8) * mm_to_pt,
            width=o.get("tick_width", 0.2) * mm_to_pt,
            direction=o.get("tick_direction", "out"),
        )

        ax.xaxis.set_major_locator(MaxNLocator(nbins=o.get("n_ticks", 4)))
        ax.yaxis.set_major_locator(MaxNLocator(nbins=o.get("n_ticks", 4)))

        if o.get("xlim"):
            ax.set_xlim(o["xlim"])
        if o.get("ylim"):
            ax.set_ylim(o["ylim"])

        if o.get("hide_top_spine", True):
            ax.spines["top"].set_visible(False)
        if o.get("hide_right_spine", True):
            ax.spines["right"].set_visible(False)

        axis_width_pt = o.get("axis_width", 0.2) * mm_to_pt
        for spine in ax.spines.values():
            spine.set_linewidth(axis_width_pt)

        fig.tight_layout()

        # Export to buffer
        buf = io.BytesIO()
        fig.savefig(buf, format=export_format, dpi=dpi, bbox_inches="tight")
        buf.seek(0)
        plt.close(fig)

        # Content types
        content_types = {
            "png": "image/png",
            "pdf": "application/pdf",
            "svg": "image/svg+xml",
            "tiff": "image/tiff",
        }

        response = HttpResponse(buf.getvalue(), content_type=content_types[export_format])
        filename = f"{json_path.stem}.{export_format}"
        response["Content-Disposition"] = f'attachment; filename="{filename}"'

        return response

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@require_http_methods(["GET"])
def get_scitex_style(request):
    """
    Get SCITEX_STYLE configuration for the frontend.

    GET /vis/api/editor/style/

    Response:
    {
        "style": {...},  // SCITEX_STYLE-compatible defaults
        "defaults": {...}  // Default values for editor
    }
    """
    try:
        defaults = _get_scitex_defaults()

        return JsonResponse(
            {
                "style": defaults,  # Use same defaults for style
                "defaults": defaults,
            }
        )

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
