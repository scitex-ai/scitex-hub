#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The retired visitor pool has no public status or capacity surface."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from django.conf import settings

from apps.infra.public_app import tasks
from apps.infra.public_app.models import ServerMetrics
from apps.infra.public_app.views import status
from apps.infra.public_app.views.status import server
from apps.infra.public_app.views.status.api.health import _build_services_dict
from apps.infra.public_app.views.status.api.history import _format_metric
from apps.infra.public_app.views.status.api.series import CHART_SPECS

ROOT = Path(__file__).resolve().parents[5]
PUBLIC_APP = ROOT / "apps" / "infra" / "public_app"

RETIRED_PUBLIC_FILES = (
    "views/status/visitor.py",
    "views/status/visitor_pool_health.py",
    "templates/public_app/visitor_status.html",
    "templates/public_app/visitor_expired.html",
    "templates/public_app/visitor_pool_full.html",
    "static/public_app/css/visitor-status.css",
    "static/public_app/css/visitor-pool-full.css",
    "static/public_app/css/server-status/visitor-pool.css",
    "static/public_app/css/server-status/slots.css",
    "static/public_app/ts/visitor-status.ts",
    "static/public_app/ts/_server-status/visitor-countdown.ts",
    "static/public_app/ts/pages/visitor-pool-full.ts",
)

VISITOR_METRIC_FIELDS = {"visitor_pool_allocated", "visitor_pool_total"}
RETIRED_SHARED_FILES = (
    "static/shared/ts/components/visitor-countdown.ts",
    "static/shared/ts/utils/visitor-heartbeat.ts",
    "static/shared/ts/utils/visitor-session-lease.ts",
)


def test_retired_public_visitor_files_are_deleted():
    remaining = [path for path in RETIRED_PUBLIC_FILES if (PUBLIC_APP / path).exists()]
    assert remaining == []


def test_retired_shared_visitor_session_files_are_deleted():
    remaining = [path for path in RETIRED_SHARED_FILES if (ROOT / path).exists()]
    assert remaining == []


def test_status_package_exports_no_visitor_endpoints():
    retired = {
        "visitor_status",
        "visitor_enter",
        "visitor_restart_session",
        "visitor_expired",
        "visitor_pool_full",
        "visitor_pool_initialize_api",
        "visitor_fill_slots_api",
        "visitor_free_slots_api",
        "visitor_heartbeat_api",
        "visitor_resources_api",
    }
    assert retired.isdisjoint(status.__all__)


def test_server_status_runs_no_visitor_pool_check():
    assert "check_visitor_pool_status" not in server._CHECK_PLACEMENTS


def test_server_metrics_model_has_no_visitor_pool_fields():
    field_names = {field.name for field in ServerMetrics._meta.get_fields()}
    assert VISITOR_METRIC_FIELDS.isdisjoint(field_names)


def test_history_metric_payload_has_no_visitor_pool_fields():
    metric = SimpleNamespace(
        timestamp=SimpleNamespace(timestamp=lambda: 1.0),
        cpu_percent=1,
        memory_percent=2,
        disk_percent=3,
        memory_used_gb=4,
        disk_used_gb=5,
        net_sent_mb=6,
        net_recv_mb=7,
        disk_read_mb=8,
        disk_write_mb=9,
        active_users_count=10,
        gpu_percent=11,
    )
    assert VISITOR_METRIC_FIELDS.isdisjoint(_format_metric(metric))


def test_chart_series_has_no_visitor_pool_panel():
    assert "visitor_pool" not in CHART_SPECS


def test_health_services_payload_has_no_visitor_pool_fields():
    payload = _build_services_dict({})
    assert not any(key.startswith("visitor_pool") for key in payload)


def test_cleanup_task_is_not_exported():
    assert not hasattr(tasks, "cleanup_expired_visitor_allocations")


def test_cleanup_task_is_not_scheduled():
    assert "cleanup-expired-visitor-allocations" not in settings.CELERY_BEAT_SCHEDULE
