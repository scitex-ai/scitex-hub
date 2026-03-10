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
Checks run in parallel via ThreadPoolExecutor for fast page loads.
"""

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

from django.shortcuts import render

from .compute_resources import check_container_runtime_status, check_slurm_status
from .gitea_orgs import check_gitea_orgs
from .health_checks import (
    check_api_services,
    check_database,
    check_disk,
    check_docker_containers,
    check_redis,
    check_ssh_services,
)
from .helpers import check_registered_users_count, check_visitor_pool_status
from .package_versions import check_package_versions
from .system_metrics import check_system_resources

logger = logging.getLogger(__name__)


def _run_check(fn, *args):
    """Run a single health check, catching exceptions."""
    try:
        fn(*args)
    except Exception as e:
        logger.warning("Health check %s failed: %s", fn.__name__, e)


def server_status(request):
    """
    Server Status Page.

    All health checks run in parallel via ThreadPoolExecutor to minimize
    page load time (max-single-timeout instead of sum-of-all-timeouts).
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

    # Checks that only need status_data (no request)
    simple_checks = [
        check_docker_containers,
        check_ssh_services,
        check_api_services,
        check_database,
        check_redis,
        check_disk,
        check_slurm_status,
        check_container_runtime_status,
        check_system_resources,
        check_registered_users_count,
        check_package_versions,
        check_gitea_orgs,
    ]

    with ThreadPoolExecutor(max_workers=len(simple_checks) + 1) as pool:
        futures = []
        for fn in simple_checks:
            futures.append(pool.submit(_run_check, fn, status_data))
        # visitor_pool needs request
        futures.append(
            pool.submit(_run_check, check_visitor_pool_status, request, status_data)
        )
        # Wait for all to complete (individual timeouts already in each check)
        for fut in as_completed(futures):
            fut.result()  # propagates _run_check's caught exceptions as None

    context = {
        "status_data": status_data,
    }

    return render(request, "public_app/server_status.html", context)


# EOF
