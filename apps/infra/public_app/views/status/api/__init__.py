#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Status API endpoints package.

Re-exports all API endpoint functions for URL routing.
"""

from __future__ import annotations

from .aggregate import status_api
from .health import healthz, server_health_status_api, versions_api
from .history import server_metrics_export_csv, server_metrics_history_api
from .realtime import server_status_api, visitor_resources_api
from .series import server_metrics_series_api

__all__ = [
    "healthz",
    "status_api",
    "server_health_status_api",
    "server_metrics_export_csv",
    "server_metrics_history_api",
    "server_metrics_series_api",
    "server_status_api",
    "versions_api",
    "visitor_resources_api",
]


# EOF
