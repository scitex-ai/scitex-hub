"""Plots Render - Plot rendering by type and styling utilities."""

import numpy as np


def render_plot_by_type(
    ax, df, plot_type: str, category: str, overrides: dict, xy_pairs: list
):
    """Render plot based on type using scitex/matplotlib methods."""
    cols = df.columns.tolist()

    if xy_pairs:
        x_col = xy_pairs[0][0]
        y_cols = [pair[1] for pair in xy_pairs]
    else:
        x_col = overrides.get("x_column", cols[0] if len(cols) > 0 else None)
        y_cols = overrides.get("y_columns", cols[1:] if len(cols) > 1 else [])

    if isinstance(y_cols, str):
        y_cols = [y_cols]

    x = df[x_col].values if x_col and x_col in df.columns else np.arange(len(df))

    if plot_type in ["plot", "line", "stx_line"]:
        _render_line_plot(ax, df, xy_pairs, x, y_cols, overrides)
    elif plot_type == "step":
        _render_step_plot(ax, df, xy_pairs, x, y_cols, overrides)
    elif plot_type == "stx_shaded_line":
        _render_shaded_line(ax, df, xy_pairs, x, y_cols)
    elif plot_type == "scatter":
        _render_scatter_plot(ax, df, xy_pairs, x, y_cols, overrides)
    elif plot_type == "stx_scatter":
        _render_stx_scatter(ax, df, x, y_cols, overrides)
    elif plot_type in ["bar", "stx_bar"]:
        _render_bar_plot(ax, df, x, y_cols, plot_type)
    elif plot_type == "barh":
        _render_barh_plot(ax, df, x, y_cols)
    elif plot_type in ["hist", "histogram"]:
        _render_histogram(ax, df, y_cols, overrides)
    elif plot_type in ["box", "boxplot"]:
        _render_boxplot(ax, df, y_cols)
    elif plot_type == "violin":
        _render_violin(ax, df, y_cols)
    elif plot_type == "heatmap":
        _render_heatmap(ax, df)


def _render_line_plot(ax, df, xy_pairs, x, y_cols, overrides):
    """Render line plot."""
    lw = overrides.get("linewidth", 1.0)
    if xy_pairs:
        for x_col_i, y_col, trace_name in xy_pairs:
            if x_col_i in df.columns and y_col in df.columns:
                ax.plot(
                    df[x_col_i].values, df[y_col].values, label=trace_name, linewidth=lw
                )
    else:
        for y_col in y_cols:
            if y_col in df.columns:
                ax.plot(x, df[y_col].values, label=y_col, linewidth=lw)


def _render_step_plot(ax, df, xy_pairs, x, y_cols, overrides):
    """Render step plot."""
    lw = overrides.get("linewidth", 1.0)
    if xy_pairs:
        for x_col_i, y_col, trace_name in xy_pairs:
            if x_col_i in df.columns and y_col in df.columns:
                ax.step(
                    df[x_col_i].values, df[y_col].values, label=trace_name, linewidth=lw
                )
    else:
        for y_col in y_cols:
            if y_col in df.columns:
                ax.step(x, df[y_col].values, label=y_col, linewidth=lw)


def _render_shaded_line(ax, df, xy_pairs, x, y_cols):
    """Render shaded line plot."""
    if xy_pairs:
        for x_col_i, y_col, trace_name in xy_pairs:
            if x_col_i in df.columns and y_col in df.columns:
                x_data, y_data = df[x_col_i].values, df[y_col].values
                ax.plot(x_data, y_data, label=trace_name)
                ax.fill_between(x_data, y_data, alpha=0.3)
    else:
        for y_col in y_cols:
            if y_col in df.columns:
                y = df[y_col].values
                ax.plot(x, y, label=y_col)
                ax.fill_between(x, y, alpha=0.3)


def _render_scatter_plot(ax, df, xy_pairs, x, y_cols, overrides):
    """Render scatter plot."""
    ms = overrides.get("marker_size", 20)
    if xy_pairs:
        for x_col_i, y_col, trace_name in xy_pairs:
            if x_col_i in df.columns and y_col in df.columns:
                ax.scatter(df[x_col_i].values, df[y_col].values, label=trace_name, s=ms)
    else:
        for y_col in y_cols:
            if y_col in df.columns:
                ax.scatter(x, df[y_col].values, label=y_col, s=ms)


def _render_stx_scatter(ax, df, x, y_cols, overrides):
    """Render stx_scatter plot."""
    ms = overrides.get("marker_size", 20)
    for y_col in y_cols:
        if y_col in df.columns:
            y = df[y_col].values
            if hasattr(ax, "stx_scatter"):
                ax.stx_scatter(x, y, label=y_col, s=ms)
            else:
                ax.scatter(x, y, label=y_col, s=ms)


def _render_bar_plot(ax, df, x, y_cols, plot_type):
    """Render bar plot."""
    if len(y_cols) > 0 and y_cols[0] in df.columns:
        y = df[y_cols[0]].values
        if plot_type == "stx_bar" and hasattr(ax, "stx_bar"):
            ax.stx_bar(x, y)
        else:
            ax.bar(x, y)


def _render_barh_plot(ax, df, x, y_cols):
    """Render horizontal bar plot."""
    if len(y_cols) > 0 and y_cols[0] in df.columns:
        ax.barh(x, df[y_cols[0]].values)


def _render_histogram(ax, df, y_cols, overrides):
    """Render histogram."""
    if len(y_cols) > 0 and y_cols[0] in df.columns:
        bins = overrides.get("bins", 10)
        ax.hist(df[y_cols[0]].values, bins=bins, alpha=0.7)


def _render_boxplot(ax, df, y_cols):
    """Render box plot."""
    data = [df[col].values for col in y_cols if col in df.columns]
    if data:
        ax.boxplot(data, labels=y_cols)


def _render_violin(ax, df, y_cols):
    """Render violin plot."""
    data = [df[col].values for col in y_cols if col in df.columns]
    if data:
        positions = list(range(1, len(data) + 1))
        ax.violinplot(data, positions=positions, showmeans=True)
        ax.set_xticks(positions)
        ax.set_xticklabels(y_cols)


def _render_heatmap(ax, df):
    """Render heatmap."""
    import matplotlib.pyplot as plt
    import numpy as np

    numeric_df = df.select_dtypes(include=[np.number])
    if not numeric_df.empty:
        im = ax.imshow(numeric_df.T, aspect="auto", cmap="viridis")
        ax.set_yticks(range(len(numeric_df.columns)))
        ax.set_yticklabels(numeric_df.columns)
        plt.colorbar(im, ax=ax)


def apply_plot_styling(ax, overrides: dict):
    """Apply common styling from overrides."""
    if overrides.get("title"):
        ax.set_title(overrides["title"], fontsize=overrides.get("title_fontsize", 10))
    if overrides.get("xlabel"):
        ax.set_xlabel(overrides["xlabel"], fontsize=overrides.get("axis_fontsize", 9))
    if overrides.get("ylabel"):
        ax.set_ylabel(overrides["ylabel"], fontsize=overrides.get("axis_fontsize", 9))
    if overrides.get("xlim"):
        ax.set_xlim(overrides["xlim"])
    if overrides.get("ylim"):
        ax.set_ylim(overrides["ylim"])
    if overrides.get("grid", False):
        ax.grid(True, alpha=0.3)
    if overrides.get("hide_top_spine", True):
        ax.spines["top"].set_visible(False)
    if overrides.get("hide_right_spine", True):
        ax.spines["right"].set_visible(False)
    ax.tick_params(axis="both", labelsize=overrides.get("tick_fontsize", 8))
