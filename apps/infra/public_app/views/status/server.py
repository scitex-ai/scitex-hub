#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Timestamp: "2025-11-29 07:00:00 (ywatanabe)"
# File: /home/ywatanabe/proj/scitex-hub/apps/public_app/views/status/server.py
# ----------------------------------------
from __future__ import annotations

import os

__FILE__ = "./apps/public_app/views/status/server.py"
__DIR__ = os.path.dirname(__FILE__)
# ----------------------------------------

"""
Server Status View

Main view for displaying comprehensive server health status.
Checks run in parallel via ThreadPoolExecutor, bounded by ONE hard
deadline for the whole pool: a single stuck check must never drag the
page's TTFB (measured in prod: crossref_local.info() at 17.59 s made
/server-status/ take 17-21 s). A check that misses the deadline is
rendered three-valued as UNKNOWN — never silently dropped, never
collapsed into healthy/unhealthy.
"""

import logging
from concurrent.futures import ThreadPoolExecutor, wait

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

# Hard deadline for the WHOLE check pool (seconds).
CHECK_DEADLINE_SECONDS = 8.0

# Single source of truth for the checks: name -> (status_data key,
# "list" | "dict", human-readable name). Order = submission order =
# stable merge order. The name is resolved from module globals at call
# time so a timed-out check can be marked UNKNOWN in the exact spot the
# template renders it.
_CHECK_PLACEMENTS = {
    "check_docker_containers": ("services", "list", "Docker Services"),
    "check_ssh_services": ("ssh_services", "list", "SSH Services"),
    "check_api_services": ("api_services", "list", "API Services"),
    "check_database": ("database", "dict", "PostgreSQL"),
    "check_redis": ("redis", "dict", "Redis Cache"),
    "check_disk": ("disk", "dict", "Disk Usage"),
    "check_slurm_status": ("slurm", "dict", "SLURM"),
    "check_container_runtime_status": ("apptainer", "dict", "Apptainer"),
    "check_system_resources": ("system", "dict", "System Resources"),
    "check_registered_users_count": ("registered_users", "dict", "Registered Users"),
    "check_package_versions": ("package_versions", "list", "Package Versions"),
    "check_gitea_orgs": ("gitea_orgs", "list", "Gitea Organisations"),
    "check_visitor_pool_status": ("visitor_pool", "dict", "Visitor Pool"),
}


def _new_status_skeleton():
    """Base keys every check may touch (mirrors the template's shape)."""
    return {
        "services": [],
        "ssh_services": [],
        "api_services": [],
        "database": {},
        "redis": {},
        "disk": {},
        "system": {},
    }


def _run_check(fn, request=None):
    """Run one health check against a PRIVATE status dict and return it.

    Private-dict isolation is what makes the deadline safe: a straggler
    that finishes after the response was sent mutates only its own
    dict, never the one the template already rendered.
    """
    part = _new_status_skeleton()
    try:
        if request is not None:
            fn(request, part)
        else:
            fn(part)
    except Exception as e:
        logger.warning("Health check %s failed: %s", fn.__name__, e)
    return part


def _merge_status(main, part):
    """Merge one completed check's private dict into the page's dict."""
    for key, value in part.items():
        if isinstance(value, list):
            main.setdefault(key, []).extend(value)
        elif isinstance(value, dict):
            main.setdefault(key, {}).update(value)
        else:
            main[key] = value


def _mark_unknown(status_data, check_name, deadline_s):
    """Represent a deadline-missing check as three-valued UNKNOWN, loudly.

    Writes an UNKNOWN placeholder where the template renders the check's
    section AND a banner entry in status_data["unknown_checks"].
    """
    key, kind, display = _CHECK_PLACEMENTS[check_name]
    message = (
        f"{display} check ({check_name}) timed out after {deadline_s:g}s "
        "— the check is still running or stuck"
    )
    entry = {
        "name": display,
        "status": "unknown",
        "health_class": "unknown",
        "error": message,
    }
    if kind == "list":
        # Extra keys the package/org card templates render.
        entry.update(
            {
                "version": "unknown",
                "is_installed": False,
                "package": check_name,
                "description": message,
            }
        )
        status_data.setdefault(key, []).append(entry)
    else:
        status_data.setdefault(key, {}).update(entry)
    status_data["unknown_checks"].append(
        {"name": display, "check": check_name, "message": message}
    )
    logger.warning("Server-status: %s", message)


def _collect_status_data(request, checks, deadline_seconds):
    """Run ``checks`` in parallel under ONE hard deadline; return status_data.

    ``checks`` maps a _CHECK_PLACEMENTS name to its callable — injected
    so tests exercise the deadline machinery with hand-rolled fakes.
    """
    status_data = _new_status_skeleton()
    status_data["unknown_checks"] = []

    pool = ThreadPoolExecutor(max_workers=len(checks))
    try:
        future_names = {}
        for name, fn in checks.items():
            if name == "check_visitor_pool_status":
                future = pool.submit(_run_check, fn, request)
            else:
                future = pool.submit(_run_check, fn)
            future_names[future] = name
        done, _ = wait(future_names, timeout=deadline_seconds)
    finally:
        # wait=False: stragglers keep running detached from the response.
        pool.shutdown(wait=False)

    for future, name in future_names.items():
        if future in done:
            _merge_status(status_data, future.result())
        else:
            _mark_unknown(status_data, name, deadline_seconds)

    return status_data


def server_status(request, checks=None, deadline_seconds=None):
    """
    Server Status Page.

    All health checks run in parallel via ThreadPoolExecutor, sharing
    ONE hard deadline (CHECK_DEADLINE_SECONDS). Checks that miss it are
    rendered as UNKNOWN. Threads cannot be killed, so stragglers finish
    in the background; the response does not wait for them.

    ``checks`` / ``deadline_seconds`` are injectable for tests; URL
    routing calls this with the defaults.
    """
    if checks is None:
        checks = {name: globals()[name] for name in _CHECK_PLACEMENTS}
    if deadline_seconds is None:
        deadline_seconds = CHECK_DEADLINE_SECONDS

    status_data = _collect_status_data(request, checks, deadline_seconds)

    context = {
        "status_data": status_data,
    }

    return render(request, "public_app/server_status.html", context)


# EOF
