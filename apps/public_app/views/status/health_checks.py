#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Timestamp: "2025-11-29 07:00:00 (ywatanabe)"
# File: /home/ywatanabe/proj/scitex-cloud/apps/public_app/views/status/health_checks.py
# ----------------------------------------
from __future__ import annotations
import os

__FILE__ = "./apps/public_app/views/status/health_checks.py"
__DIR__ = os.path.dirname(__FILE__)
# ----------------------------------------

"""
Health Check Functions

Core health checking for Docker, SSH, Database, Redis, and Disk.
"""

import logging
import socket
from pathlib import Path

import psutil
from django.conf import settings
from django.core.cache import cache
from django.db import connection

logger = logging.getLogger("scitex")


def check_docker_containers(status_data):
    """Check Docker containers status."""
    try:
        import docker
        client = docker.from_env()
        scitex_env = os.environ.get("SCITEX_CLOUD_ENV", "dev")
        container_name_prefix = f"scitex-cloud-{scitex_env}"
        containers = client.containers.list(all=True, filters={"name": container_name_prefix})

        for container in containers:
            health_status = None
            try:
                health = container.attrs.get('State', {}).get('Health', {})
                health_status = health.get('Status') if health else None
            except Exception:
                pass

            is_running = container.status == "running"
            if health_status:
                display_status = f"{container.status} ({health_status})"
                health_class = health_status
            else:
                display_status = container.status
                health_class = "healthy" if is_running else "down"

            status_data["services"].append({
                "name": container.name.replace("scitex-cloud-dev-", "").replace("-1", ""),
                "status": container.status,
                "display_status": display_status,
                "health_status": health_status,
                "health_class": health_class,
                "is_running": is_running,
                "is_healthy": is_running and health_status in (None, "healthy"),
                "image": container.image.tags[0] if container.image.tags else "unknown",
            })
    except Exception as e:
        logger.warning(f"Could not check Docker containers: {e}")
        status_data["services"].append({
            "name": "Docker",
            "status": "unavailable",
            "display_status": "unavailable",
            "health_status": None,
            "health_class": "down",
            "is_running": False,
            "is_healthy": False,
            "error": str(e),
        })


def check_ssh_services(status_data):
    """Check SSH services (Workspace Gateway and Gitea)."""
    ssh_check_host = '127.0.0.1'
    if Path('/.dockerenv').exists():
        ssh_check_host = 'host.docker.internal'

    # Workspace SSH Gateway (port 2200)
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex((ssh_check_host, 2200))
        sock.close()
        is_running = result == 0
        status_data["ssh_services"].append({
            "name": "Workspace SSH Gateway",
            "port": 2200,
            "is_running": is_running,
            "status": "running" if is_running else "down",
            "health_class": "healthy" if is_running else "down",
        })
    except Exception as e:
        status_data["ssh_services"].append({
            "name": "Workspace SSH Gateway",
            "port": 2200,
            "is_running": False,
            "status": "error",
            "health_class": "unhealthy",
            "error": str(e),
        })

    # Gitea SSH
    gitea_ssh_port = int(getattr(settings, 'SCITEX_CLOUD_GITEA_SSH_PORT', 2222))
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex((ssh_check_host, gitea_ssh_port))
        sock.close()
        is_running = result == 0
        status_data["ssh_services"].append({
            "name": "Gitea SSH (Git operations)",
            "port": gitea_ssh_port,
            "is_running": is_running,
            "status": "running" if is_running else "down",
            "health_class": "healthy" if is_running else "down",
        })
    except Exception as e:
        status_data["ssh_services"].append({
            "name": "Gitea SSH",
            "port": gitea_ssh_port,
            "is_running": False,
            "status": "error",
            "health_class": "unhealthy",
            "error": str(e),
        })


def check_database(status_data):
    """Check database connection."""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            status_data["database"] = {
                "is_running": True,
                "status": "connected",
                "health_class": "healthy",
                "backend": connection.settings_dict['ENGINE'].split('.')[-1],
                "name": connection.settings_dict['NAME'],
            }
    except Exception as e:
        status_data["database"] = {
            "is_running": False,
            "status": "error",
            "health_class": "unhealthy",
            "error": str(e),
        }


def check_redis(status_data):
    """Check Redis connection."""
    try:
        cache.set('health_check', 'ok', 10)
        test_value = cache.get('health_check')
        is_connected = test_value == 'ok'
        status_data["redis"] = {
            "is_running": is_connected,
            "status": "connected" if is_connected else "error",
            "health_class": "healthy" if is_connected else "unhealthy",
        }
    except Exception as e:
        status_data["redis"] = {
            "is_running": False,
            "status": "error",
            "health_class": "unhealthy",
            "error": str(e),
        }


def check_disk(status_data):
    """Check disk usage."""
    try:
        disk = psutil.disk_usage('/')
        status_data["disk"] = {
            "total_tb": round(disk.total / (1024**4), 2),
            "used_tb": round(disk.used / (1024**4), 2),
            "free_tb": round(disk.free / (1024**4), 2),
            "percent_used": disk.percent,
            "is_healthy": disk.percent < 90,
        }
    except Exception as e:
        status_data["disk"] = {
            "is_healthy": False,
            "error": str(e),
        }


def check_citation_graph(status_data):
    """
    Check Citation Graph service availability.

    Reports mode (local/proxy) and health status.
    """
    try:
        from apps.scholar_app.services.citation_graph import get_citation_graph_service
        service = get_citation_graph_service()
        health = service.health_check()

        # Determine mode and health
        mode = health.get('mode', 'local')
        is_healthy = health.get('status') == 'healthy'
        proxy_target = health.get('proxy_target', None)

        status_data["citation_graph"] = {
            "is_running": is_healthy,
            "status": health.get('status', 'unknown'),
            "health_class": "healthy" if is_healthy else "unhealthy",
            "mode": mode,
            "proxy_target": proxy_target,
            "database": health.get('database', 'unknown'),
        }
    except Exception as e:
        logger.warning(f"Could not check citation graph service: {e}")
        status_data["citation_graph"] = {
            "is_running": False,
            "status": "unavailable",
            "health_class": "unhealthy",
            "mode": "unknown",
            "error": str(e),
        }


# EOF
