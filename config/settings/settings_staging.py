#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: /home/ywatanabe/proj/scitex-hub/config/settings/settings_staging.py
# ----------------------------------------
from __future__ import annotations

import os

__FILE__ = "./config/settings/settings_staging.py"
__DIR__ = os.path.dirname(__FILE__)
# ----------------------------------------

"""
Staging settings for SciTeX Hub project.
Production-like setup for local testing before deployment.
Uses daphne (ASGI) but without SSL/Cloudflare.
"""

from dotenv import load_dotenv

from config import branding
from config._env import (
    getenv_with_legacy_alias as _getenv_alias,
)
from config._env import (
    require_env_with_legacy_alias as _require_env_alias,
)

from ._logging_merge import merge_logging
from .settings_shared import *

# Environment identity -- drives the tab title marker "(staging)" and the
# NAVY-ON-WHITE favicon. Literal: running settings_staging IS staging.
SCITEX_ENV = branding.ENV_STAGING

# ---------------------------------------
# Env
# ---------------------------------------
try:
    load_dotenv(os.path.join(BASE_DIR, ".env"))
except Exception as e:
    print(f"Error loading .env: {e}")

# ---------------------------------------
# Security
# ---------------------------------------
# Staging allows DEBUG for testing (configurable via env)
DEBUG = os.getenv("DEBUG", "False").lower() in ("true", "1", "yes")

# ---------------------------------------
# SciTeX Settings
# ---------------------------------------
# Use 'main' branch for writer template in staging (same as prod)
SCITEX_WRITER_TEMPLATE_BRANCH = os.getenv("SCITEX_WRITER_TEMPLATE_BRANCH", "main")
SCITEX_WRITER_TEMPLATE_TAG = os.getenv("SCITEX_WRITER_TEMPLATE_TAG", None)

# Fail-loud if SECRET_KEY is unset under BOTH canonical and legacy aliases.
# Honors SCITEX_CLOUD_DJANGO_SECRET_KEY (ADR-0001 legacy) with a
# DeprecationWarning when used.
SECRET_KEY = _require_env_alias("SCITEX_HUB_DJANGO_SECRET_KEY")

# Allow localhost and internal IPs for staging
ALLOWED_HOSTS = _getenv_alias(
    "SCITEX_HUB_ALLOWED_HOSTS", "localhost,127.0.0.1,0.0.0.0"
).split(",")

# Security headers (lighter than production - no external access)
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "SAMEORIGIN"

# No SSL in staging (direct HTTP access)
SECURE_SSL_REDIRECT = False
SECURE_HSTS_SECONDS = 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SECURE_HSTS_PRELOAD = False

# ---------------------------------------
# Cookie
# ---------------------------------------
# No HTTPS in staging
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True

# CSRF trusted origins for staging (port 31294 per 3129X scheme)
CSRF_TRUSTED_ORIGINS = _getenv_alias(
    "SCITEX_HUB_CSRF_TRUSTED_ORIGINS",
    "http://localhost:31294,http://127.0.0.1:31294",
).split(",")

# ---------------------------------------
# Database
# ---------------------------------------
# PostgreSQL for staging via PgBouncer (separate from dev and prod)
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": _getenv_alias("SCITEX_HUB_POSTGRES_DB", "scitex_hub_staging"),
        "USER": _getenv_alias("SCITEX_HUB_POSTGRES_USER", "scitex_staging"),
        "PASSWORD": _getenv_alias(
            "SCITEX_HUB_POSTGRES_PASSWORD", "scitex_staging_2025"
        ),
        # Connect via PgBouncer for connection pooling
        "HOST": _getenv_alias("SCITEX_HUB_DB_HOST", "pgbouncer"),
        "PORT": _getenv_alias("SCITEX_HUB_DB_PORT", "6432"),
        "ATOMIC_REQUESTS": True,
        # CONN_MAX_AGE=0: Let PgBouncer handle connection pooling
        "CONN_MAX_AGE": 0,
        "CONN_HEALTH_CHECKS": True,
        # Disable server-side cursors (incompatible with PgBouncer transaction pooling)
        "DISABLE_SERVER_SIDE_CURSORS": True,
        "OPTIONS": {
            "connect_timeout": 10,
        },
    }
}

# ---------------------------------------
# Email
# ---------------------------------------
# Console backend for staging (no actual emails sent)
EMAIL_BACKEND = _getenv_alias(
    "SCITEX_HUB_EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend"
)

# ---------------------------------------
# Integration
# ---------------------------------------
# Gitea - Local staging instance
GITEA_URL = _getenv_alias("SCITEX_HUB_GITEA_URL_IN_CONTAINER", "http://gitea:3000")
GITEA_API_URL = f"{GITEA_URL}/api/v1"
GITEA_TOKEN = _getenv_alias("SCITEX_HUB_GITEA_TOKEN", "")
GITEA_INTEGRATION_ENABLED = True

# Gitea Clone URLs (for user-facing clone button)
SCITEX_HUB_GITEA_URL = _getenv_alias(
    "SCITEX_HUB_GITEA_URL_IN_HOST", "http://localhost:3013"
)
SCITEX_HUB_GIT_DOMAIN = _getenv_alias("SCITEX_HUB_GIT_DOMAIN", "127.0.0.1")
SCITEX_HUB_GITEA_SSH_PORT = _getenv_alias("SCITEX_HUB_GITEA_SSH_PORT", "2232")

# ---------------------------------------
# Logging
# ---------------------------------------
# merge_logging, NOT LOGGING.update -- see the note in settings_prod.py and the
# measurement in config/settings/_logging_merge.py. `update` replaced the whole
# loggers section, which deleted the base's wiring and left mail_admins
# referenced by nothing in staging too.
LOGGING = merge_logging(
    LOGGING,
    {
        "handlers": {
            # Staging-specific handlers (similar to prod but more verbose).
            # The base's handlers are kept by the merge.
            "file_app": {
                "level": "DEBUG",
                "class": "logging.handlers.RotatingFileHandler",
                "filename": os.path.join(LOG_DIR, "app.log"),
                "maxBytes": 1024 * 1024 * 10,
                "backupCount": 5,
                "formatter": "verbose",
            },
            # REDEFINES the base's "django_file" instead of adding a second
            # handler on the same file -- see the same note in settings_prod.
            "django_file": {
                "level": "INFO",
                "class": "logging.handlers.RotatingFileHandler",
                "filename": os.path.join(LOG_DIR, "django.log"),
                "maxBytes": 1024 * 1024 * 10,
                "backupCount": 5,
                "formatter": "verbose",
            },
            "file_error": {
                "level": "ERROR",
                "class": "logging.handlers.RotatingFileHandler",
                "filename": os.path.join(LOG_DIR, "error.log"),
                "maxBytes": 1024 * 1024 * 10,
                "backupCount": 5,
                "formatter": "verbose",
            },
            "console_staging": {
                "level": "INFO",
                "class": "logging.StreamHandler",
                "formatter": "standard",
            },
        },
        "loggers": {
            # Loggers redefined for staging. Every logger NOT named here --
            # django.security, scitex.errors and the four app loggers -- keeps
            # the base's handlers, mail_admins included.
            "django": {
                "handlers": ["django_file", "console_staging"],
                "level": "INFO",
                "propagate": False,
            },
            # mail_admins is re-listed because redefining a logger replaces its
            # handler list. NOTE: staging pins the console email backend in
            # deployment/docker/envs/.env.staging, so this rail composes
            # correctly but prints instead of sending -- that is staging's
            # deliberate choice, and it is why the wiring must be gated by
            # composition rather than by watching for mail to arrive.
            "django.request": {
                "handlers": ["file_error", "console_staging", "mail_admins"],
                "level": "INFO",
                "propagate": False,
            },
            "scitex": {
                "handlers": ["file_app", "file_error", "console_staging"],
                "level": "DEBUG",
                "propagate": False,
            },
        },
        # Root logger. Deliberately NOT on the operator rail -- same reason as
        # production: an unbounded catch-all message set makes the mailbox
        # unreadable, which is the same outcome as sending nothing.
        "root": {
            "handlers": ["file_error", "console_staging"],
            "level": "INFO",
        },
    },
)

# EOF


# ---------------------------------------------------------------------------
# Content-hashed static URLs (opt-in, prod/staging only)
# ---------------------------------------------------------------------------
# Only the environments whose entrypoint runs collectstatic may use the manifest
# backend — it resolves {% static %} through staticfiles.json, which does not
# exist until collectstatic has run. See config/settings/settings_static.py for
# why the hashing is load-bearing (stale CSS + fresh JS rendered the launcher as
# two columns of stacked icons on a real phone).
from .settings_static import hashed_storages  # noqa: E402

STORAGES = hashed_storages(STORAGES)  # noqa: F405

# EOF
