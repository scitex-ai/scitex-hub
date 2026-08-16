#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Server metrics collection task."""

from __future__ import annotations

import logging
import subprocess

import psutil
from celery import shared_task
from django.contrib.sessions.models import Session
from django.core.cache import cache
from django.db import connection
from django.utils import timezone

from apps.infra.public_app.models import ServerMetrics, SiteHealthProbe

from .utils import check_port

logger = logging.getLogger(__name__)


def _get_cpu_metrics() -> tuple[float, int, int]:
    """Get CPU usage metrics."""
    cpu_percent = psutil.cpu_percent(interval=0.1)
    cpu_count = psutil.cpu_count(logical=False) or psutil.cpu_count()
    cpu_count_logical = psutil.cpu_count(logical=True)
    return cpu_percent, cpu_count, cpu_count_logical


def _get_service_status() -> tuple[bool, bool, bool, bool]:
    """Check service statuses: database, redis, ssh_gateway, gitea_ssh."""
    # Check SSH ports
    ssh_gateway_status = check_port(2200)
    gitea_ssh_status = check_port(2222)

    # Check database
    database_status = False
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        database_status = True
    except Exception:
        pass

    # Check Redis
    redis_status = False
    try:
        cache.set("health_check", "ok", 10)
        redis_status = cache.get("health_check") == "ok"
    except Exception:
        pass

    return database_status, redis_status, ssh_gateway_status, gitea_ssh_status


def _get_docker_count() -> int | None:
    """Get running Docker container count with timeout protection."""
    try:
        import docker

        # Use timeout to prevent blocking if Docker daemon is slow
        client = docker.from_env(timeout=5)
        containers = client.containers.list()
        return len(containers)
    except Exception:
        return None


def _get_visitor_pool_status() -> tuple[int | None, int | None]:
    """Get visitor pool allocation status."""
    try:
        from apps.infra.project_app.services.visitor_pool import VisitorPool

        pool_status = VisitorPool.get_pool_status()
        return pool_status["allocated"], pool_status["total"]
    except Exception as e:
        logger.debug(f"Could not get visitor pool status: {e}")
        return None, None


def _get_active_users_count() -> int | None:
    """Count active logged-in users from sessions."""
    try:
        active_sessions = Session.objects.filter(expire_date__gte=timezone.now())
        user_ids = set()
        for session in active_sessions:
            session_data = session.get_decoded()
            user_id = session_data.get("_auth_user_id")
            if user_id:
                user_ids.add(user_id)
        return len(user_ids)
    except Exception as e:
        logger.debug(f"Could not get active users count: {e}")
        return None


def _get_gpu_percent() -> float | None:
    """Get GPU utilization percentage (NVIDIA or AMD)."""
    try:
        # Try NVIDIA first
        result = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=utilization.gpu",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            timeout=2,
        )
        if result.returncode == 0 and result.stdout.strip():
            return float(result.stdout.strip().split("\n")[0])
    except Exception:
        pass

    try:
        # Try AMD rocm-smi
        import re

        result = subprocess.run(
            ["rocm-smi", "--showuse"], capture_output=True, text=True, timeout=2
        )
        if result.returncode == 0 and result.stdout:
            for line in result.stdout.split("\n"):
                if "GPU use" in line or "%" in line:
                    match = re.search(r"(\d+(?:\.\d+)?)\s*%", line)
                    if match:
                        return float(match.group(1))
    except Exception:
        pass

    return None


@shared_task(
    bind=True,
    name="apps.infra.public_app.tasks.collect_server_metrics",
    ignore_result=True,
    soft_time_limit=30,
    time_limit=60,
)
def collect_server_metrics(self):
    """
    Collect and store current server metrics.

    Runs periodically (every 5 seconds) to gather system, service, and user metrics.
    """
    try:
        # Gather all metrics
        cpu_percent, cpu_count, cpu_count_logical = _get_cpu_metrics()
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage("/")
        disk_io = psutil.disk_io_counters()
        net_io = psutil.net_io_counters()

        database_status, redis_status, ssh_gateway_status, gitea_ssh_status = (
            _get_service_status()
        )
        docker_services_running = _get_docker_count()
        visitor_pool_allocated, visitor_pool_total = _get_visitor_pool_status()
        active_users_count = _get_active_users_count()
        gpu_percent = _get_gpu_percent()

        # Create metrics record
        ServerMetrics.objects.create(
            timestamp=timezone.now(),
            cpu_percent=cpu_percent,
            cpu_cores=cpu_count,
            cpu_cores_logical=cpu_count_logical,
            memory_percent=memory.percent,
            memory_used_gb=round((memory.total - memory.available) / (1024**3), 2),
            memory_total_gb=round(memory.total / (1024**3), 2),
            memory_available_gb=round(memory.available / (1024**3), 2),
            disk_percent=disk.percent,
            disk_used_gb=round(disk.used / (1024**3), 2),
            disk_total_gb=round(disk.total / (1024**3), 2),
            disk_read_mb=round(disk_io.read_bytes / (1024**2), 2) if disk_io else 0,
            disk_write_mb=round(disk_io.write_bytes / (1024**2), 2) if disk_io else 0,
            net_sent_mb=round(net_io.bytes_sent / (1024**2), 2),
            net_recv_mb=round(net_io.bytes_recv / (1024**2), 2),
            docker_services_running=docker_services_running,
            ssh_gateway_status=ssh_gateway_status,
            gitea_ssh_status=gitea_ssh_status,
            database_status=database_status,
            redis_status=redis_status,
            visitor_pool_allocated=visitor_pool_allocated,
            visitor_pool_total=visitor_pool_total,
            active_users_count=active_users_count,
            gpu_percent=gpu_percent,
        )

        # Clean up old records (keep last 30 days)
        cutoff_date = timezone.now() - timezone.timedelta(days=30)
        deleted_count, _ = ServerMetrics.objects.filter(
            timestamp__lt=cutoff_date
        ).delete()
        if deleted_count > 0:
            logger.info(
                f"Deleted {deleted_count} old metric records (older than 30 days)"
            )

        # Same 30-day retention for site health probes (check_site_health)
        deleted_probes, _ = SiteHealthProbe.objects.filter(
            timestamp__lt=cutoff_date
        ).delete()
        if deleted_probes > 0:
            logger.info(
                f"Deleted {deleted_probes} old site health probe records (older than 30 days)"
            )

        logger.debug(
            f"Collected metrics: CPU={cpu_percent}%, Memory={memory.percent}%, Disk={disk.percent}%"
        )

    except Exception as e:
        logger.error(f"Failed to collect metrics: {e}", exc_info=True)
        raise


# EOF
