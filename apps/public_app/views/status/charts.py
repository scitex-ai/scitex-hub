#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Timestamp: "2025-12-02 16:00:00 (ywatanabe)"
# File: /home/ywatanabe/proj/scitex-cloud/apps/public_app/views/status/charts.py

"""
Server Status Charts - Pre-rendered PNG serving.

Charts are pre-generated every 1 minute by Celery task for:
- 8 metrics × 3 time ranges × 2 themes = 48 images
- Served instantly on request from cache directory.
"""

import logging
from pathlib import Path

from django.http import FileResponse, HttpResponse

logger = logging.getLogger("scitex")

# Chart output directory (shared between Django and Celery containers via /app volume)
CHART_DIR = Path("/app/data/charts")
CHART_DIR.mkdir(exist_ok=True)

# Supported configurations
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


def get_chart_path(metric_type: str, minutes: int, theme: str) -> Path:
    """Get the path for a pre-rendered chart image."""
    return CHART_DIR / f"{metric_type}_{minutes}_{theme}.png"


def render_metric_chart(request, metric_type: str):
    """Serve a pre-rendered metric chart PNG."""
    # Validate metric type
    if metric_type not in METRIC_TYPES:
        return HttpResponse(f"Unknown metric: {metric_type}", status=400)

    # Get parameters
    minutes = int(request.GET.get("minutes", 60))
    theme = request.GET.get("theme", "dark")

    # Normalize to supported time ranges
    if minutes not in TIME_RANGES:
        minutes = min(TIME_RANGES, key=lambda x: abs(x - minutes))

    if theme not in THEMES:
        theme = "dark"

    # Get pre-rendered chart path
    img_path = get_chart_path(metric_type, minutes, theme)

    if not img_path.exists():
        # Chart not yet generated - trigger on-demand generation
        logger.warning(f"Chart not found: {img_path}, generating on-demand")
        try:
            from .chart_generator import generate_single_chart

            generate_single_chart(metric_type, minutes, theme)
        except Exception as e:
            logger.error(f"Failed to generate chart: {e}")
            return HttpResponse("Chart not available", status=503)

    if img_path.exists():
        return FileResponse(
            open(img_path, "rb"),
            content_type="image/png",
            headers={"Cache-Control": "public, max-age=30"},
        )

    return HttpResponse("Chart not available", status=503)


# EOF
