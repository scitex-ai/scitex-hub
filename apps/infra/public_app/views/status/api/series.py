#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Server-metrics time series as JSON — the data source for the status charts.

Replaces the server-side PNG render path (2026-07-30, operator decision).
The old path pre-rendered every chart with matplotlib: 8 metrics x 3 time
ranges x 2 themes = 48 Celery child tasks EVERY 60 SECONDS (~69,120 renders
a day), each importing matplotlib + numpy + scipy.signal and calling
``scitex.plt.utils.configure_mpl`` before a ``savefig(dpi=150)``. It put the
``celery`` queue ~97,000 messages deep on prod and had already starved
``cleanup_expired_visitor_allocations``, breaking the visitor pool. This
endpoint serves the same eight panels as ONE cheap JSON read; the browser
draws them as inline SVG.

Three deliberate design decisions:

1. NO scipy, and no separate smoothing pass. The old ``_downsample`` used
   ``scipy.signal.resample``, which is FFT-based: it assumes the signal is
   PERIODIC, so on a non-periodic load trace it rings (Gibbs) and can emit
   NEGATIVE values for a metric that is non-negative by construction.
   Bucket-averaging is both the downsample and the anti-alias filter, is
   O(n) with no dependency, and cannot invent a value outside the observed
   range. Dropping scipy here is a correctness gain, not only a cost cut.
2. Colour is named, never resolved. Each series carries the NAME of a CSS
   custom property; the browser resolves it against the active theme. That
   is what makes the old light/dark 2x render multiplier unnecessary.
3. No silent fallback. An empty window is a 503 that names the problem, not
   a zero-filled series a chart would draw as a convincing flat "no load"
   line. A gap inside a window stays ``null`` (the renderer breaks the line)
   and a metric with no samples at all is reported ``available: false`` with
   a reason.
"""

from __future__ import annotations

import logging
from datetime import timedelta

from django.conf import settings
from django.http import JsonResponse
from django.utils import timezone

from ....models import ServerMetrics

logger = logging.getLogger("scitex")

# Windows the page offers, in minutes. Anything else is a 400 — never
# silently snapped onto a neighbouring window, which would show the caller
# a different time range than the one it asked for.
SUPPORTED_RANGES = (60, 360, 1440)

# Points per series after downsampling. 120 keeps the whole 8-panel payload
# in the low tens of kB while still resolving a 24h window to ~12 min bins.
MAX_POINTS = 120

# Rows read per request before downsampling. At the 60s collection cadence a
# 24h window is ~1,440 rows; the ceiling bounds a runaway backfill.
MAX_ROWS = 5000

# How old the newest sample may be before the window is reported STALE.
# ``collect_server_metrics`` runs every 60s, so five missed collections is
# unambiguous. This is NOT the same failure as an empty window: prod on
# 2026-07-30 had rows 2.4 HOURS old, which means a 24h window still returns
# real data that a chart would draw as if it were current. "Stale" and "fresh"
# must be distinguishable in the payload, or the page silently presents a
# two-hour-old trace as live monitoring.
STALE_AFTER_SECONDS = 300

_PERCENT_AXIS = {"y_label": "Usage (%)", "unit": "%", "y_max": 100}
_RATE_AXIS = {"y_label": "Rate (MB/s)", "unit": " MB/s", "y_max": None}

# Single source of truth for the eight panels: labels, axes, fields and the
# CSS variable each line takes its colour from. The client renders whatever
# this says, so a new metric is a change HERE only.
CHART_SPECS: dict[str, dict] = {
    "cpu": {
        "label": "CPU Usage",
        **_PERCENT_AXIS,
        "series": [
            {
                "key": "cpu",
                "label": "CPU",
                "field": "cpu_percent",
                "color_var": "--chart-cpu",
                "fill": True,
            }
        ],
    },
    "memory": {
        "label": "Memory Usage",
        **_PERCENT_AXIS,
        "series": [
            {
                "key": "memory",
                "label": "Memory",
                "field": "memory_percent",
                "color_var": "--chart-memory",
                "fill": True,
            }
        ],
    },
    "disk": {
        "label": "Disk Usage",
        **_PERCENT_AXIS,
        "series": [
            {
                "key": "disk",
                "label": "Disk",
                "field": "disk_percent",
                "color_var": "--chart-disk",
                "fill": True,
            }
        ],
    },
    "gpu": {
        "label": "GPU Usage",
        **_PERCENT_AXIS,
        "series": [
            {
                "key": "gpu",
                "label": "GPU",
                "field": "gpu_percent",
                "color_var": "--chart-gpu",
                "fill": True,
            }
        ],
    },
    "disk_io": {
        "label": "Disk I/O Rate",
        **_RATE_AXIS,
        "series": [
            {
                "key": "read",
                "label": "Read",
                "field": "disk_read_mb",
                "color_var": "--chart-disk-read",
                "rate": True,
            },
            {
                "key": "write",
                "label": "Write",
                "field": "disk_write_mb",
                "color_var": "--chart-disk-write",
                "rate": True,
            },
        ],
    },
    "net_io": {
        "label": "Network I/O Rate",
        **_RATE_AXIS,
        "series": [
            {
                "key": "sent",
                "label": "Sent",
                "field": "net_sent_mb",
                "color_var": "--chart-net-sent",
                "rate": True,
            },
            {
                "key": "recv",
                "label": "Received",
                "field": "net_recv_mb",
                "color_var": "--chart-net-recv",
                "rate": True,
            },
        ],
    },
    "visitor_pool": {
        "label": "Visitor Pool",
        "y_label": "Slots (n)",
        "unit": "",
        "y_max": "visitor_pool_size",  # resolved per request from settings
        "integer": True,
        "series": [
            {
                "key": "allocated",
                "label": "Allocated",
                "field": "visitor_pool_allocated",
                "color_var": "--chart-visitor-pool",
                "fill": True,
            }
        ],
    },
    "active_users": {
        "label": "Active Users",
        "y_label": "Users (n)",
        "unit": "",
        "y_max": None,
        "integer": True,
        "series": [
            {
                "key": "active",
                "label": "Active",
                "field": "active_users_count",
                "color_var": "--chart-active-users",
                "fill": True,
            }
        ],
    },
}


def server_metrics_series_api(request):
    """Serve every status-page chart's data for one time window as JSON."""
    raw_minutes = request.GET.get("minutes", str(SUPPORTED_RANGES[0]))
    try:
        minutes = int(raw_minutes)
    except (TypeError, ValueError):
        return _bad_range(raw_minutes)
    if minutes not in SUPPORTED_RANGES:
        return _bad_range(raw_minutes)

    now = timezone.now()
    start = now - timedelta(minutes=minutes)
    rows = list(
        ServerMetrics.objects.filter(timestamp__gte=start)
        .order_by("timestamp")
        .values("timestamp", *_needed_fields())[:MAX_ROWS]
    )

    if not rows:
        # Loud, not empty: a zero-filled series renders as a believable flat
        # "no load" trace, which is indistinguishable from a healthy idle host.
        newest = (
            ServerMetrics.objects.order_by("-timestamp")
            .values_list("timestamp", flat=True)
            .first()
        )
        logger.warning(
            "server-metrics series: no ServerMetrics rows in the last %s minutes "
            "(newest row overall: %s)",
            minutes,
            newest,
        )
        return JsonResponse(
            {
                "error": "no-metrics",
                "detail": (
                    f"No server metrics recorded in the last {minutes} minutes. "
                    "collect_server_metrics is not running."
                ),
                "minutes": minutes,
                # Distinguishes "the collector never ran" from "the collector
                # stopped N hours ago", which is the state prod was in on
                # 2026-07-30 (newest row 2.4h old).
                "latest_sample_at": newest.isoformat() if newest else None,
                "latest_sample_age_seconds": (
                    int((now - newest).total_seconds()) if newest else None
                ),
            },
            status=503,
        )

    buckets = _bucket_ranges(len(rows), MAX_POINTS)
    timestamps = [_bucket_timestamp(rows, lo, hi) for lo, hi in buckets]

    latest = rows[-1]["timestamp"]
    age_seconds = int((now - latest).total_seconds())
    stale = age_seconds > STALE_AFTER_SECONDS

    if stale:
        logger.warning(
            "server-metrics series: newest sample is %ss old (> %ss); "
            "collect_server_metrics may not be running",
            age_seconds,
            STALE_AFTER_SECONDS,
        )

    return JsonResponse(
        {
            "minutes": minutes,
            "generated_at": now.isoformat(),
            "start": start.isoformat(),
            "sample_count": len(rows),
            "max_points": MAX_POINTS,
            "latest_sample_at": latest.isoformat(),
            "latest_sample_age_seconds": age_seconds,
            "stale_after_seconds": STALE_AFTER_SECONDS,
            "stale": stale,
            # Two forms on purpose. The BADGE is drawn inside each chart, where
            # the plot box is 438 user units wide and a full sentence would both
            # overflow it and collide with the multi-series legend. The REASON is
            # the page-level banner text.
            "stale_badge": _stale_badge(age_seconds) if stale else None,
            "stale_reason": _stale_reason(age_seconds) if stale else None,
            "t": timestamps,
            "charts": {
                name: _build_chart(spec, rows, buckets)
                for name, spec in CHART_SPECS.items()
            },
        }
    )


def _human_age(age_seconds: int) -> str:
    """Compact age: minutes below an hour, then hours to one decimal."""
    if age_seconds < 3600:
        return f"{age_seconds // 60} min"
    return f"{age_seconds / 3600:.1f} h"


def _stale_badge(age_seconds: int) -> str:
    """Short in-chart caption. Must fit the 438-unit-wide plot box."""
    return f"{_human_age(age_seconds)} stale"


def _stale_reason(age_seconds: int) -> str:
    """Say how far behind the data is, in words a reader can act on."""
    return (
        f"Newest sample is {_human_age(age_seconds)} old — collect_server_metrics "
        "is not keeping up, so these charts are history, not live monitoring."
    )


def _bad_range(raw_minutes: str) -> JsonResponse:
    """Reject an unsupported window instead of quietly serving another one."""
    return JsonResponse(
        {
            "error": "unsupported-range",
            "detail": (
                f"minutes={raw_minutes!r} is not offered. "
                f"Supported: {', '.join(str(m) for m in SUPPORTED_RANGES)}."
            ),
            "supported": list(SUPPORTED_RANGES),
        },
        status=400,
    )


def _needed_fields() -> list[str]:
    """Every model field any spec reads (deduplicated, stable order)."""
    fields: list[str] = []
    for spec in CHART_SPECS.values():
        for series in spec["series"]:
            if series["field"] not in fields:
                fields.append(series["field"])
    return fields


def _build_chart(spec: dict, rows: list[dict], buckets: list[tuple[int, int]]) -> dict:
    """Downsample every line of one panel and report its availability."""
    lines = []
    for series in spec["series"]:
        if series.get("rate"):
            per_row = _rates(rows, series["field"])
        else:
            per_row = [row[series["field"]] for row in rows]
        lines.append(
            {
                "key": series["key"],
                "label": series["label"],
                "color_var": series["color_var"],
                "fill": bool(series.get("fill")),
                "values": [_mean(per_row[lo:hi]) for lo, hi in buckets],
            }
        )

    has_data = any(v is not None for line in lines for v in line["values"])
    return {
        "label": spec["label"],
        "y_label": spec["y_label"],
        "unit": spec["unit"],
        "y_max": _resolve_y_max(spec["y_max"]),
        "integer": bool(spec.get("integer")),
        "available": has_data,
        "reason": None if has_data else "No samples recorded for this metric.",
        "series": lines,
    }


def _resolve_y_max(y_max):
    """Resolve a symbolic y_max at request time so settings stay authoritative."""
    if y_max == "visitor_pool_size":
        pool_size = getattr(settings, "SCITEX_HUB_VISITOR_POOL_SIZE", 4) or 4
        return int(pool_size)
    return y_max


def _rates(rows: list[dict], field: str) -> list[float | None]:
    """Per-second deltas of a cumulative counter.

    The first row has no predecessor, so its rate is ``None`` (a gap), not 0
    — a fabricated leading zero is a visible dip that never happened. A
    counter that went BACKWARDS means the host or the device counter reset;
    that clamps to 0 rather than reporting negative throughput.
    """
    rates: list[float | None] = [None]
    for prev, cur in zip(rows, rows[1:]):
        prev_value, cur_value = prev[field], cur[field]
        if prev_value is None or cur_value is None:
            rates.append(None)
            continue
        seconds = (cur["timestamp"] - prev["timestamp"]).total_seconds()
        if seconds <= 0:
            rates.append(None)
            continue
        rates.append(max(0.0, (cur_value - prev_value) / seconds))
    return rates


def _bucket_ranges(n: int, max_points: int) -> list[tuple[int, int]]:
    """Split ``n`` ordered rows into at most ``max_points`` contiguous bins."""
    if n <= max_points:
        return [(i, i + 1) for i in range(n)]
    ranges = []
    for bucket in range(max_points):
        lo = (bucket * n) // max_points
        hi = ((bucket + 1) * n) // max_points
        ranges.append((lo, max(hi, lo + 1)))
    return ranges


def _bucket_timestamp(rows: list[dict], lo: int, hi: int) -> int:
    """Epoch-ms stamp for one bin: the midpoint of the rows it covers."""
    first = rows[lo]["timestamp"].timestamp()
    last = rows[hi - 1]["timestamp"].timestamp()
    return int(((first + last) / 2) * 1000)


def _mean(values: list) -> float | None:
    """Mean of the non-null values, or ``None`` when the bin holds no data."""
    present = [v for v in values if v is not None]
    if not present:
        return None
    return round(sum(present) / len(present), 4)


# EOF
