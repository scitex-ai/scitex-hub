#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Timestamp: "2025-12-02 16:00:00 (ywatanabe)"
# File: /home/ywatanabe/proj/scitex-hub/apps/public_app/views/status/chart_generator.py

"""
Chart Generator - Creates metric charts for server status page.

Pre-generates all chart combinations:
- 8 metrics × 3 time ranges × 2 themes = 48 images
- Called by Celery task every 1 minute.
"""

import logging
from datetime import timedelta
from pathlib import Path

import matplotlib
import numpy as np
from scipy import signal

matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger("scitex")

# Chart output directory (shared between Django and Celery containers via /app volume)
CHART_DIR = Path("/app/data/charts")
CHART_DIR.mkdir(exist_ok=True)

# Chart configurations
METRIC_TYPES = [
    "cpu",
    "memory",
    "disk",
    "gpu",
    "disk_io",
    "net_io",
    "visitor_pool",
    "active_users",
]
TIME_RANGES = [60, 360, 1440]  # 1h, 6h, 24h in minutes
THEMES = ["dark", "light"]

# Fixed chart dimensions (mm)
WIDTH_MM = 100
HEIGHT_MM = 60

# Maximum data points for smooth line plots
MAX_DATA_POINTS = 60

# Theme colors (transparent background, high contrast text)
THEME_COLORS = {
    "dark": {
        "bg": "none",  # Transparent
        "axis": "#b5c7d1",  # Lighter for visibility
        "tick": "#d0dce3",  # Even lighter for text
    },
    "light": {
        "bg": "none",  # Transparent
        "axis": "#2a3f4d",  # Darker for visibility
        "tick": "#1a2a35",  # Even darker for text
    },
}

# Metric configurations with axis labels and units
CHART_CONFIGS = {
    "cpu": {
        "color": "#36A2EB",
        "y_max": 100,
        "fill": True,
        "field": "cpu_percent",
        "ylabel": "Usage (%)",
        "xlabel": "Time",
    },
    "memory": {
        "color": "#FF6384",
        "y_max": 100,
        "fill": True,
        "field": "memory_percent",
        "ylabel": "Usage (%)",
        "xlabel": "Time",
    },
    "disk": {
        "color": "#4BC0C0",
        "y_max": 100,
        "fill": True,
        "field": "disk_percent",
        "ylabel": "Usage (%)",
        "xlabel": "Time",
    },
    "gpu": {
        "color": "#9966FF",
        "y_max": 100,
        "fill": True,
        "field": "gpu_percent",
        "ylabel": "Usage (%)",
        "xlabel": "Time",
    },
    "disk_io": {
        "colors": ["#4BC0C0", "#FF9F40"],
        "labels": ["Read", "Write"],
        "fields": ["disk_read_mb", "disk_write_mb"],
        "ylabel": "Rate (MB/s)",
        "xlabel": "Time",
    },
    "net_io": {
        "colors": ["#FF6384", "#36A2EB"],
        "labels": ["Sent", "Recv"],
        "fields": ["net_sent_mb", "net_recv_mb"],
        "ylabel": "Rate (MB/s)",
        "xlabel": "Time",
    },
    "visitor_pool": {
        "color": "#C9CBCF",
        "y_max": int(getattr(settings, "SCITEX_HUB_VISITOR_POOL_SIZE", 4) * 1.1),
        "fill": True,
        "field": "visitor_pool_allocated",
        "ylabel": "Slots (n)",
        "xlabel": "Time",
    },
    "active_users": {
        "color": "#4BC0C0",
        "fill": True,
        "field": "active_users_count",
        "ylabel": "Users (n)",
        "xlabel": "Time",
    },
}


def get_chart_path(metric_type: str, minutes: int, theme: str) -> Path:
    """Get the path for a chart image."""
    return CHART_DIR / f"{metric_type}_{minutes}_{theme}.png"


def generate_single_chart(metric_type: str, minutes: int, theme: str) -> bool:
    """Generate a single chart image."""
    from apps.infra.public_app.models import ServerMetrics

    try:
        # Apply SCITEX_STYLE via configure_mpl
        from scitex.plt.utils import configure_mpl

        plt_configured, _ = configure_mpl(
            plt,
            hide_top_right_spines=True,
            line_width=1.0,
            dpi_save=150,
        )

        # Query data
        start_time = timezone.now() - timedelta(minutes=minutes)
        metrics = list(
            ServerMetrics.objects.filter(timestamp__gte=start_time).order_by(
                "timestamp"
            )
        )

        if not metrics:
            logger.debug(f"No data for {metric_type} ({minutes}min)")
            return False

        # Extract and downsample data
        raw_timestamps = [m.timestamp for m in metrics]
        config = CHART_CONFIGS.get(metric_type, CHART_CONFIGS["cpu"])
        data = _extract_metric_data(metrics, config)

        # Downsample timestamps to match data
        timestamps = _downsample_timestamps(raw_timestamps)

        # Get theme colors
        colors = THEME_COLORS[theme]

        # Create figure with transparent background
        fig, ax = plt_configured.subplots(figsize=(WIDTH_MM / 25.4, HEIGHT_MM / 25.4))
        fig.patch.set_alpha(0)  # Transparent figure background
        ax.patch.set_alpha(0)  # Transparent axes background

        # Plot data - ensure timestamps and data have same length
        n_points = min(
            len(timestamps),
            (
                len(data)
                if not isinstance(data, dict)
                else min(len(v) for v in data.values())
            ),
        )
        timestamps = timestamps[:n_points]

        if isinstance(data, dict):
            # Multi-line chart (disk_io, net_io)
            chart_colors = config.get("colors", ["#4BC0C0", "#FF9F40"])
            labels = config.get("labels", list(data.keys()))
            for i, (key, values) in enumerate(data.items()):
                y = np.array(values[:n_points])
                ax.plot(
                    timestamps,
                    y,
                    color=chart_colors[i % len(chart_colors)],
                    linewidth=1.0,
                    label=labels[i] if i < len(labels) else key,
                )
            ax.legend(
                fontsize=13,
                loc="lower right",
                bbox_to_anchor=(1, 1.02),  # Above axes, right-aligned
                frameon=False,
                labelcolor=colors["tick"],
                ncol=2,  # Horizontal layout
            )
        else:
            # Single line chart (no fill for consistency)
            color = config.get("color", "#36A2EB")
            y = np.array(data[:n_points])
            ax.plot(timestamps, y, color=color, linewidth=1)

        # Y limits
        if "y_max" in config:
            ax.set_ylim(0, config["y_max"])
        else:
            ax.set_ylim(bottom=0)

        # Format x-axis (3-4 ticks)
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
        ax.xaxis.set_major_locator(mdates.AutoDateLocator(minticks=3, maxticks=4))

        # Set y-axis ticks (3-4 ticks)
        ax.yaxis.set_major_locator(plt_configured.MaxNLocator(nbins=3, integer=True))

        # Set axis labels with units (scientific rigor)
        xlabel = config.get("xlabel", "Time")
        ylabel = config.get("ylabel", "Value")
        ax.set_xlabel(xlabel, fontsize=12)
        ax.set_ylabel(ylabel, fontsize=12)

        # Apply theme colors for visibility
        ax.spines["bottom"].set_color(colors["axis"])
        ax.spines["left"].set_color(colors["axis"])
        ax.tick_params(axis="both", colors=colors["tick"], labelsize=11)
        ax.xaxis.label.set_color(colors["tick"])
        ax.yaxis.label.set_color(colors["tick"])

        # Make tick labels bold for better readability
        for label in ax.get_xticklabels() + ax.get_yticklabels():
            label.set_fontweight("medium")

        # Save with transparent background
        fig.tight_layout()
        img_path = get_chart_path(metric_type, minutes, theme)
        fig.savefig(str(img_path), dpi=150, transparent=True, format="png")
        plt_configured.close(fig)

        return True

    except Exception as e:
        logger.error(f"Failed to generate chart {metric_type}_{minutes}_{theme}: {e}")
        return False
    finally:
        plt.close("all")


def generate_all_charts() -> dict:
    """Generate all chart combinations sequentially. Use generate_all_charts_parallel for speed."""
    results = {"success": 0, "failed": 0, "skipped": 0}

    for metric in METRIC_TYPES:
        for minutes in TIME_RANGES:
            for theme in THEMES:
                try:
                    if generate_single_chart(metric, minutes, theme):
                        results["success"] += 1
                    else:
                        results["skipped"] += 1
                except Exception as e:
                    logger.error(
                        f"Chart generation failed: {metric}_{minutes}_{theme}: {e}"
                    )
                    results["failed"] += 1

    logger.info(f"Chart generation complete: {results}")
    return results


def get_all_chart_combinations() -> list:
    """Get all (metric, minutes, theme) combinations."""
    combinations = []
    for metric in METRIC_TYPES:
        for minutes in TIME_RANGES:
            for theme in THEMES:
                combinations.append((metric, minutes, theme))
    return combinations


def _downsample(data: list, target_points: int = MAX_DATA_POINTS) -> np.ndarray:
    """Downsample data using scipy.signal.resample."""
    arr = np.array(data, dtype=float)
    n = len(arr)
    if n <= target_points:
        return arr

    return signal.resample(arr, target_points)


def _downsample_timestamps(
    timestamps: list, target_points: int = MAX_DATA_POINTS
) -> list:
    """Downsample timestamps by selecting evenly spaced points."""
    n = len(timestamps)
    if n <= target_points:
        return timestamps

    indices = np.linspace(0, n - 1, target_points, dtype=int)
    return [timestamps[i] for i in indices]


def _extract_metric_data(metrics, config: dict):
    """Extract data from metrics queryset."""
    if "fields" in config:
        # Multi-field (dict return for I/O charts)
        data = {}
        for field in config["fields"]:
            values = []
            prev_val = 0
            for m in metrics:
                val = getattr(m, field, None)
                if val is not None:
                    # Calculate rate (difference from previous)
                    rate = max(0, val - prev_val) if prev_val > 0 else 0
                    values.append(rate)
                    prev_val = val
                else:
                    values.append(0)
            data[field] = _downsample(values)
        return data
    else:
        # Single field
        field = config["field"]
        values = [getattr(m, field, 0) or 0 for m in metrics]
        return _downsample(values)


# EOF
