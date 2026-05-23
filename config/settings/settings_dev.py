#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Timestamp: "2025-11-10 15:46:56 (ywatanabe)"
# File: /home/ywatanabe/proj/scitex-hub/config/settings/settings_dev.py
# ----------------------------------------
from __future__ import annotations

import os

__FILE__ = "./config/settings/settings_dev.py"
__DIR__ = os.path.dirname(__FILE__)
# ----------------------------------------

"""
Development settings for SciTeX Hub project.
"""

import socket

from dotenv import load_dotenv

from .settings_shared import *


# ---------------------------------------
# Functions
# ---------------------------------------
def test_redis_connection():
    """Test if Redis is available"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex(("127.0.0.1", 6379))
        sock.close()
        return result == 0
    except:
        return False


# ---------------------------------------
# Env
# ---------------------------------------
try:
    load_dotenv(os.path.join(BASE_DIR, ".env"))
except Exception as e:
    print(e)

# ---------------------------------------
# Security (Development)
# ---------------------------------------
# Allow same-site iframes (needed for PDF viewer in writer app)
X_FRAME_OPTIONS = "SAMEORIGIN"

# ---------------------------------------
# Security
# ---------------------------------------
DEBUG = os.getenv("SCITEX_CLOUD_DJANGO_DEBUG", "True").lower() in [
    "true",
    "1",
    "yes",
]

# ---------------------------------------
# SciTeX Settings
# ---------------------------------------
# Use main branch for clean writer template (develop has dev artifacts)
_wtb = os.getenv("SCITEX_WRITER_TEMPLATE_BRANCH", "main")
SCITEX_WRITER_TEMPLATE_BRANCH = None if _wtb in ("", "null", "None") else _wtb
_wtt = os.getenv("SCITEX_WRITER_TEMPLATE_TAG", "")
SCITEX_WRITER_TEMPLATE_TAG = None if _wtt in ("", "null", "None") else _wtt
SECRET_KEY = os.getenv("SCITEX_CLOUD_DJANGO_SECRET_KEY")
ALLOWED_HOSTS = os.getenv(
    "SCITEX_CLOUD_ALLOWED_HOSTS",
    "localhost,127.0.0.1,0.0.0.0,[::1],testserver",
).split(",")

# Add WSL2 dynamic IP support (172.x.x.x range)
# This allows access from any WSL2 IP which can change on restart

try:
    wsl_ip = socket.gethostbyname(socket.gethostname())
    if wsl_ip not in ALLOWED_HOSTS:
        ALLOWED_HOSTS.append(wsl_ip)
except Exception:
    pass

# Also allow any 172.x.x.x IP for WSL2 flexibility in development
ALLOWED_HOSTS.append(".172.19.33.56")  # Specific WSL2 IP
ALLOWED_HOSTS.append("*")  # Allow all hosts in development


# Hot reload settings
INTERNAL_IPS = [
    "127.0.0.1",
    "172.20.0.1",  # Docker network gateway (for browser requests from host)
]

# WhiteNoise: auto-refresh static files in development
# This ensures changes to JS/CSS files are picked up immediately without restart
WHITENOISE_AUTOREFRESH = True
# Disable browser caching of static files in development to ensure fresh JS/CSS
WHITENOISE_MAX_AGE = 0

# Override STATICFILES_DIRS for dev - exclude .jsbuild since Vite handles TypeScript
# In dev mode, Vite serves TypeScript directly via dev server (port 5173)
# .jsbuild contains stale compiled JS that interferes with Vite HMR
STATICFILES_DIRS = [
    BASE_DIR / "static",
    # Note: .jsbuild is excluded in dev mode - Vite handles TypeScript transpilation
]

# Dual-Vite architecture ports
# Host Vite (port 5173): platform files — runs on host with native FS watching
# Container Vite (port 5174): developmentally-installed app files — runs in container on-demand
VITE_HOST_PORT = 5173
VITE_DEV_APP_PORT = 5174
# Set True to use pre-built Vite assets (staticfiles/vite/) instead of Vite dev server.
# Useful when Vite dev server can't run (resource constraints). Run `npm run build` first.
VITE_USE_BUILD = os.environ.get("SCITEX_CLOUD_VITE_USE_BUILD", "").lower() in (
    "1",
    "true",
    "yes",
)
# Set to your Windows LAN IP for iPhone dev testing (e.g. "192.168.0.67").
# Default "127.0.0.1" works for localhost-only dev.
# "auto" tries to detect the Windows host LAN IP via default gateway.
_vite_host_env = os.environ.get("SCITEX_CLOUD_VITE_HOST_IP", "127.0.0.1")
if _vite_host_env == "auto":
    try:
        import subprocess

        _gw = subprocess.check_output(
            ["ip", "route", "show", "default"], text=True
        ).split()[2]
        VITE_HOST_IP = _gw
    except Exception:
        VITE_HOST_IP = "127.0.0.1"
else:
    VITE_HOST_IP = _vite_host_env


# django-browser-reload configuration
# Note: Templates, CSS, and JS files are watched to trigger browser reload
# Visitor pool initialization is now optimized with fast-path check
def _get_extra_watch_files():
    """Dynamically get files to watch for browser reload."""
    import glob

    files = []
    # Watch templates for browser reload (visitor pool init is now fast)
    files.extend(
        glob.glob(str(BASE_DIR / "apps/*/templates/**/*.html"), recursive=True)
    )
    files.extend(glob.glob(str(BASE_DIR / "templates/**/*.html"), recursive=True))
    # Watch compiled CSS/JS from TypeScript
    files.extend(glob.glob(str(BASE_DIR / "static/**/*.css"), recursive=True))
    files.extend(glob.glob(str(BASE_DIR / "apps/*/static/**/*.css"), recursive=True))
    files.extend(glob.glob(str(BASE_DIR / "static/**/*.js"), recursive=True))
    files.extend(glob.glob(str(BASE_DIR / "apps/*/static/**/*.js"), recursive=True))
    return files


DJANGO_BROWSER_RELOAD_EXTRA_FILES = _get_extra_watch_files()

# ---------------------------------------
# Applications
# ---------------------------------------
DEVELOPMENT_APPS = [
    "daphne",  # Must be first for runserver integration
    "django_browser_reload",
    "django_extensions",
]

INSTALLED_APPS = (
    DEVELOPMENT_APPS + INSTALLED_APPS
)  # Daphne must be before django.contrib.staticfiles

# ASGI Application
ASGI_APPLICATION = "config.asgi.application"
MIDDLEWARE += [
    "django_browser_reload.middleware.BrowserReloadMiddleware",
    "config.middleware.DevNoCacheMiddleware",  # Prevent browser caching of JS modules + HTML
]


# ---------------------------------------
# Database - Fallback
# ---------------------------------------
# Use SQLite: export SCITEX_CLOUD_USE_SQLITE_DEV=1
if os.environ.get("SCITEX_CLOUD_USE_SQLITE_DEV"):
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "data" / "db" / "sqlite" / "scitex_hub_dev.db",
        }
    }
else:
    # PostgreSQL (default for development)
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.environ.get("SCITEX_CLOUD_DB_NAME_DEV", "scitex_hub_dev"),
            "USER": os.environ.get("SCITEX_CLOUD_DB_USER_DEV", "scitex_dev"),
            "PASSWORD": os.environ.get(
                "SCITEX_CLOUD_DB_PASSWORD_DEV", "scitex_dev_2025"
            ),
            "HOST": os.environ.get("SCITEX_CLOUD_DB_HOST_DEV", "localhost"),
            "PORT": os.environ.get("SCITEX_CLOUD_DB_PORT_DEV", "5432"),
            # ATOMIC_REQUESTS disabled: incompatible with ASGI (Daphne)
            # — same issue as production (see settings_prod.py).
            # Visitor middleware DB errors cascade to views.
            "ATOMIC_REQUESTS": False,
            "CONN_MAX_AGE": 600,  # Connection pooling (10 minutes)
            "OPTIONS": {
                "connect_timeout": 10,
            },
        }
    }

# ---------------------------------------
# Integration
# ---------------------------------------
# Gitea
# Use container URL for Django (http://gitea:3000) for inter-container communication
GITEA_URL = os.environ.get(
    "SCITEX_CLOUD_GITEA_URL_IN_CONTAINER_DEV", "http://gitea:3000"
)
GITEA_API_URL = f"{GITEA_URL}/api/v1"
GITEA_TOKEN = os.environ.get("SCITEX_CLOUD_GITEA_TOKEN_DEV", "")
GITEA_INTEGRATION_ENABLED = True  # Core feature, always enabled

# Gitea Clone URLs (for user-facing clone button)
SCITEX_CLOUD_GITEA_URL = os.environ.get(
    "SCITEX_CLOUD_GITEA_URL_DEV", "http://127.0.0.1:3000"
)
SCITEX_CLOUD_GIT_DOMAIN = os.environ.get("SCITEX_CLOUD_GIT_DOMAIN", "127.0.0.1")
SCITEX_CLOUD_GITEA_SSH_PORT = require_env("SCITEX_CLOUD_GITEA_SSH_PORT_DEV")

# Development Cache Configuration - fallback to dummy cache if Redis not available
# Override cache configuration for development if Redis is not available
if not test_redis_connection():
    print("⚠️  Redis not available in development, using local memory cache")
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "scitex-hub-dev",
            "TIMEOUT": 3600,
            "OPTIONS": {"MAX_ENTRIES": 1000},
        }
    }
    # Use database sessions if Redis is not available
    SESSION_ENGINE = "django.contrib.sessions.backends.db"

# ---------------------------------------
# Logging
# ---------------------------------------
LOGGING.update(
    {
        "handlers": {
            # Keep existing handlers from base settings
            **LOGGING.get("handlers", {}),
            # Add development-specific handlers
            "file_app": {
                "level": "DEBUG",
                "class": "logging.handlers.RotatingFileHandler",
                "filename": LOG_DIR / "app.log",
                "maxBytes": 1024 * 1024 * 5,  # 5 MB
                "backupCount": 5,
                "formatter": "standard",
            },
            "file_django": {
                "level": "INFO",
                "class": "logging.handlers.RotatingFileHandler",
                "filename": LOG_DIR / "django.log",
                "maxBytes": 1024 * 1024 * 5,  # 5 MB
                "backupCount": 5,
                "formatter": "standard",
            },
            "file_requests": {
                "level": "DEBUG",
                "class": "logging.handlers.RotatingFileHandler",
                "filename": LOG_DIR / "requests.log",
                "maxBytes": 1024 * 1024 * 5,  # 5 MB
                "backupCount": 5,
                "formatter": "standard",
            },
            "console_debug": {
                "level": "DEBUG",
                "class": "logging.StreamHandler",
                "formatter": "standard",
            },
        },
        "loggers": {
            # Update existing loggers from base settings
            **LOGGING.get("loggers", {}),
            # Add development-specific loggers
            "django": {
                "handlers": ["console", "file_django"],
                "level": "INFO",
                "propagate": True,
            },
            "django.request": {
                "handlers": ["file_requests"],
                "level": "ERROR",  # Only log errors, not 404s for __reload__
                "propagate": True,
            },
            "django.server": {
                "handlers": ["file_django"],
                "level": "ERROR",  # Suppress __reload__ 404 warnings
                "propagate": False,
            },
            "django.db.backends": {
                "handlers": ["console_debug"],
                "level": (
                    "DEBUG" if os.environ.get("SCITEX_CLOUD_SQL_DEBUG") else "INFO"
                ),
                "propagate": False,
            },
            "scitex": {
                "handlers": ["console_debug", "file_app"],
                "level": "DEBUG",
                "propagate": True,
            },
        },
    }
)

# ---------------------------------------
# Celery Beat Schedule Override for Development
# ---------------------------------------
# Chart generation dispatches 48 child tasks; use 60s to avoid queue flooding
CELERY_BEAT_SCHEDULE["generate-status-charts"] = {
    "task": "apps.infra.public_app.tasks.generate_status_charts",
    "schedule": 60.0,
    "options": {
        "expires": 55.0,
    },
}

# Re-enable metrics collection in dev (runs as Celery task, not in Daphne)
CELERY_BEAT_SCHEDULE["collect-server-metrics"] = {
    "task": "apps.infra.public_app.tasks.collect_server_metrics",
    "schedule": 10.0,
    "options": {
        "expires": 9.0,
    },
}

# ---------------------------------------
# Test User Credentials for API Docs Examples
# ---------------------------------------
# Used to populate API docs code examples in Private mode (dev only)
TEST_USER_PASSWORD = os.environ.get("SCITEX_CLOUD_TEST_USER_PASSWORD", "Password123!")

# ---------------------------------------
# Dev App Preview
# ---------------------------------------
# Add local app directories here to preview them without publishing.
# Each entry is a filesystem path to a directory containing manifest.json.
# Example: DEV_APPS = ["/home/user/my_app"]
DEV_APPS = []

# EOF
