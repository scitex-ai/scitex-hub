"""Chart generator for LLM usage dashboard — returns PNG bytes."""

import io
import logging
from typing import Dict, List

import matplotlib

matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.ticker import MaxNLocator

logger = logging.getLogger("scitex")

# Dark-theme palette, originally copied from the server-status chart_generator
# (deleted 2026-07-30 — those charts are now browser-rendered SVG). This one is
# request-driven from the LLM usage admin view, not a Celery fan-out, so it was
# left on matplotlib.
_THEME = {
    "bg": "none",
    "axis": "#b5c7d1",
    "tick": "#d0dce3",
}

_COLORS = {
    "cost": "#FF6384",
    "tokens": "#36A2EB",
    "requests": "#4BC0C0",
}

_FIG_W = 5.0  # inches
_FIG_H = 3.0  # inches
_DPI = 150


def _fig_to_bytes(fig) -> bytes:
    """Serialize figure to PNG bytes and close it."""
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=_DPI, transparent=True, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf.read()


def _style_axes(ax):
    """Apply consistent dark-theme styling to an axes object."""
    ax.patch.set_alpha(0)
    ax.spines["bottom"].set_color(_THEME["axis"])
    ax.spines["left"].set_color(_THEME["axis"])
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.tick_params(axis="both", colors=_THEME["tick"], labelsize=9)
    ax.xaxis.label.set_color(_THEME["tick"])
    ax.yaxis.label.set_color(_THEME["tick"])


def generate_cost_chart(time_series: List[Dict], days: int = 30) -> bytes:
    """Daily cost line chart.

    Args:
        time_series: Output from get_usage_time_series().
        days: Label for x-axis context.

    Returns:
        PNG image as bytes.
    """
    fig, ax = plt.subplots(figsize=(_FIG_W, _FIG_H))
    fig.patch.set_alpha(0)

    if time_series:
        dates = [row["date"] for row in time_series]
        costs = [row["cost"] for row in time_series]
        ax.plot(
            dates, costs, color=_COLORS["cost"], linewidth=1.5, marker="o", markersize=3
        )
        ax.fill_between(dates, costs, alpha=0.15, color=_COLORS["cost"])
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%m/%d"))
        ax.xaxis.set_major_locator(mdates.AutoDateLocator(minticks=3, maxticks=5))
    else:
        ax.text(
            0.5,
            0.5,
            "No data",
            transform=ax.transAxes,
            ha="center",
            va="center",
            color=_THEME["tick"],
            fontsize=12,
        )

    ax.set_ylim(bottom=0)
    ax.yaxis.set_major_locator(MaxNLocator(nbins=4))
    ax.set_xlabel("Date", fontsize=10)
    ax.set_ylabel("Cost (USD)", fontsize=10)
    _style_axes(ax)
    fig.tight_layout()
    return _fig_to_bytes(fig)


def generate_tokens_chart(time_series: List[Dict], days: int = 30) -> bytes:
    """Daily token usage bar chart.

    Args:
        time_series: Output from get_usage_time_series().
        days: Label for x-axis context.

    Returns:
        PNG image as bytes.
    """
    fig, ax = plt.subplots(figsize=(_FIG_W, _FIG_H))
    fig.patch.set_alpha(0)

    if time_series:
        dates = [row["date"] for row in time_series]
        tokens = [row["tokens"] for row in time_series]
        # Use bar width proportional to number of days shown
        bar_width = max(0.5, 20.0 / max(len(dates), 1))
        ax.bar(dates, tokens, color=_COLORS["tokens"], alpha=0.8, width=bar_width)
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%m/%d"))
        ax.xaxis.set_major_locator(mdates.AutoDateLocator(minticks=3, maxticks=5))
    else:
        ax.text(
            0.5,
            0.5,
            "No data",
            transform=ax.transAxes,
            ha="center",
            va="center",
            color=_THEME["tick"],
            fontsize=12,
        )

    ax.set_ylim(bottom=0)
    ax.yaxis.set_major_locator(MaxNLocator(nbins=4, integer=True))
    ax.set_xlabel("Date", fontsize=10)
    ax.set_ylabel("Tokens", fontsize=10)
    _style_axes(ax)
    fig.tight_layout()
    return _fig_to_bytes(fig)


def generate_model_breakdown_chart(model_data: List[Dict]) -> bytes:
    """Horizontal bar chart of token usage by model.

    Args:
        model_data: Output from get_usage_by_model().

    Returns:
        PNG image as bytes.
    """
    fig, ax = plt.subplots(figsize=(_FIG_W, _FIG_H))
    fig.patch.set_alpha(0)

    if model_data:
        # Show top 8 models at most to keep chart readable
        data = model_data[:8]
        labels = [d["model"] for d in data]
        tokens = [d["tokens"] for d in data]

        # Truncate long model names
        labels = [lbl if len(lbl) <= 24 else lbl[:21] + "..." for lbl in labels]

        palette = [
            "#36A2EB",
            "#FF6384",
            "#4BC0C0",
            "#FF9F40",
            "#9966FF",
            "#FFCD56",
            "#C9CBCF",
            "#FF6384",
        ]
        colors = [palette[i % len(palette)] for i in range(len(labels))]

        y_pos = np.arange(len(labels))
        ax.barh(y_pos, tokens, color=colors, alpha=0.85)
        ax.set_yticks(y_pos)
        ax.set_yticklabels(labels, fontsize=8, color=_THEME["tick"])
        ax.xaxis.set_major_locator(MaxNLocator(nbins=4, integer=True))
    else:
        ax.text(
            0.5,
            0.5,
            "No data",
            transform=ax.transAxes,
            ha="center",
            va="center",
            color=_THEME["tick"],
            fontsize=12,
        )

    ax.set_xlim(left=0)
    ax.set_xlabel("Tokens", fontsize=10)
    _style_axes(ax)
    fig.tight_layout()
    return _fig_to_bytes(fig)
