#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Server metrics history API endpoints."""

from __future__ import annotations

import csv
import logging
from datetime import timedelta

from django.http import HttpResponse, JsonResponse
from django.utils import timezone

from ....models import ServerMetrics

logger = logging.getLogger("scitex")


def server_metrics_history_api(request):
    """API endpoint for historical server metrics (returns JSON)."""
    try:
        hours = int(request.GET.get("hours", 24))
        limit = int(request.GET.get("limit", 1000))

        start_time = timezone.now() - timedelta(hours=hours)
        metrics = ServerMetrics.objects.filter(timestamp__gte=start_time).order_by(
            "timestamp"
        )[:limit]

        data = {
            "count": metrics.count(),
            "start_time": start_time.isoformat(),
            "end_time": timezone.now().isoformat(),
            "metrics": [_format_metric(m) for m in metrics],
        }

        return JsonResponse(data)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


def _format_metric(m) -> dict:
    """Format a single metric record for JSON response."""
    return {
        "timestamp": int(m.timestamp.timestamp() * 1000),
        "cpu_percent": m.cpu_percent,
        "memory_percent": m.memory_percent,
        "disk_percent": m.disk_percent,
        "memory_used_gb": m.memory_used_gb,
        "disk_used_gb": m.disk_used_gb,
        "net_sent_mb": m.net_sent_mb,
        "net_recv_mb": m.net_recv_mb,
        "disk_read_mb": m.disk_read_mb,
        "disk_write_mb": m.disk_write_mb,
        "visitor_pool_allocated": m.visitor_pool_allocated,
        "visitor_pool_total": m.visitor_pool_total,
        "active_users_count": m.active_users_count,
        "gpu_percent": m.gpu_percent if hasattr(m, "gpu_percent") else None,
    }


def server_metrics_export_csv(request):
    """Export server metrics as CSV file."""
    try:
        hours = int(request.GET.get("hours", 24))
        start_time = timezone.now() - timedelta(hours=hours)

        metrics = ServerMetrics.objects.filter(timestamp__gte=start_time).order_by(
            "timestamp"
        )

        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = (
            f'attachment; filename="server_metrics_{timezone.now().strftime("%Y%m%d_%H%M%S")}.csv"'
        )

        writer = csv.writer(response)
        writer.writerow(_get_csv_header())

        for m in metrics:
            writer.writerow(_format_metric_csv_row(m))

        return response
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


def _get_csv_header() -> list[str]:
    """Get CSV header row."""
    return [
        "Timestamp",
        "CPU %",
        "CPU Cores",
        "CPU Cores Logical",
        "Memory %",
        "Memory Used (TB)",
        "Memory Total (TB)",
        "Memory Available (TB)",
        "Disk %",
        "Disk Used (TB)",
        "Disk Total (TB)",
        "Disk Read (MB)",
        "Disk Write (MB)",
        "Network Sent (MB)",
        "Network Received (MB)",
        "Docker Services",
        "SSH Gateway",
        "Gitea SSH",
        "Database",
        "Redis",
    ]


def _format_metric_csv_row(m) -> list:
    """Format a single metric record for CSV row."""
    return [
        m.timestamp.isoformat(),
        m.cpu_percent,
        m.cpu_cores,
        m.cpu_cores_logical,
        m.memory_percent,
        round(m.memory_used_gb / 1024, 3) if m.memory_used_gb else None,
        round(m.memory_total_gb / 1024, 3) if m.memory_total_gb else None,
        round(m.memory_available_gb / 1024, 3) if m.memory_available_gb else None,
        m.disk_percent,
        round(m.disk_used_gb / 1024, 2) if m.disk_used_gb else None,
        round(m.disk_total_gb / 1024, 2) if m.disk_total_gb else None,
        m.disk_read_mb,
        m.disk_write_mb,
        m.net_sent_mb,
        m.net_recv_mb,
        m.docker_services_running,
        m.ssh_gateway_status,
        m.gitea_ssh_status,
        m.database_status,
        m.redis_status,
    ]


# EOF
