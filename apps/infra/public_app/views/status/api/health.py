#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Health check and status API endpoints."""

from __future__ import annotations

import logging

import requests
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
from ..visitor_pool_health import check_visitor_pool

logger = logging.getLogger("scitex")

# Packages to report in version API
ECOSYSTEM_PACKAGES = [
    "scitex",
    "figrecipe",
    "crossref-local",
    "openalex-local",
    "scitex-writer",
    "socialia",
]


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
        # The anonymous-visitor product path. Every other check above was green
        # for ~1h35m on 2026-08-16 while all 16 visitor slots sat quarantined
        # and every visitor silently got the shared readonly account. Read-only:
        # it counts slots, it never reconciles them.
        check_visitor_pool(status_data)

        # Vite dev server check (DEBUG only)
        from django.conf import settings

        if settings.DEBUG:
            _check_vite_dev_server(status_data)

        # Determine overall health
        overall_status, color = _determine_overall_health(status_data)

        # Build issues list from non-healthy services
        issues = _build_issues_list(status_data)

        # Build response
        return JsonResponse(
            {
                "status": overall_status,
                "color": color,
                "timestamp": timezone.now().isoformat(),
                "issues": issues,
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

    # Visitor pool. `unhealthy` (ready == 0) must be an ERROR, not a warning:
    # `issues[]` renders only in the staff-only notification bell, so the
    # status COLOUR is the sole signal an anonymous visitor can see, and only
    # "error" moves it off green. Downgrading a total outage of the visitor
    # product path to "warning" would reproduce the 2026-08-16 incident for
    # every non-staff viewer.
    visitor_pool = status_data.get("visitor_pool", {})
    if visitor_pool.get("health_class") == "unhealthy":
        has_errors = True
    elif visitor_pool.get("health_class") == "warning":
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
        "visitor_pool": status_data.get("visitor_pool", {}).get(
            "health_class", "unknown"
        ),
        # `ready`, never `free` — see visitor_pool_health.classify_visitor_pool.
        "visitor_pool_ready": status_data.get("visitor_pool", {}).get("ready"),
        "visitor_pool_total": status_data.get("visitor_pool", {}).get("total"),
        "visitor_pool_quarantined": status_data.get("visitor_pool", {}).get(
            "quarantined"
        ),
    }


def _check_vite_dev_server(status_data: dict) -> None:
    """Check if Vite dev server is responding (DEBUG only)."""
    try:
        resp = requests.get("http://127.0.0.1:5173/@vite/client", timeout=2)
        is_healthy = resp.status_code == 200
    except Exception:
        is_healthy = False

    status_data["vite"] = {
        "is_running": is_healthy,
        "health_class": "healthy" if is_healthy else "warning",
    }


def _build_issues_list(status_data: dict) -> list[dict]:
    """Extract non-healthy services into a flat issues list."""
    issues = []

    # Database
    db = status_data.get("database", {})
    if db.get("health_class") not in ("healthy", None):
        issues.append(
            {
                "service": "Database",
                "level": "error",
                "message": db.get("error", "Connection failed"),
            }
        )

    # Redis
    redis = status_data.get("redis", {})
    if redis.get("health_class") not in ("healthy", None):
        issues.append(
            {
                "service": "Redis",
                "level": "error",
                "message": redis.get("error", "Connection failed"),
            }
        )

    # SLURM
    slurm = status_data.get("slurm", {})
    if slurm.get("health_class") == "unhealthy":
        issues.append(
            {
                "service": "Compute",
                "level": "error",
                "message": slurm.get("error", "SLURM unavailable"),
            }
        )
    elif slurm.get("health_class") == "warning":
        issues.append(
            {
                "service": "Compute",
                "level": "warning",
                "message": slurm.get("details", "Degraded"),
            }
        )

    # Apptainer
    apptainer = status_data.get("apptainer", {})
    if apptainer.get("health_class") in ("unhealthy", "warning"):
        issues.append(
            {
                "service": "Container Runtime",
                "level": "warning",
                "message": apptainer.get("error", "Not available"),
            }
        )

    # Vite (DEBUG only)
    vite = status_data.get("vite", {})
    if vite and vite.get("health_class") != "healthy":
        issues.append(
            {
                "service": "Vite Dev Server",
                "level": "warning",
                "message": "Not responding — JS/CSS may be broken",
            }
        )

    # SSH services
    for ssh in status_data.get("ssh_services", []):
        if ssh.get("health_class") in ("unhealthy", "down"):
            issues.append(
                {
                    "service": ssh.get("name", "SSH"),
                    "level": "warning",
                    "message": ssh.get("error", "Not responding"),
                }
            )

    # API services
    for api in status_data.get("api_services", []):
        if api.get("health_class") in ("unhealthy", "down"):
            issues.append(
                {
                    "service": api.get("name", "API"),
                    "level": "warning",
                    "message": api.get("error", "Not responding"),
                }
            )

    # User data permissions
    perms = status_data.get("user_data_permissions", {})
    if perms.get("health_class") == "unhealthy":
        issues.append(
            {
                "service": "User Data",
                "level": "warning",
                "message": perms.get("message", "Permission issues"),
            }
        )

    # Visitor pool. The message carries the REPAIR COMMAND, not just the
    # symptom — every other entry in this list is a bare symptom string, and
    # on 2026-08-16 the repair for this exact failure existed only inside a
    # card comment addressed to whoever deployed next (constitution §7).
    # "unknown" (the probe itself raised) is listed here but deliberately does
    # NOT flip the public dot in _determine_overall_health: an unmeasurable
    # pool is a fact staff must see, not a proven outage to alarm visitors with.
    visitor_pool = status_data.get("visitor_pool", {})
    if visitor_pool.get("health_class") in ("unhealthy", "warning", "unknown"):
        issues.append(
            {
                "service": "Visitor Pool",
                "level": visitor_pool.get("level", "warning"),
                "message": visitor_pool.get("message", "Visitor pool degraded"),
            }
        )

    return issues


def versions_api(request):
    """API endpoint returning installed package versions for ecosystem health dashboard.

    Returns JSON with installed versions of scitex ecosystem packages.
    Used by scitex dev dashboard to show Docker environment versions.
    """
    from importlib.metadata import PackageNotFoundError, version

    from django.conf import settings

    packages = {}
    for pkg in ECOSYSTEM_PACKAGES:
        try:
            packages[pkg] = {"installed": version(pkg), "status": "ok"}
        except PackageNotFoundError:
            packages[pkg] = {"installed": None, "status": "not_installed"}
        except Exception as e:
            packages[pkg] = {"installed": None, "status": "error", "error": str(e)}

    # Include scitex-hub version from settings
    cloud_version = getattr(settings, "SCITEX_HUB_VERSION", "unknown")
    packages["scitex-hub"] = {"installed": cloud_version, "status": "ok"}

    # Include environment info
    env = getattr(settings, "SCITEX_ENV", "unknown")

    return JsonResponse(
        {
            "packages": packages,
            "environment": env,
            "timestamp": timezone.now().isoformat(),
        }
    )


# EOF
