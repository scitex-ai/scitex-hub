#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Public app Celery tasks.

Re-exports all tasks for Celery autodiscovery.
"""

from __future__ import annotations

from .charts import generate_single_status_chart, generate_status_charts
from .health import (
    HEALTH_CHECK_CACHE_KEY,
    HEALTH_CHECK_FAILURE_COUNT_KEY,
    HEALTH_CHECK_LAST_NOTIFICATION_KEY,
    FLOOD_DETECTION_PREFIX,
    FLOOD_ALERT_LAST_SENT_KEY,
    check_site_health,
    cleanup_expired_visitor_allocations,
    check_request_flood,
    warm_public_status_cache,
)
from .metrics import collect_server_metrics
from .utils import check_port

__all__ = [
    # Metrics
    "collect_server_metrics",
    # Charts
    "generate_single_status_chart",
    "generate_status_charts",
    # Health
    "cleanup_expired_visitor_allocations",
    "check_site_health",
    "check_request_flood",
    "warm_public_status_cache",
    "HEALTH_CHECK_CACHE_KEY",
    "HEALTH_CHECK_FAILURE_COUNT_KEY",
    "HEALTH_CHECK_LAST_NOTIFICATION_KEY",
    "FLOOD_DETECTION_PREFIX",
    "FLOOD_ALERT_LAST_SENT_KEY",
    # Utils
    "check_port",
]


# EOF
