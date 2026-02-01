#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Timestamp: "2025-11-29 07:00:00 (ywatanabe)"
# File: /home/ywatanabe/proj/scitex-cloud/apps/public_app/views/status/server.py
# ----------------------------------------
from __future__ import annotations
import os

__FILE__ = "./apps/public_app/views/status/server.py"
__DIR__ = os.path.dirname(__FILE__)
# ----------------------------------------

"""
Server Status View

Main view for displaying comprehensive server health status.
"""

from django.shortcuts import render

from .health_checks import (
    check_docker_containers,
    check_ssh_services,
    check_api_services,
    check_database,
    check_redis,
    check_disk,
)
from .package_versions import check_package_versions
from .compute_resources import (
    check_slurm_status,
    check_container_runtime_status,
)
from .system_metrics import check_system_resources
from .helpers import check_visitor_pool_status, check_registered_users_count


def server_status(request):
    """
    Server Status Page.

    Shows comprehensive server health status:
    - Docker containers status
    - SSH services (workspace gateway, Gitea)
    - Database connection
    - Redis connection
    - Disk usage
    - System resources (CPU, Memory, GPU)
    - SLURM and Apptainer/Singularity status
    - Visitor pool allocations
    """
    status_data = {
        "services": [],
        "ssh_services": [],
        "api_services": [],
        "database": {},
        "redis": {},
        "disk": {},
        "system": {},
    }

    # Check all services
    check_docker_containers(status_data)
    check_ssh_services(status_data)
    check_api_services(status_data)
    check_database(status_data)
    check_redis(status_data)
    check_disk(status_data)

    # Check compute resources
    check_slurm_status(status_data)
    check_container_runtime_status(status_data)

    # Check system resources
    check_system_resources(status_data)

    # Get visitor pool status
    check_visitor_pool_status(request, status_data)

    # Get registered users count
    check_registered_users_count(status_data)

    # Check package versions
    check_package_versions(status_data)

    context = {
        "status_data": status_data,
    }

    return render(request, "public_app/server_status.html", context)


# EOF
