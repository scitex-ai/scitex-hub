#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Health check and status API endpoints."""

from __future__ import annotations

import logging

from django.http import JsonResponse
from django.utils import timezone

from ..compute_resources import check_container_runtime_status, check_slurm_status
from ..health_checks import (
    check_api_services,
    check_database,
    check_redis,
    check_ssh_services,
    check_user_data_permissions,
)

logger = logging.getLogger("scitex")


def healthz(request):
    """
    Lightweight health check endpoint for frontend status indicator.

    Only checks critical services (DB + Redis) for fast response (<1s).
    """
    try:
        status_data = {}
        check_database(status_data)
        check_redis(status_data)

        db_healthy = status_data.get("database", {}).get("health_class") == "healthy"
        redis_healthy = status_data.get("redis", {}).get("health_class") == "healthy"

        if db_healthy and redis_healthy:
            return JsonResponse({"status": "healthy", "color": "#22c55e"})
        else:
            return JsonResponse({"status": "error", "color": "#ef4444"})
    except Exception as e:
        logger.exception(f"Error in healthz: {e}")
        return JsonResponse({"status": "error", "color": "#ef4444"}, status=500)


def server_health_status_api(request):
    """API endpoint for overall server health status (for header indicator)."""
    try:
        status_data = {"services": [], "ssh_services": [], "api_services": []}

        # Check critical services
        check_database(status_data)
        check_redis(status_data)
        check_ssh_services(status_data)
        check_api_services(status_data)
        check_slurm_status(status_data)
        check_container_runtime_status(status_data)
        check_user_data_permissions(status_data)

        # Determine overall health
        overall_status, color = _determine_overall_health(status_data)

        # Build response
        return JsonResponse(
            {
                "status": overall_status,
                "color": color,
                "timestamp": timezone.now().isoformat(),
                "services": _build_services_dict(status_data),
            }
        )
    except Exception as e:
        logger.exception(f"Error in server_health_status_api: {e}")
        return JsonResponse(
            {"status": "error", "color": "#ef4444", "error": str(e)}, status=500
        )


def _determine_overall_health(status_data: dict) -> tuple[str, str]:
    """Determine overall health status and color from service statuses."""
    has_errors = False
    has_warnings = False
    has_starting = False

    # Check core services
    if status_data.get("database", {}).get("health_class") in ["unhealthy", "down"]:
        has_errors = True
    if status_data.get("redis", {}).get("health_class") in ["unhealthy", "down"]:
        has_errors = True

    # Check compute resources
    slurm = status_data.get("slurm", {})
    if slurm.get("health_class") == "unhealthy":
        has_errors = True
    elif slurm.get("health_class") == "warning":
        has_warnings = True

    apptainer = status_data.get("apptainer", {})
    if apptainer.get("health_class") == "unhealthy":
        has_errors = True
    elif apptainer.get("health_class") == "warning":
        has_warnings = True

    # Check Docker containers
    for service in status_data.get("services", []):
        if service.get("status") in ["starting", "created"]:
            has_starting = True
        elif service.get("status") not in ["running", "healthy"]:
            has_errors = True

    # Check SSH and API services (warnings only)
    for ssh in status_data.get("ssh_services", []):
        if ssh.get("health_class") in ["unhealthy", "down"]:
            has_warnings = True

    for api in status_data.get("api_services", []):
        if api.get("health_class") in ["unhealthy", "down"]:
            has_warnings = True

    # User data permissions
    if status_data.get("user_data_permissions", {}).get("health_class") == "unhealthy":
        has_warnings = True

    # Determine final status
    if has_errors:
        return "error", "#ef4444"
    elif has_warnings:
        return "warning", "#eab308"
    elif has_starting:
        return "starting", "#22c55e"
    else:
        return "healthy", "#22c55e"


def _build_services_dict(status_data: dict) -> dict:
    """Build services status dictionary from status_data."""
    # Container status
    containers = {}
    for service in status_data.get("services", []):
        name = service.get("name", "").lower()
        containers[name] = service.get("health_class", "unknown")

    # SSH services status
    ssh_services_status = {}
    for ssh in status_data.get("ssh_services", []):
        key = (
            ssh.get("name", "")
            .lower()
            .replace(" ", "_")
            .replace("(", "")
            .replace(")", "")
        )
        ssh_services_status[key] = ssh.get("health_class", "unknown")

    # API services status
    api_services_status = {}
    for api in status_data.get("api_services", []):
        key = api.get("name", "").lower().replace(" ", "_")
        api_services_status[key] = api.get("health_class", "unknown")

    citation_graph = status_data.get("citation_graph", {})
    user_data_perms = status_data.get("user_data_permissions", {})

    return {
        "database": status_data.get("database", {}).get("health_class", "unknown"),
        "redis": status_data.get("redis", {}).get("health_class", "unknown"),
        "slurm": status_data.get("slurm", {}).get("health_class", "unknown"),
        "apptainer": status_data.get("apptainer", {}).get("health_class", "unknown"),
        "flower": containers.get("flower", "unknown"),
        "celery_worker": containers.get("celery_worker", "unknown"),
        "celery_beat": containers.get("celery_beat", "unknown"),
        "gitea": containers.get("gitea", "unknown"),
        "nginx": containers.get("nginx", "unknown"),
        "postgres": containers.get("postgres", "unknown"),
        **ssh_services_status,
        **api_services_status,
        "citation_graph": citation_graph.get("health_class", "unknown"),
        "citation_graph_mode": citation_graph.get("mode", "unknown"),
        "user_data_permissions": user_data_perms.get("health_class", "unknown"),
    }


# EOF
