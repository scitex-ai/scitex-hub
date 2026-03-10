"""SciTeX Editor Render - Figure rendering and plotting utilities."""

import base64
import io


def render_figure_preview(metadata, csv_data, overrides):
    """Render figure as base64 PNG with applied overrides."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.ticker import MaxNLocator

    mm_to_pt = 2.83465
    o = overrides

    dpi = o.get("dpi", 300)
    fig_size = o.get("fig_size", [3.15, 2.68])
    axis_fontsize = o.get("axis_fontsize", 7)
    tick_fontsize = o.get("tick_fontsize", 7)
    title_fontsize = o.get("title_fontsize", 8)
    legend_fontsize = o.get("legend_fontsize", 6)
    linewidth_pt = o.get("linewidth", 0.57)
    axis_width_pt = o.get("axis_width", 0.2) * mm_to_pt
    tick_length_pt = o.get("tick_length", 0.8) * mm_to_pt
    tick_width_pt = o.get("tick_width", 0.2) * mm_to_pt
    tick_direction = o.get("tick_direction", "out")
    n_ticks = o.get("n_ticks", 4)
    transparent = o.get("transparent", True)

    fig, ax = plt.subplots(figsize=fig_size, dpi=dpi)
    if transparent:
        fig.patch.set_facecolor("none")
        ax.patch.set_facecolor("none")
    elif o.get("facecolor"):
        fig.patch.set_facecolor(o["facecolor"])
        ax.patch.set_facecolor(o["facecolor"])

    if csv_data is not None and not csv_data.empty:
        plot_from_csv(ax, csv_data, o, linewidth_pt, legend_fontsize)
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

    if o.get("title"):
        ax.set_title(o["title"], fontsize=title_fontsize)
    if o.get("xlabel"):
        ax.set_xlabel(o["xlabel"], fontsize=axis_fontsize)
    if o.get("ylabel"):
        ax.set_ylabel(o["ylabel"], fontsize=axis_fontsize)

    ax.tick_params(
        axis="both",
        labelsize=tick_fontsize,
        length=tick_length_pt,
        width=tick_width_pt,
        direction=tick_direction,
    )
    ax.xaxis.set_major_locator(MaxNLocator(nbins=n_ticks))
    ax.yaxis.set_major_locator(MaxNLocator(nbins=n_ticks))

    if o.get("grid"):
        ax.grid(True, linewidth=axis_width_pt, alpha=0.3)
    if o.get("xlim"):
        ax.set_xlim(o["xlim"])
    if o.get("ylim"):
        ax.set_ylim(o["ylim"])
    if o.get("hide_top_spine", True):
        ax.spines["top"].set_visible(False)
    if o.get("hide_right_spine", True):
        ax.spines["right"].set_visible(False)
    for spine in ax.spines.values():
        spine.set_linewidth(axis_width_pt)

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

    buf = io.BytesIO()
    fig.savefig(
        buf, format="png", dpi=dpi, bbox_inches="tight", transparent=transparent
    )
    buf.seek(0)
    img_data = base64.b64encode(buf.read()).decode("utf-8")
    plt.close(fig)

    return img_data


def plot_from_csv(ax, df, overrides, linewidth, legend_fontsize):
    """Reconstruct plot from CSV data using trace info."""
    o = overrides
    legend_visible = o.get("legend_visible", True)
    legend_frameon = o.get("legend_frameon", False)
    legend_loc = o.get("legend_loc", "best")
    traces = o.get("traces", [])

    if traces:
        for trace in traces:
            csv_cols = trace.get("csv_columns", {})
            x_col, y_col = csv_cols.get("x"), csv_cols.get("y")
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
        _plot_fallback(
            ax,
            df,
            linewidth,
            legend_fontsize,
            legend_visible,
            legend_frameon,
            legend_loc,
        )


def _plot_fallback(
    ax, df, linewidth, legend_fontsize, legend_visible, legend_frameon, legend_loc
):
    """Fallback plotting when no trace info available."""
    cols = df.columns.tolist()
    trace_groups = {}

    for col in cols:
        if col.endswith("_x"):
            trace_id = col[:-2]
            y_col = trace_id + "_y"
            if y_col in cols:
                parts = trace_id.split("_")
                label = parts[2] if len(parts) > 2 else trace_id
                trace_groups[trace_id] = {"x_col": col, "y_col": y_col, "label": label}

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


def render_export_figure(csv_data, overrides, export_format, export_dpi):
    """Render figure for export in specified format."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.ticker import MaxNLocator

    o = overrides
    mm_to_pt = 2.83465

    fig_size = o.get("fig_size", [3.15, 2.68])
    dpi = o.get("dpi", export_dpi)

    fig, ax = plt.subplots(figsize=fig_size, dpi=dpi)
    fig.patch.set_facecolor("white")
    ax.patch.set_facecolor("white")

    if csv_data is not None and not csv_data.empty:
        plot_from_csv(
            ax, csv_data, o, o.get("linewidth", 0.57), o.get("legend_fontsize", 6)
        )

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

    buf = io.BytesIO()
    fig.savefig(buf, format=export_format, dpi=dpi, bbox_inches="tight")
    buf.seek(0)
    plt.close(fig)

    return buf.getvalue()
