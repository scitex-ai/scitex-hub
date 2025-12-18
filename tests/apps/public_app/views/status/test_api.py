#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for apps/public_app/views/status/api.py"""

import pytest

# from apps.public_app.views.status.api import ...


class TestPlaceholder:
    """Placeholder test class - replace with actual tests."""

    def test_placeholder(self):
        """Placeholder test - implement actual tests."""
        pytest.skip("Not implemented yet")

if __name__ == "__main__":
    import os

    import pytest

    pytest.main([os.path.abspath(__file__)])

# --------------------------------------------------------------------------------
# Start of Source Code from: apps/public_app/views/status/api.py
# --------------------------------------------------------------------------------
# #!/usr/bin/env python3
# # -*- coding: utf-8 -*-
# # Timestamp: "2025-11-29 07:00:00 (ywatanabe)"
# # File: /home/ywatanabe/proj/scitex-cloud/apps/public_app/views/status/api.py
# # ----------------------------------------
# from __future__ import annotations
# import os
# 
# __FILE__ = "./apps/public_app/views/status/api.py"
# __DIR__ = os.path.dirname(__FILE__)
# # ----------------------------------------
# 
# """
# Server Status API Endpoints
# 
# JSON endpoints for real-time and historical server metrics.
# """
# 
# import csv
# import logging
# import time
# from datetime import timedelta
# 
# import psutil
# from django.contrib.sessions.models import Session
# from django.http import HttpResponse, JsonResponse
# from django.utils import timezone
# 
# from ...models import ServerMetrics
# from .helpers import get_gpu_utilization
# from .health_checks import check_docker_containers, check_database, check_redis, check_citation_graph
# 
# logger = logging.getLogger("scitex")
# 
# 
# def server_status_api(request):
#     """API endpoint for real-time server metrics (returns JSON)"""
#     try:
#         data = {
#             "timestamp": int(time.time() * 1000),  # milliseconds
#             "cpu_percent": psutil.cpu_percent(interval=0.1),
#             "memory_percent": psutil.virtual_memory().percent,
#             "disk_percent": psutil.disk_usage('/').percent,
#         }
# 
#         # GPU metrics
#         data["gpu_percent"] = get_gpu_utilization()
# 
#         # Network I/O rates
#         net_io = psutil.net_io_counters()
#         disk_io = psutil.disk_io_counters()
# 
#         data["net_sent_mb_total"] = round(net_io.bytes_sent / (1024**2), 2)
#         data["net_recv_mb_total"] = round(net_io.bytes_recv / (1024**2), 2)
#         data["disk_read_mb_total"] = round(disk_io.read_bytes / (1024**2), 2) if disk_io else 0
#         data["disk_write_mb_total"] = round(disk_io.write_bytes / (1024**2), 2) if disk_io else 0
# 
#         # Visitor pool status
#         try:
#             from apps.project_app.services.visitor_pool import VisitorPool
#             pool_status = VisitorPool.get_pool_status()
#             data["visitor_pool_allocated"] = pool_status['allocated']
#             data["visitor_pool_total"] = pool_status['total']
#         except Exception as e:
#             logger.debug(f"Could not get visitor pool status: {e}")
#             data["visitor_pool_allocated"] = None
#             data["visitor_pool_total"] = None
# 
#         # Active users count and total users
#         try:
#             from django.contrib.auth import get_user_model
#             User = get_user_model()
# 
#             # Count active users from sessions
#             active_sessions = Session.objects.filter(expire_date__gte=timezone.now())
#             user_ids = set()
#             for session in active_sessions:
#                 session_data = session.get_decoded()
#                 user_id = session_data.get('_auth_user_id')
#                 if user_id:
#                     user_ids.add(user_id)
#             data["active_users_count"] = len(user_ids)
# 
#             # Count total registered users (excluding visitor accounts)
#             data["total_users_count"] = User.objects.exclude(username__startswith="visitor-").count()
#         except Exception as e:
#             logger.debug(f"Could not get users count: {e}")
#             data["active_users_count"] = None
#             data["total_users_count"] = None
# 
#         return JsonResponse(data)
#     except Exception as e:
#         return JsonResponse({"error": str(e)}, status=500)
# 
# 
# def healthz(request):
#     """
#     Lightweight health check endpoint for frontend status indicator.
# 
#     Only checks critical services (DB + Redis) for fast response (<1s).
#     For full diagnostics, use /api/server-health/ or /server-status/ page.
#     """
#     try:
#         status_data = {}
# 
#         # Only check database and Redis (fast checks)
#         check_database(status_data)
#         check_redis(status_data)
# 
#         # Determine overall health
#         db_healthy = status_data.get('database', {}).get('health_class') == 'healthy'
#         redis_healthy = status_data.get('redis', {}).get('health_class') == 'healthy'
# 
#         if db_healthy and redis_healthy:
#             return JsonResponse({
#                 "status": "healthy",
#                 "color": "#22c55e",
#             })
#         else:
#             return JsonResponse({
#                 "status": "error",
#                 "color": "#ef4444",
#             })
#     except Exception as e:
#         logger.exception(f"Error in healthz: {e}")
#         return JsonResponse({
#             "status": "error",
#             "color": "#ef4444",
#         }, status=500)
# 
# 
# def server_health_status_api(request):
#     """
#     API endpoint for overall server health status (for header indicator).
# 
#     Returns:
#         - status: "healthy" | "warning" | "error" | "starting"
#         - color: hex color code for indicator
#         - services: dict of service statuses
#     """
#     try:
#         status_data = {"services": []}
# 
#         # Check critical services (with selective skipping for performance)
#         check_database(status_data)
#         check_redis(status_data)
# 
#         # Skip slow checks for the health endpoint (used by header indicator)
#         # Full checks available on /server-status/ page
#         # check_docker_containers(status_data)  # Slow Docker API calls
#         # check_slurm_status(status_data)  # Can be slow
#         # check_container_runtime_status(status_data)  # Can be slow
#         # check_citation_graph(status_data)  # Already skipped internally
# 
#         # Determine overall health
#         has_errors = False
#         has_warnings = False
#         has_starting = False
# 
#         # Check database
#         if status_data.get('database', {}).get('health_class') in ['unhealthy', 'down']:
#             has_errors = True
# 
#         # Check redis
#         if status_data.get('redis', {}).get('health_class') in ['unhealthy', 'down']:
#             has_errors = True
# 
#         # Check SLURM
#         slurm = status_data.get('slurm', {})
#         if slurm.get('health_class') == 'unhealthy':
#             has_errors = True
#         elif slurm.get('health_class') == 'warning':
#             has_warnings = True
# 
#         # Check Apptainer
#         apptainer = status_data.get('apptainer', {})
#         if apptainer.get('health_class') == 'unhealthy':
#             has_errors = True
#         elif apptainer.get('health_class') == 'warning':
#             has_warnings = True
# 
#         # Check Docker containers
#         services = status_data.get('services', [])
#         for service in services:
#             if service.get('status') in ['starting', 'created']:
#                 has_starting = True
#             elif service.get('status') not in ['running', 'healthy']:
#                 has_errors = True
# 
#         # Determine final status and color
#         if has_errors:
#             overall_status = "error"
#             color = "#ef4444"  # Red
#         elif has_starting:
#             overall_status = "starting"
#             color = "#22c55e"  # Green (will flash)
#         elif has_warnings:
#             overall_status = "warning"
#             color = "#eab308"  # Yellow
#         else:
#             overall_status = "healthy"
#             color = "#22c55e"  # Green
# 
#         # Build container status dict for easy lookup
#         containers = {}
#         for service in services:
#             # Extract service name (e.g., "flower" from "scitex-cloud-nas-flower-1")
#             name = service.get('name', '').lower()
#             containers[name] = service.get('health_class', 'unknown')
# 
#         # Citation graph status (non-critical - don't affect overall health)
#         citation_graph = status_data.get('citation_graph', {})
# 
#         return JsonResponse({
#             "status": overall_status,
#             "color": color,
#             "services": {
#                 "database": status_data.get('database', {}).get('health_class', 'unknown'),
#                 "redis": status_data.get('redis', {}).get('health_class', 'unknown'),
#                 "slurm": status_data.get('slurm', {}).get('health_class', 'unknown'),
#                 "apptainer": status_data.get('apptainer', {}).get('health_class', 'unknown'),
#                 # Docker containers
#                 "flower": containers.get('flower', 'unknown'),
#                 "celery_worker": containers.get('celery_worker', 'unknown'),
#                 "celery_beat": containers.get('celery_beat', 'unknown'),
#                 "gitea": containers.get('gitea', 'unknown'),
#                 "nginx": containers.get('nginx', 'unknown'),
#                 "postgres": containers.get('postgres', 'unknown'),
#                 # Scholar services
#                 "citation_graph": citation_graph.get('health_class', 'unknown'),
#                 "citation_graph_mode": citation_graph.get('mode', 'unknown'),
#             }
#         })
#     except Exception as e:
#         logger.exception(f"Error in server_health_status_api: {e}")
#         return JsonResponse({
#             "status": "error",
#             "color": "#ef4444",
#             "error": str(e)
#         }, status=500)
# 
# 
# def server_metrics_history_api(request):
#     """API endpoint for historical server metrics (returns JSON)"""
#     try:
#         # Get query parameters
#         hours = int(request.GET.get('hours', 24))  # Default: last 24 hours
#         limit = int(request.GET.get('limit', 1000))  # Max records to return
# 
#         # Query metrics
#         start_time = timezone.now() - timedelta(hours=hours)
#         metrics = ServerMetrics.objects.filter(
#             timestamp__gte=start_time
#         ).order_by('timestamp')[:limit]
# 
#         # Format data
#         data = {
#             "count": metrics.count(),
#             "start_time": start_time.isoformat(),
#             "end_time": timezone.now().isoformat(),
#             "metrics": [
#                 {
#                     "timestamp": int(m.timestamp.timestamp() * 1000),
#                     "cpu_percent": m.cpu_percent,
#                     "memory_percent": m.memory_percent,
#                     "disk_percent": m.disk_percent,
#                     "memory_used_gb": m.memory_used_gb,
#                     "disk_used_gb": m.disk_used_gb,
#                     "net_sent_mb": m.net_sent_mb,
#                     "net_recv_mb": m.net_recv_mb,
#                     "disk_read_mb": m.disk_read_mb,
#                     "disk_write_mb": m.disk_write_mb,
#                     "visitor_pool_allocated": m.visitor_pool_allocated,
#                     "visitor_pool_total": m.visitor_pool_total,
#                     "active_users_count": m.active_users_count,
#                     "gpu_percent": m.gpu_percent if hasattr(m, 'gpu_percent') else None,
#                 }
#                 for m in metrics
#             ]
#         }
# 
#         return JsonResponse(data)
#     except Exception as e:
#         return JsonResponse({"error": str(e)}, status=500)
# 
# 
# def server_metrics_export_csv(request):
#     """Export server metrics as CSV file"""
#     try:
#         # Get query parameters
#         hours = int(request.GET.get('hours', 24))
#         start_time = timezone.now() - timedelta(hours=hours)
# 
#         # Query metrics
#         metrics = ServerMetrics.objects.filter(
#             timestamp__gte=start_time
#         ).order_by('timestamp')
# 
#         # Create CSV response
#         response = HttpResponse(content_type='text/csv')
#         response['Content-Disposition'] = f'attachment; filename="server_metrics_{timezone.now().strftime("%Y%m%d_%H%M%S")}.csv"'
# 
#         writer = csv.writer(response)
# 
#         # Write header
#         writer.writerow([
#             'Timestamp',
#             'CPU %',
#             'CPU Cores',
#             'CPU Cores Logical',
#             'Memory %',
#             'Memory Used (TB)',
#             'Memory Total (TB)',
#             'Memory Available (TB)',
#             'Disk %',
#             'Disk Used (TB)',
#             'Disk Total (TB)',
#             'Disk Read (MB)',
#             'Disk Write (MB)',
#             'Network Sent (MB)',
#             'Network Received (MB)',
#             'Docker Services',
#             'SSH Gateway',
#             'Gitea SSH',
#             'Database',
#             'Redis',
#         ])
# 
#         # Write data
#         for m in metrics:
#             writer.writerow([
#                 m.timestamp.isoformat(),
#                 m.cpu_percent,
#                 m.cpu_cores,
#                 m.cpu_cores_logical,
#                 m.memory_percent,
#                 round(m.memory_used_gb / 1024, 3) if m.memory_used_gb else None,
#                 round(m.memory_total_gb / 1024, 3) if m.memory_total_gb else None,
#                 round(m.memory_available_gb / 1024, 3) if m.memory_available_gb else None,
#                 m.disk_percent,
#                 round(m.disk_used_gb / 1024, 2) if m.disk_used_gb else None,
#                 round(m.disk_total_gb / 1024, 2) if m.disk_total_gb else None,
#                 m.disk_read_mb,
#                 m.disk_write_mb,
#                 m.net_sent_mb,
#                 m.net_recv_mb,
#                 m.docker_services_running,
#                 m.ssh_gateway_status,
#                 m.gitea_ssh_status,
#                 m.database_status,
#                 m.redis_status,
#             ])
# 
#         return response
#     except Exception as e:
#         return JsonResponse({"error": str(e)}, status=500)
# 
# 
# # EOF

# --------------------------------------------------------------------------------
# End of Source Code from: apps/public_app/views/status/api.py
# --------------------------------------------------------------------------------
