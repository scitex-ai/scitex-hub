#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for apps/public_app/tasks.py"""

import pytest

# from apps.infra.public_app.tasks import ...


class TestPlaceholder:
    """Placeholder test class - replace with actual tests."""

    def test_placeholder_pending_implementation(self):
        """Placeholder test - implement actual tests."""
        # Arrange
        # Act
        # Assert
        pytest.skip("Not implemented yet")


if __name__ == "__main__":
    import os

    import pytest

    pytest.main([os.path.abspath(__file__)])

# --------------------------------------------------------------------------------
# Start of Source Code from: apps/public_app/tasks.py
# --------------------------------------------------------------------------------
# #!/usr/bin/env python3
# # -*- coding: utf-8 -*-
# # Timestamp: "2025-11-26 (ywatanabe)"
# # File: apps/public_app/tasks.py
#
# """
# Celery tasks for Public App.
#
# Provides server metrics collection and maintenance tasks.
# """
#
# import logging
# import socket
# import subprocess
# from typing import Optional
#
# import psutil
# from celery import shared_task, group
# from django.contrib.sessions.models import Session
# from django.core.cache import cache
# from django.db import connection
# from django.utils import timezone
#
# from apps.infra.public_app.models import ServerMetrics
#
# logger = logging.getLogger(__name__)
#
#
# @shared_task(
#     bind=True,
#     name="apps.infra.public_app.tasks.collect_server_metrics",
#     ignore_result=True,
#     soft_time_limit=30,
#     time_limit=60,
# )
# def collect_server_metrics(self):
#     """
#     Collect and store current server metrics.
#
#     Runs periodically (every 5 seconds) to gather:
#     - CPU, Memory, Disk usage
#     - Network and Disk I/O
#     - Docker service status
#     - SSH gateway status
#     - Database and Redis status
#     - Visitor pool status
#     - Active users count
#     - GPU metrics (if available)
#     """
#     try:
#         # Get CPU info
#         cpu_percent = psutil.cpu_percent(interval=0.1)
#         cpu_count = psutil.cpu_count(logical=False) or psutil.cpu_count()
#         cpu_count_logical = psutil.cpu_count(logical=True)
#
#         # Get memory info
#         memory = psutil.virtual_memory()
#         memory_used_gb = round((memory.total - memory.available) / (1024**3), 2)
#
#         # Get disk info
#         disk = psutil.disk_usage("/")
#         disk_io = psutil.disk_io_counters()
#
#         # Get network info
#         net_io = psutil.net_io_counters()
#
#         # Check service statuses
#         ssh_gateway_status = _check_port(2200)
#         gitea_ssh_status = _check_port(2222)
#
#         # Check database
#         database_status = False
#         try:
#             with connection.cursor() as cursor:
#                 cursor.execute("SELECT 1")
#             database_status = True
#         except:
#             pass
#
#         # Check Redis
#         redis_status = False
#         try:
#             cache.set("health_check", "ok", 10)
#             redis_status = cache.get("health_check") == "ok"
#         except:
#             pass
#
#         # Check Docker services
#         docker_services_running = None
#         try:
#             import docker
#
#             client = docker.from_env()
#             containers = client.containers.list()
#             docker_services_running = len(containers)
#         except:
#             pass
#
#         # Get visitor pool status
#         visitor_pool_allocated = None
#         visitor_pool_total = None
#         try:
#             from apps.infra.project_app.services.visitor_pool import VisitorPool
#
#             pool_status = VisitorPool.get_pool_status()
#             visitor_pool_allocated = pool_status["allocated"]
#             visitor_pool_total = pool_status["total"]
#         except Exception as e:
#             logger.debug(f"Could not get visitor pool status: {e}")
#
#         # Count active logged-in users
#         active_users_count = None
#         try:
#             active_sessions = Session.objects.filter(expire_date__gte=timezone.now())
#             user_ids = set()
#             for session in active_sessions:
#                 session_data = session.get_decoded()
#                 user_id = session_data.get("_auth_user_id")
#                 if user_id:
#                     user_ids.add(user_id)
#             active_users_count = len(user_ids)
#         except Exception as e:
#             logger.debug(f"Could not get active users count: {e}")
#
#         # Get GPU metrics
#         gpu_percent = None
#         try:
#             # Try NVIDIA first
#             try:
#                 result = subprocess.run(
#                     [
#                         "nvidia-smi",
#                         "--query-gpu=utilization.gpu",
#                         "--format=csv,noheader,nounits",
#                     ],
#                     capture_output=True,
#                     text=True,
#                     timeout=2,
#                 )
#                 if result.returncode == 0 and result.stdout.strip():
#                     gpu_percent = float(result.stdout.strip().split("\n")[0])
#             except:
#                 pass
#
#             # Try AMD rocm-smi if NVIDIA didn't work
#             if gpu_percent is None:
#                 try:
#                     result = subprocess.run(
#                         ["rocm-smi", "--showuse"],
#                         capture_output=True,
#                         text=True,
#                         timeout=2,
#                     )
#                     if result.returncode == 0 and result.stdout:
#                         import re
#
#                         for line in result.stdout.split("\n"):
#                             if "GPU use" in line or "%" in line:
#                                 match = re.search(r"(\d+(?:\.\d+)?)\s*%", line)
#                                 if match:
#                                     gpu_percent = float(match.group(1))
#                                     break
#                 except:
#                     pass
#         except:
#             pass
#
#         # Create metrics record
#         ServerMetrics.objects.create(
#             timestamp=timezone.now(),
#             cpu_percent=cpu_percent,
#             cpu_cores=cpu_count,
#             cpu_cores_logical=cpu_count_logical,
#             memory_percent=memory.percent,
#             memory_used_gb=memory_used_gb,
#             memory_total_gb=round(memory.total / (1024**3), 2),
#             memory_available_gb=round(memory.available / (1024**3), 2),
#             disk_percent=disk.percent,
#             disk_used_gb=round(disk.used / (1024**3), 2),
#             disk_total_gb=round(disk.total / (1024**3), 2),
#             disk_read_mb=round(disk_io.read_bytes / (1024**2), 2) if disk_io else 0,
#             disk_write_mb=round(disk_io.write_bytes / (1024**2), 2) if disk_io else 0,
#             net_sent_mb=round(net_io.bytes_sent / (1024**2), 2),
#             net_recv_mb=round(net_io.bytes_recv / (1024**2), 2),
#             docker_services_running=docker_services_running,
#             ssh_gateway_status=ssh_gateway_status,
#             gitea_ssh_status=gitea_ssh_status,
#             database_status=database_status,
#             redis_status=redis_status,
#             visitor_pool_allocated=visitor_pool_allocated,
#             visitor_pool_total=visitor_pool_total,
#             active_users_count=active_users_count,
#             gpu_percent=gpu_percent,
#         )
#
#         # Clean up old records (keep last 30 days)
#         cutoff_date = timezone.now() - timezone.timedelta(days=30)
#         deleted_count, _ = ServerMetrics.objects.filter(
#             timestamp__lt=cutoff_date
#         ).delete()
#         if deleted_count > 0:
#             logger.info(
#                 f"Deleted {deleted_count} old metric records (older than 30 days)"
#             )
#
#         logger.debug(
#             f"Collected metrics: CPU={cpu_percent}%, Memory={memory.percent}%, Disk={disk.percent}%"
#         )
#
#     except Exception as e:
#         logger.error(f"Failed to collect metrics: {e}", exc_info=True)
#         # Re-raise to trigger Celery's retry mechanism
#         raise
#
#
# @shared_task(
#     bind=True,
#     name="apps.infra.public_app.tasks.cleanup_expired_visitor_allocations",
#     ignore_result=True,
#     soft_time_limit=30,
#     time_limit=60,
# )
# def cleanup_expired_visitor_allocations(self):
#     """
#     Clean up expired visitor slot allocations.
#
#     Runs periodically (every 5 minutes) to free up visitor slots whose
#     sessions have expired. This ensures slots are available for new visitors
#     even if the user didn't explicitly log out or their session wasn't cleaned up.
#
#     Returns:
#         int: Number of slots freed
#     """
#     try:
#         from apps.infra.project_app.services.visitor_pool import VisitorPool
#
#         freed_count = VisitorPool.cleanup_expired_allocations()
#
#         if freed_count > 0:
#             logger.info(f"[VisitorPool] Cleaned up {freed_count} expired visitor allocations")
#         else:
#             logger.debug("[VisitorPool] No expired allocations to clean up")
#
#         return freed_count
#
#     except Exception as e:
#         logger.error(f"[VisitorPool] Failed to clean up expired allocations: {e}", exc_info=True)
#         # Re-raise to trigger Celery's retry mechanism
#         raise
#
#
# def _check_port(port: int, host: str = "127.0.0.1", timeout: int = 1) -> bool:
#     """Check if a port is open/accessible."""
#     try:
#         sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
#         sock.settimeout(timeout)
#         result = sock.connect_ex((host, port))
#         sock.close()
#         return result == 0
#     except:
#         return False
#
#
# @shared_task(
#     bind=True,
#     name="apps.infra.public_app.tasks.generate_single_status_chart",
#     ignore_result=True,
#     soft_time_limit=30,
#     time_limit=45,
# )
# def generate_single_status_chart(self, metric_type: str, minutes: int, theme: str):
#     """
#     Generate a single server status chart.
#
#     This task is called in parallel by generate_status_charts_parallel.
#     """
#     try:
#         from apps.infra.public_app.views.status.chart_generator import generate_single_chart
#
#         success = generate_single_chart(metric_type, minutes, theme)
#         if success:
#             logger.debug(f"[Charts] Generated: {metric_type}_{minutes}_{theme}")
#         return success
#
#     except Exception as e:
#         logger.error(f"[Charts] Failed: {metric_type}_{minutes}_{theme}: {e}")
#         return False
#
#
# @shared_task(
#     bind=True,
#     name="apps.infra.public_app.tasks.generate_status_charts",
#     ignore_result=True,
#     soft_time_limit=120,
#     time_limit=180,
# )
# def generate_status_charts(self):
#     """
#     Pre-generate all server status charts in parallel.
#
#     Dispatches 48 parallel tasks (8 metrics × 3 time ranges × 2 themes)
#     to generate all chart combinations concurrently using Celery group.
#
#     Charts are stored in /tmp/scitex_charts/ and served instantly on request.
#     """
#     try:
#         from apps.infra.public_app.views.status.chart_generator import get_all_chart_combinations
#
#         combinations = get_all_chart_combinations()
#
#         # Create a group of tasks for parallel execution
#         chart_tasks = group(
#             generate_single_status_chart.s(metric, minutes, theme)
#             for metric, minutes, theme in combinations
#         )
#
#         # Execute all tasks in parallel
#         result = chart_tasks.apply_async()
#         logger.info(f"[Charts] Dispatched {len(combinations)} chart generation tasks in parallel")
#
#         return {"dispatched": len(combinations)}
#
#     except Exception as e:
#         logger.error(f"[Charts] Failed to dispatch chart tasks: {e}", exc_info=True)
#         raise
#
#
# # EOF

# --------------------------------------------------------------------------------
# End of Source Code from: apps/public_app/tasks.py
# --------------------------------------------------------------------------------
