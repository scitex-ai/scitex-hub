#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Public app Celery tasks.

Re-exports all tasks for Celery autodiscovery.
"""

from __future__ import annotations

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
from .liveness import (
    LIVENESS_KEY_PREFIX,
    liveness_key,
    queue_liveness_beacon,
    write_liveness_stamp,
)
from .metrics import collect_server_metrics
from .utils import check_port

__all__ = [
    # Metrics
    "collect_server_metrics",
    # NOTE: no chart-render tasks. The /server-status/ charts are drawn in the
    # browser from /api/server-metrics/series/ (2026-07-30). The deleted
    # dispatcher fanned out 48 matplotlib renders every 60s into a container
    # path django could not read, so it never delivered a chart.
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
    # Liveness (end-to-end queue watchdog)
    "LIVENESS_KEY_PREFIX",
    "liveness_key",
    "queue_liveness_beacon",
    "write_liveness_stamp",
    # Utils
    "check_port",
]


# EOF
