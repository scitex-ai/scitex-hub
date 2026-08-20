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

from config import branding

from ._logging_merge import merge_logging
from .settings_shared import *

# Environment identity -- drives the tab title marker "(dev)" and the GREEN
# favicon. Literal, not env-var derived: running settings_dev IS development.
SCITEX_ENV = branding.ENV_DEVELOPMENT


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
DEBUG = os.getenv("SCITEX_HUB_DJANGO_DEBUG", "True").lower() in [
    "true",
    "1",
    "yes",
]

# In dev and in the test suite ONE process is both the visitor-slot resetter and
# the web process, so the truthful owner to hand a recycled tree to is itself.
# This is a declaration about the dev deployment, not a fallback: the setting
# in settings_shared stays `scitex` for production, and an explicit
# SCITEX_HUB_APP_UNIX_OWNER still wins here. verify_app_can_write() keeps
# comparing real st_uid values, so the final gate can still fail in dev.
APP_UNIX_OWNER = os.getenv("SCITEX_HUB_APP_UNIX_OWNER") or f"{os.getuid()}:{os.getgid()}"

# ---------------------------------------
# SciTeX Settings
# ---------------------------------------
# Use main branch for clean writer template (develop has dev artifacts)
_wtb = os.getenv("SCITEX_WRITER_TEMPLATE_BRANCH", "main")
SCITEX_WRITER_TEMPLATE_BRANCH = None if _wtb in ("", "null", "None") else _wtb
_wtt = os.getenv("SCITEX_WRITER_TEMPLATE_TAG", "")
SCITEX_WRITER_TEMPLATE_TAG = None if _wtt in ("", "null", "None") else _wtt
# SECRET_KEY is deliberately NOT re-read here. settings_shared already resolves
# it through getenv_with_legacy_alias() -- which honors the deprecated
# SCITEX_CLOUD_DJANGO_SECRET_KEY name (ADR-0001) -- and raises if it is unset.
# A plain os.getenv() here would miss the alias and silently overwrite that
# value with None, so a dev env file using the legacy name yields an empty
# SECRET_KEY and Django refuses to boot.
ALLOWED_HOSTS = os.getenv(
    "SCITEX_HUB_ALLOWED_HOSTS",
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

# CSRF trusted origins for dev. Django's Origin-header CSRF check is a
# SEPARATE gate from ALLOWED_HOSTS (added Django 4.0) -- being permissive
# above does not cover it, so every POST form (login included) 403s with
# "CSRF verification failed ... Origin checking failed" as soon as dev is
# reached over any origin not listed here. Undiscovered until 2026-08-20:
# nobody had gotten this far in a tunnel-based dev session before (an
# earlier bug -- vite.py hardcoding http:// -- blocked ALL page JS first,
# see apps/infra/public_app/templatetags/vite.py history), so login was
# never actually attempted through compute-0N-net.scitex.ai until then.
# *.scitex.ai covers every host's Cloudflare tunnel domain (compute-01
# through compute-0N) without needing a per-host update.
CSRF_TRUSTED_ORIGINS = os.getenv(
    "SCITEX_HUB_CSRF_TRUSTED_ORIGINS",
    "http://localhost:8000,http://127.0.0.1:8000,https://*.scitex.ai",
).split(",")


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
VITE_USE_BUILD = os.environ.get("SCITEX_HUB_VITE_USE_BUILD", "").lower() in (
    "1",
    "true",
    "yes",
)
# Set to your Windows LAN IP for iPhone dev testing (e.g. "192.168.0.67").
# Default "127.0.0.1" works for localhost-only dev.
# "auto" tries to detect the Windows host LAN IP via default gateway.
_vite_host_env = os.environ.get("SCITEX_HUB_VITE_HOST_IP", "127.0.0.1")
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
# Use SQLite: export SCITEX_HUB_USE_SQLITE_DEV=1
if os.environ.get("SCITEX_HUB_USE_SQLITE_DEV"):
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
            "NAME": os.environ.get("SCITEX_HUB_DB_NAME_DEV", "scitex_hub_dev"),
            "USER": os.environ.get("SCITEX_HUB_DB_USER_DEV", "scitex_dev"),
            # DECLARED EXCEPTION, not an oversight. This is the compose-local
            # dev postgres, which every real deployment overrides via
            # SCITEX_HUB_DB_PASSWORD_DEV; prod uses settings_prod, which has no
            # literal fallback at all. Emptying it would break `docker compose
            # up` for anyone who has not set the variable, so it is declared
            # rather than removed. If the dev database is ever exposed beyond
            # the compose network this must become an empty default instead.
            "PASSWORD": os.environ.get(
                "SCITEX_HUB_DB_PASSWORD_DEV", "scitex_dev_2025"
            ),  # pragma: allowlist secret
            "HOST": os.environ.get("SCITEX_HUB_DB_HOST_DEV", "localhost"),
            "PORT": os.environ.get("SCITEX_HUB_DB_PORT_DEV", "5432"),
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
GITEA_URL = os.environ.get("SCITEX_HUB_GITEA_URL_IN_CONTAINER_DEV", "http://gitea:3000")
GITEA_API_URL = f"{GITEA_URL}/api/v1"
GITEA_TOKEN = os.environ.get("SCITEX_HUB_GITEA_TOKEN_DEV", "")
GITEA_INTEGRATION_ENABLED = True  # Core feature, always enabled

# Gitea Clone URLs (for user-facing clone button)
SCITEX_HUB_GITEA_URL = os.environ.get(
    "SCITEX_HUB_GITEA_URL_DEV", "http://127.0.0.1:3000"
)
SCITEX_HUB_GIT_DOMAIN = os.environ.get("SCITEX_HUB_GIT_DOMAIN", "127.0.0.1")
SCITEX_HUB_GITEA_SSH_PORT = require_env("SCITEX_HUB_GITEA_SSH_PORT_DEV")

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
# merge_logging, NOT LOGGING.update -- see the note in settings_prod.py and the
# measurement in config/settings/_logging_merge.py. This module happened to
# spread `**LOGGING.get("loggers", {})` and so kept the base's wiring, but the
# spread was a habit rather than a guarantee: the same literal in prod and
# staging did not have it, and nothing noticed for months.
LOGGING = merge_logging(
    LOGGING,
    {
        "handlers": {
            # Development-specific handlers. The base's handlers are kept by
            # the merge.
            "file_app": {
                "level": "DEBUG",
                "class": "logging.handlers.RotatingFileHandler",
                "filename": LOG_DIR / "app.log",
                "maxBytes": 1024 * 1024 * 5,  # 5 MB
                "backupCount": 5,
                "formatter": "standard",
            },
            # "file_django" used to be defined here as a byte-for-byte copy of
            # the base's "django_file" -- same file, same size, same backups --
            # so dev ran two RotatingFileHandlers over LOG_DIR/django.log and
            # left the base's handler attached to nothing. The base's entry is
            # simply reused instead.
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
            # Loggers redefined for development. Every logger NOT named here
            # keeps the base's handlers.
            "django": {
                "handlers": ["console", "django_file"],
                "level": "INFO",
                "propagate": True,
            },
            # mail_admins IS listed here on purpose, even though dev runs with
            # DEBUG=True and require_debug_false drops every record. The rail
            # must have exactly ONE gate deciding whether a developer machine
            # mails, and that gate is require_debug_false -- the same reasoning
            # settings_shared gives for defining ADMINS once instead of per
            # environment. Omitting the handler here would be a SECOND, silent
            # gate, and two gates where one is invisible is precisely how this
            # rail came to be dead in production without anyone noticing. It
            # also means a developer debugging with DEBUG=False sees the real
            # production behaviour rather than a quieter imitation of it.
            "django.request": {
                "handlers": ["file_requests", "mail_admins"],
                "level": "ERROR",  # Only log errors, not 404s for __reload__
                "propagate": True,
            },
            "django.server": {
                "handlers": ["django_file"],
                "level": "ERROR",  # Suppress __reload__ 404 warnings
                "propagate": False,
            },
            "django.db.backends": {
                "handlers": ["console_debug"],
                "level": (
                    "DEBUG" if os.environ.get("SCITEX_HUB_SQL_DEBUG") else "INFO"
                ),
                "propagate": False,
            },
            "scitex": {
                "handlers": ["console_debug", "file_app"],
                "level": "DEBUG",
                "propagate": True,
            },
        },
    },
)

# ---------------------------------------
# Celery Beat Schedule Override for Development
# ---------------------------------------
# expire_seconds, NOT "expires": DatabaseScheduler's ModelEntry silently
# drops unknown option keys — see the schedule header in settings_celery.py
# (2026-07-21 50k-backlog incident).
#
# The status-chart render override that used to live here was removed on
# 2026-07-30: charts are drawn in the browser from /api/server-metrics/series/,
# so there is no render task to schedule. It mattered that BOTH files were
# cleaned — this override re-declared the entry via subscript assignment, so
# deleting it from settings_celery.py alone would have left dev still fanning
# out 48 tasks a minute.

# Re-enable metrics collection in dev at a 10s cadence (prod runs the
# settings_celery.py entry at 60s; runs as Celery task, not in Daphne)
CELERY_BEAT_SCHEDULE["collect-server-metrics"] = {
    "task": "apps.infra.public_app.tasks.collect_server_metrics",
    "schedule": 10.0,
    "options": {
        "expire_seconds": 9,
    },
}

# ---------------------------------------
# Test User Credentials for API Docs Examples
# ---------------------------------------
# Used to populate API docs code examples in Private mode (dev only).
#
# NO LITERAL DEFAULT. This value is RENDERED INTO A PAGE
# (public_app/views/api.py:61,105 -> api_docs_section.html), so a baked-in
# default does not sit quietly in a config file — it gets displayed. The former
# default "Password123!" was published in this repo, in the README and on the
# setup page, and on 2026-08-16 it was found to authenticate as `test-user` on
# PRODUCTION.
#
# Empty is the honest value when the environment has not supplied one: both
# call sites already read it via getattr(settings, "TEST_USER_PASSWORD", "")
# behind a DEBUG check, and an empty example is better than a confident example
# of the wrong password.
TEST_USER_PASSWORD = os.environ.get("SCITEX_HUB_TEST_USER_PASSWORD", "")

# ---------------------------------------
# Dev App Preview
# ---------------------------------------
# Add local app directories here to preview them without publishing.
# Each entry is a filesystem path to a directory containing manifest.json.
# Example: DEV_APPS = ["/home/user/my_app"]
DEV_APPS = []

# EOF
