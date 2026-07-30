#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Shared fixtures for the server-status chart tests.

Underscore-prefixed so pytest does not collect it as a test module. Split out
of test_status_charts_client_side.py to keep both test files under the repo's
512-line ceiling.

Context (2026-07-30, operator decision): the /server-status/ charts were
force-generated with figrecipe/matplotlib on the server —
``generate_status_charts`` fanned out 48 child tasks EVERY 60 SECONDS (8
metrics x 3 time ranges x 2 themes), about 69,120 renders/day, each importing
matplotlib + numpy + scipy.signal. They are now drawn in the browser as inline
SVG from one JSON read.
"""

from __future__ import annotations

import importlib
from datetime import timedelta
from pathlib import Path

from django.utils import timezone

REPO_ROOT = Path(__file__).resolve().parents[3]
SETTINGS_CELERY_PATH = REPO_ROOT / "config" / "settings" / "settings_celery.py"
SETTINGS_DEV_PATH = REPO_ROOT / "config" / "settings" / "settings_dev.py"

STATUS_URL = "/server-status/"
SERIES_URL = "/api/server-metrics/series/"

# The eight metric panels the page renders.
CHART_METRICS = (
    "cpu",
    "memory",
    "disk",
    "gpu",
    "disk_io",
    "net_io",
    "visitor_pool",
    "active_users",
)


def code_lines_naming(source: str, names: tuple[str, ...]) -> list[str]:
    """Non-comment, non-blank lines that mention any of ``names``.

    Comment lines are skipped so the deliberate prose about the deleted entry
    (in the settings headers and in the test docstrings) does not read as a
    live declaration.

    Why a line scanner and not a regex on the dict-literal form: the beat entry
    was spelled TWO ways — a dict-literal key in settings_celery.py
    (``"generate-status-charts": {``) and a SUBSCRIPT assignment in
    settings_dev.py (``CELERY_BEAT_SCHEDULE["generate-status-charts"] = {``).
    A pattern anchored to the first form PASSED VACUOUSLY against the second in
    the pre-fix run (measured 2026-07-30), which is exactly the free pass a
    negative assertion gets when its pattern cannot match what it claims is
    absent.
    """
    hits = []
    for line in source.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if any(name in stripped for name in names):
            hits.append(stripped)
    return hits


def import_error_of(module_name: str) -> ImportError | None:
    """Return the ImportError a module raises, or None when it imports."""
    try:
        importlib.import_module(module_name)
    except ImportError as exc:
        return exc
    return None


def seed_metrics(
    minutes: int, step_seconds: int, ends_minutes_ago: int = 0
) -> None:
    """Insert monotonically increasing ServerMetrics rows over a window.

    ``ends_minutes_ago`` moves the whole run back in time so a STALE table
    (rows exist, but all of them old — prod's actual 2026-07-30 state, newest
    row 2.4 hours behind) can be reproduced.

    ``gpu_percent`` is deliberately left NULL: the endpoint must report a
    metric with no samples as unavailable rather than drawing a zero line.
    """
    from apps.infra.public_app.models import ServerMetrics

    now = timezone.now() - timedelta(minutes=ends_minutes_ago)
    samples = (minutes * 60) // step_seconds
    rows = [
        ServerMetrics(
            timestamp=now - timedelta(seconds=step_seconds * (samples - i)),
            cpu_percent=10.0 + (i % 20),
            memory_percent=40.0 + (i % 10),
            memory_used_gb=64.0,
            memory_total_gb=128.0,
            memory_available_gb=64.0,
            disk_percent=55.0,
            disk_used_gb=1100.0,
            disk_total_gb=2000.0,
            disk_read_mb=100.0 * i,
            disk_write_mb=50.0 * i,
            net_sent_mb=20.0 * i,
            net_recv_mb=30.0 * i,
            visitor_pool_allocated=i % 4,
            visitor_pool_total=4,
            active_users_count=i % 3,
        )
        for i in range(samples)
    ]
    ServerMetrics.objects.bulk_create(rows)


# EOF
