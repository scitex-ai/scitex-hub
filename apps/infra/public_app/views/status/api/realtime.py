#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Real-time server metrics API endpoints."""

from __future__ import annotations

import logging
import time

import psutil
from django.contrib.sessions.models import Session
from django.http import JsonResponse
from django.utils import timezone

from ..helpers import get_gpu_utilization

logger = logging.getLogger("scitex")


def server_status_api(request):
    """API endpoint for real-time server metrics (returns JSON)."""
    try:
        data = {
            "timestamp": int(time.time() * 1000),
            "cpu_percent": psutil.cpu_percent(interval=0.1),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_percent": psutil.disk_usage("/").percent,
        }

        # GPU metrics
        data["gpu_percent"] = get_gpu_utilization()

        # Network I/O rates
        net_io = psutil.net_io_counters()
        disk_io = psutil.disk_io_counters()

        data["net_sent_mb_total"] = round(net_io.bytes_sent / (1024**2), 2)
        data["net_recv_mb_total"] = round(net_io.bytes_recv / (1024**2), 2)
        data["disk_read_mb_total"] = (
            round(disk_io.read_bytes / (1024**2), 2) if disk_io else 0
        )
        data["disk_write_mb_total"] = (
            round(disk_io.write_bytes / (1024**2), 2) if disk_io else 0
        )

        # Visitor pool status
        try:
            from apps.infra.project_app.services.visitor_pool import VisitorPool

            pool_status = VisitorPool.get_pool_status()
            data["visitor_pool_allocated"] = pool_status["allocated"]
            data["visitor_pool_total"] = pool_status["total"]
        except Exception as e:
            logger.debug(f"Could not get visitor pool status: {e}")
            data["visitor_pool_allocated"] = None
            data["visitor_pool_total"] = None

        # Active users count and total users
        try:
            from django.contrib.auth import get_user_model

            User = get_user_model()

            active_sessions = Session.objects.filter(expire_date__gte=timezone.now())
            user_ids = set()
            for session in active_sessions:
                session_data = session.get_decoded()
                user_id = session_data.get("_auth_user_id")
                if user_id:
                    user_ids.add(user_id)
            data["active_users_count"] = len(user_ids)

            data["total_users_count"] = User.objects.exclude(
                username__startswith="visitor-"
            ).count()
        except Exception as e:
            logger.debug(f"Could not get users count: {e}")
            data["active_users_count"] = None
            data["total_users_count"] = None

        return JsonResponse(data)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


def visitor_resources_api(request):
    """API endpoint for visitor resource allocation (for product tour)."""
    from config.settings.quotas import SLURM_QUOTAS

    return JsonResponse(
        {
            "cpus": SLURM_QUOTAS.get("interactive_cpus", 2),
            "memory_gb": SLURM_QUOTAS.get("interactive_memory_gb", 4),
            "time_limit": SLURM_QUOTAS.get("interactive_time_limit", "04:00:00"),
            "session_duration": "1 hour",
        }
    )


# EOF
