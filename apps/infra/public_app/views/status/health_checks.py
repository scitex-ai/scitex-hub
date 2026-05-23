#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Timestamp: "2025-11-29 07:00:00 (ywatanabe)"
# File: /home/ywatanabe/proj/scitex-hub/apps/public_app/views/status/health_checks.py
# ----------------------------------------
from __future__ import annotations

import os

__FILE__ = "./apps/public_app/views/status/health_checks.py"
__DIR__ = os.path.dirname(__FILE__)
# ----------------------------------------

"""
Health Check Functions

Core health checking for Docker, SSH, Database, Redis, Disk, and API services.
"""

import logging
import os
import socket
from pathlib import Path

import requests
from django.conf import settings
from django.core.cache import cache
from django.db import connection

logger = logging.getLogger("scitex")


def check_docker_containers(status_data):
    """Check Docker containers status."""
    try:
        import docker

        client = docker.from_env()
        scitex_env = os.environ.get("SCITEX_HUB_ENV", "dev")
        container_name_prefix = f"scitex-hub-{scitex_env}"
        containers = client.containers.list(
            all=True, filters={"name": container_name_prefix}
        )

        for container in containers:
            health_status = None
            try:
                health = container.attrs.get("State", {}).get("Health", {})
                health_status = health.get("Status") if health else None
            except Exception:
                pass

            is_running = container.status == "running"
            if health_status:
                display_status = f"{container.status} ({health_status})"
                health_class = health_status
            else:
                display_status = container.status
                health_class = "healthy" if is_running else "down"

            status_data["services"].append(
                {
                    "name": container.name.replace("scitex-hub-dev-", "").replace(
                        "-1", ""
                    ),
                    "status": container.status,
                    "display_status": display_status,
                    "health_status": health_status,
                    "health_class": health_class,
                    "is_running": is_running,
                    "is_healthy": is_running and health_status in (None, "healthy"),
                    "image": (
                        container.image.tags[0] if container.image.tags else "unknown"
                    ),
                }
            )
    except Exception as e:
        logger.warning(f"Could not check Docker containers: {e}")
        status_data["services"].append(
            {
                "name": "Docker",
                "status": "unavailable",
                "display_status": "unavailable",
                "health_status": None,
                "health_class": "down",
                "is_running": False,
                "is_healthy": False,
                "error": str(e),
            }
        )


def _check_ssh_banner(host: str, port: int, timeout: float = 2.0) -> tuple[bool, str]:
    """
    Check SSH service by verifying SSH banner.

    Returns (is_functional, banner_or_error).
    """
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        if result != 0:
            sock.close()
            return False, "Connection refused"

        # Try to receive SSH banner (e.g., "SSH-2.0-OpenSSH_8.9")
        try:
            banner = sock.recv(256).decode("utf-8", errors="ignore").strip()
            sock.close()
            if banner.startswith("SSH-"):
                return True, banner
            else:
                return False, f"Invalid banner: {banner[:50]}"
        except socket.timeout:
            sock.close()
            return False, "Banner timeout"
    except Exception as e:
        return False, str(e)


def check_ssh_services(status_data):
    """Check SSH services (Workspace Gateway and Gitea) with banner verification."""
    # Workspace SSH Gateway runs in the same container (Django container)
    # So always check on localhost, regardless of Docker environment
    workspace_ssh_host = "127.0.0.1"

    # Gitea SSH runs in separate container, use Docker network hostname
    gitea_ssh_host = "gitea" if Path("/.dockerenv").exists() else "127.0.0.1"

    # Workspace SSH Gateway (port 2200) - via cloudflared at ssh.scitex.ai
    is_functional, banner_or_error = _check_ssh_banner(workspace_ssh_host, 2200)
    status_data["ssh_services"].append(
        {
            "name": "Workspace SSH Gateway",
            "port": 2200,
            "public_url": "ssh.scitex.ai",
            "is_running": is_functional,
            "status": "running" if is_functional else "down",
            "health_class": "healthy" if is_functional else "down",
            "banner": banner_or_error if is_functional else None,
            "error": None if is_functional else banner_or_error,
        }
    )

    # Gitea SSH - via cloudflared at gitea.scitex.ai
    # Inside Docker: use internal port 22 (gitea container's SSH)
    # Outside Docker: use external mapped port from settings (default 2222)
    gitea_ssh_port = (
        22
        if Path("/.dockerenv").exists()
        else int(getattr(settings, "SCITEX_HUB_GITEA_SSH_PORT", 2222))
    )
    is_functional, banner_or_error = _check_ssh_banner(gitea_ssh_host, gitea_ssh_port)
    status_data["ssh_services"].append(
        {
            "name": "Gitea SSH (Git operations)",
            "port": gitea_ssh_port,
            "public_url": "gitea.scitex.ai",
            "is_running": is_functional,
            "status": "running" if is_functional else "down",
            "health_class": "healthy" if is_functional else "down",
            "banner": banner_or_error if is_functional else None,
            "error": None if is_functional else banner_or_error,
        }
    )


def _check_local_db(name, package_name):
    """Check a local database service by delegating to the package's own info().

    Each package (crossref_local, openalex_local) handles mode detection
    (DB vs HTTP) and health checking internally.
    """
    import importlib

    result = {
        "name": name,
        "is_running": False,
        "status": "unavailable",
        "health_class": "unhealthy",
    }

    try:
        pkg = importlib.import_module(package_name)
    except ImportError as e:
        result["error"] = f"Package not installed: {e}"
        return result

    if not hasattr(pkg, "info"):
        result["error"] = "Package missing 'info' function"
        return result

    try:
        pkg_info = pkg.info()
        mode = pkg_info.get("mode", "unknown")
        status = pkg_info.get("status", "unknown")

        if status in ("ok", "healthy", "running"):
            api_url = pkg_info.get("api_url", "")
            result.update(
                {
                    "is_running": True,
                    "status": "healthy",
                    "health_class": "healthy",
                    "mode": mode,
                    "details": f"{mode} mode" + (f" ({api_url})" if api_url else ""),
                }
            )
        elif status == "unreachable":
            result.update(
                {
                    "status": "degraded",
                    "health_class": "warning",
                    "mode": mode,
                    "details": pkg_info.get("error", "Unreachable"),
                }
            )
        else:
            result.update(
                {
                    "status": "degraded",
                    "health_class": "warning",
                    "mode": mode,
                    "details": f"Status: {status}",
                }
            )
    except FileNotFoundError:
        result.update(
            {
                "status": "degraded",
                "health_class": "warning",
                "details": "Database not configured",
            }
        )
    except Exception as e:
        result.update(
            {
                "status": "degraded",
                "health_class": "warning",
                "details": str(e),
            }
        )

    return result


def check_api_services(status_data):
    """Check API services (CrossRef Local, OpenAlex Local, Gitea HTTP, SciTeX MCP)."""
    status_data["api_services"] = []

    # CrossRef Local - delegates to crossref_local.info()
    status_data["api_services"].append(
        _check_local_db("CrossRef Local", "crossref_local")
    )

    # OpenAlex Local - delegates to openalex_local.info()
    status_data["api_services"].append(
        _check_local_db("OpenAlex Local", "openalex_local")
    )

    # Gitea HTTP API - check /api/v1/version endpoint
    try:
        response = requests.get("http://gitea:3000/api/v1/version", timeout=5)
        is_healthy = response.status_code == 200
        data = response.json() if is_healthy else {}
        status_data["api_services"].append(
            {
                "name": "Gitea API",
                "url": "gitea:3000",
                "public_url": "https://git.scitex.ai",
                "is_running": is_healthy,
                "status": "healthy" if is_healthy else "error",
                "health_class": "healthy" if is_healthy else "unhealthy",
                "response_time_ms": int(response.elapsed.total_seconds() * 1000),
                "details": f"v{data.get('version', 'unknown')}" if data else "",
            }
        )
    except requests.exceptions.Timeout:
        status_data["api_services"].append(
            {
                "name": "Gitea API",
                "url": "gitea:3000",
                "public_url": "https://git.scitex.ai",
                "is_running": False,
                "status": "timeout",
                "health_class": "unhealthy",
                "error": "Request timed out",
            }
        )
    except Exception as e:
        status_data["api_services"].append(
            {
                "name": "Gitea API",
                "url": "gitea:3000",
                "public_url": "https://git.scitex.ai",
                "is_running": False,
                "status": "error",
                "health_class": "unhealthy",
                "error": str(e),
            }
        )

    # SciTeX MCP Server (in-process — verify tools are importable)
    try:
        from scitex.mcp_server import mcp as _mcp

        tm = getattr(_mcp, "_tool_manager", None)
        if tm is not None and hasattr(tm, "_tools"):
            tool_count = len(tm._tools)
        else:
            import asyncio

            tools = asyncio.run(_mcp.list_tools())
            tool_count = len(tools)
        status_data["api_services"].append(
            {
                "name": "SciTeX MCP Tools",
                "url": "in-process",
                "public_url": "/mcp (auth required)",
                "is_running": True,
                "status": "healthy",
                "health_class": "healthy",
                "details": f"{tool_count} tools loaded",
            }
        )
    except Exception as e:
        status_data["api_services"].append(
            {
                "name": "SciTeX MCP Tools",
                "url": "in-process",
                "public_url": "/mcp (auth required)",
                "is_running": False,
                "status": "error",
                "health_class": "unhealthy",
                "error": str(e),
            }
        )


def check_database(status_data):
    """Check database connection."""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            status_data["database"] = {
                "is_running": True,
                "status": "connected",
                "health_class": "healthy",
                "backend": connection.settings_dict["ENGINE"].split(".")[-1],
                "name": connection.settings_dict["NAME"],
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
        cache.set("health_check", "ok", 10)
        test_value = cache.get("health_check")
        is_connected = test_value == "ok"
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
        st = os.statvfs("/")
        total = st.f_blocks * st.f_frsize
        free = st.f_bavail * st.f_frsize
        used = total - free
        percent_used = round((used / total) * 100, 1) if total > 0 else 0
        status_data["disk"] = {
            "total_tb": round(total / (1024**4), 2),
            "used_tb": round(used / (1024**4), 2),
            "free_tb": round(free / (1024**4), 2),
            "percent_used": percent_used,
            "is_healthy": percent_used < 90,
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

    NOTE: Temporarily skipped for health endpoint to prevent timeout issues.
    Full check available on /server-status/ page.
    """
    # Skip citation graph check in health endpoint to prevent timeouts
    # The health endpoint needs to be fast (<3s) for Docker healthcheck
    # Full citation graph status is checked on the server-status page
    status_data["citation_graph"] = {
        "is_running": True,
        "status": "skipped",
        "health_class": "healthy",
        "mode": "not_checked",
        "note": "Check skipped for performance (see /server-status/ for details)",
    }


def check_user_data_permissions(status_data):
    """
    Check user data directory permissions.

    NAS bind mounts can cause permission issues where directories
    appear as d--------- (no permissions) inside the container despite
    having proper permissions on the host.

    Returns:
        dict with:
        - is_healthy: bool
        - status: "ok" | "warning" | "error"
        - health_class: "healthy" | "warning" | "unhealthy"
        - broken_dirs: list of directories with permission issues
        - message: human-readable status
    """
    user_data_path = Path("/app/data/users")
    broken_dirs = []

    try:
        if not user_data_path.exists():
            status_data["user_data_permissions"] = {
                "is_healthy": True,
                "status": "ok",
                "health_class": "healthy",
                "broken_dirs": [],
                "message": "User data directory not yet created",
            }
            return

        # Check for directories without read/execute permissions
        for user_dir in user_data_path.iterdir():
            if not user_dir.is_dir():
                continue

            # Check if directory is accessible
            try:
                # Try to list directory contents
                list(user_dir.iterdir())
            except PermissionError:
                broken_dirs.append(str(user_dir.name))

            # Also check subdirectories (proj directory)
            for subdir in user_dir.glob("*"):
                if subdir.is_dir():
                    try:
                        list(subdir.iterdir())
                    except PermissionError:
                        broken_dirs.append(f"{user_dir.name}/{subdir.name}")

        if broken_dirs:
            status_data["user_data_permissions"] = {
                "is_healthy": False,
                "status": "error",
                "health_class": "unhealthy",
                "broken_dirs": broken_dirs[:10],  # Limit to first 10
                "total_broken": len(broken_dirs),
                "message": f"Permission issues detected in {len(broken_dirs)} directories",
            }
        else:
            status_data["user_data_permissions"] = {
                "is_healthy": True,
                "status": "ok",
                "health_class": "healthy",
                "broken_dirs": [],
                "message": "All user directories accessible",
            }
    except Exception as e:
        logger.warning(f"Could not check user data permissions: {e}")
        status_data["user_data_permissions"] = {
            "is_healthy": False,
            "status": "error",
            "health_class": "unhealthy",
            "error": str(e),
            "message": f"Permission check failed: {e}",
        }


# EOF
