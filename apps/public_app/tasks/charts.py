#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Server status chart generation tasks."""

from __future__ import annotations

import logging

from celery import group, shared_task

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    name="apps.public_app.tasks.generate_single_status_chart",
    ignore_result=True,
    soft_time_limit=30,
    time_limit=45,
)
def generate_single_status_chart(self, metric_type: str, minutes: int, theme: str):
    """
    Generate a single server status chart.

    This task is called in parallel by generate_status_charts.
    """
    try:
        from apps.public_app.views.status.chart_generator import generate_single_chart

        success = generate_single_chart(metric_type, minutes, theme)
        if success:
            logger.debug(f"[Charts] Generated: {metric_type}_{minutes}_{theme}")
        return success

    except Exception as e:
        logger.error(f"[Charts] Failed: {metric_type}_{minutes}_{theme}: {e}")
        return False


@shared_task(
    bind=True,
    name="apps.public_app.tasks.generate_status_charts",
    ignore_result=True,
    soft_time_limit=120,
    time_limit=180,
)
def generate_status_charts(self):
    """
    Pre-generate all server status charts in parallel.

    Dispatches 48 parallel tasks (8 metrics x 3 time ranges x 2 themes)
    to generate all chart combinations concurrently using Celery group.

    Charts are stored in /tmp/scitex_charts/ and served instantly on request.
    """
    try:
        from apps.public_app.views.status.chart_generator import (
            get_all_chart_combinations,
        )

        combinations = get_all_chart_combinations()

        # Create a group of tasks for parallel execution
        chart_tasks = group(
            generate_single_status_chart.s(metric, minutes, theme)
            for metric, minutes, theme in combinations
        )

        # Execute all tasks in parallel
        result = chart_tasks.apply_async()
        logger.info(
            f"[Charts] Dispatched {len(combinations)} chart generation tasks in parallel"
        )

        return {"dispatched": len(combinations)}

    except Exception as e:
        logger.error(f"[Charts] Failed to dispatch chart tasks: {e}", exc_info=True)
        raise


# EOF
