#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: /home/ywatanabe/proj/scitex-hub/config/settings/settings_prod.py
# ----------------------------------------
from __future__ import annotations

import os

__FILE__ = "./config/settings/settings_prod.py"
__DIR__ = os.path.dirname(__FILE__)
# ----------------------------------------

"""
Production settings for SciTeX Hub project.
Optimized for deployment with Cloudflare Tunnel.
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

# Environment identity -- unmarked tab title ("<App> — SciTeX") and the NAVY
# favicon: the official product look. Literal: settings_prod IS production.
SCITEX_ENV = branding.ENV_PRODUCTION

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
# Allow DEBUG override via environment variable for troubleshooting
# WARNING: Set DEBUG=False in production after debugging!
DEBUG = os.getenv("DEBUG", "False").lower() in ("true", "1", "yes")

# ---------------------------------------
# SciTeX Settings
# ---------------------------------------
# Use 'main' branch for writer template in production
SCITEX_WRITER_TEMPLATE_BRANCH = os.getenv("SCITEX_WRITER_TEMPLATE_BRANCH", "main")
SCITEX_WRITER_TEMPLATE_TAG = os.getenv("SCITEX_WRITER_TEMPLATE_TAG", None)

# Fail-loud if SECRET_KEY is unset under BOTH canonical and legacy aliases.
# Honors SCITEX_CLOUD_DJANGO_SECRET_KEY (ADR-0001 legacy) with a
# DeprecationWarning when used.
SECRET_KEY = _require_env_alias("SCITEX_HUB_DJANGO_SECRET_KEY")

ALLOWED_HOSTS = _getenv_alias("SCITEX_HUB_ALLOWED_HOSTS", "127.0.0.1,localhost").split(
    ","
)
# Allow internal Docker container-to-container OAuth2 requests
ALLOWED_HOSTS += ["scitex-hub-prod-django-1"]

SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_PRELOAD = True
SECURE_REDIRECT_EXEMPT = []

# SSL handled by Cloudflare Tunnel
SECURE_SSL_REDIRECT = (
    _getenv_alias("SCITEX_HUB_ENABLE_SSL_REDIRECT", "false").lower() == "true"
)
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
X_FRAME_OPTIONS = "SAMEORIGIN"  # Allow same-site iframes (needed for PDF viewer)
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"

# ---------------------------------------
# Cookie
# ---------------------------------------
SESSION_COOKIE_SECURE = (
    _getenv_alias("SCITEX_HUB_FORCE_HTTPS_COOKIES", "true").lower() == "true"
)
CSRF_COOKIE_SECURE = (
    _getenv_alias("SCITEX_HUB_FORCE_HTTPS_COOKIES", "true").lower() == "true"
)
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True

# ---------------------------------------
# Database
# ---------------------------------------
if _getenv_alias("SCITEX_HUB_USE_SQLITE_PROD"):
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "data" / "db" / "sqlite" / "scitex_hub_prod.db",
        }
    }
else:
    # PostgreSQL (default for production)
    DB_PASSWORD = _getenv_alias("SCITEX_HUB_DB_PASSWORD")

    if DB_PASSWORD and DB_PASSWORD != "CHANGE-THIS-DATABASE-PASSWORD-FOR-PROD":
        # Remote PostgreSQL via PgBouncer (for production deployment)
        DATABASES = {
            "default": {
                "ENGINE": "django.db.backends.postgresql",
                "NAME": _getenv_alias("SCITEX_HUB_DB_NAME", "scitex_hub_prod"),
                "USER": _getenv_alias("SCITEX_HUB_DB_USER", "scitex_prod"),
                "PASSWORD": DB_PASSWORD,
                # Connect via PgBouncer for connection pooling
                "HOST": _getenv_alias("SCITEX_HUB_DB_HOST", "pgbouncer"),
                "PORT": _getenv_alias("SCITEX_HUB_DB_PORT", "6432"),
                # ATOMIC_REQUESTS disabled: incompatible with ASGI (Daphne)
                # + PgBouncer transaction pooling.  Middleware and views run
                # in different threads under ASGI, so a dirty connection in
                # one thread cascades "transaction aborted" errors to the
                # view's atomic wrapper.  Views needing transactions should
                # use @transaction.atomic explicitly.
                "ATOMIC_REQUESTS": False,
                # CONN_MAX_AGE=0: Let PgBouncer handle connection pooling
                # This closes Django connections after each request, allowing
                # PgBouncer to efficiently manage the actual PostgreSQL connections
                "CONN_MAX_AGE": 0,
                "CONN_HEALTH_CHECKS": True,  # Django 4.1+ connection health checks
                # Disable server-side cursors (incompatible with PgBouncer transaction pooling)
                "DISABLE_SERVER_SIDE_CURSORS": True,
                "OPTIONS": {
                    "connect_timeout": 10,
                    "options": "-c statement_timeout=30000",
                },
            }
        }
    else:
        # Fallback to environment variables (for docker-compose via PgBouncer)
        DATABASES = {
            "default": {
                "ENGINE": "django.db.backends.postgresql",
                "NAME": _getenv_alias("SCITEX_HUB_POSTGRES_DB", "scitex_hub_prod"),
                "USER": _getenv_alias("SCITEX_HUB_POSTGRES_USER", "scitex_prod"),
                "PASSWORD": _getenv_alias(
                    "SCITEX_HUB_POSTGRES_PASSWORD", "CHANGE_THIS_IN_PROD"
                ),
                # Connect via PgBouncer for connection pooling
                "HOST": _getenv_alias("SCITEX_HUB_DB_HOST", "pgbouncer"),
                "PORT": _getenv_alias("SCITEX_HUB_DB_PORT", "6432"),
                "ATOMIC_REQUESTS": False,
                "CONN_MAX_AGE": 0,
                "CONN_HEALTH_CHECKS": True,
                "DISABLE_SERVER_SIDE_CURSORS": True,
            }
        }

# ADMINS / MANAGERS moved to settings_shared on 2026-08-15 so that every
# non-dev environment inherits the same recipients. Defining them only here
# left staging with the empty default, i.e. an error-mail handler wired to
# nobody.

# ---------------------------------------
# Integration
# ---------------------------------------
# Gitea - Always enabled (core feature)
GITEA_URL = _getenv_alias("SCITEX_HUB_GITEA_URL", "https://git.scitex.ai")
GITEA_API_URL = _getenv_alias(
    "SCITEX_HUB_GITEA_API_URL", "https://git.scitex.ai/api/v1"
)
GITEA_TOKEN = _getenv_alias("SCITEX_HUB_GITEA_TOKEN", "")
GITEA_INTEGRATION_ENABLED = True  # Core feature, always enabled

# Gitea Clone URLs (for user-facing clone button)
SCITEX_HUB_GITEA_URL = _getenv_alias("SCITEX_HUB_GITEA_URL", "https://git.scitex.ai")
SCITEX_HUB_GIT_DOMAIN = _getenv_alias("SCITEX_HUB_GIT_DOMAIN", "git.scitex.ai")
SCITEX_HUB_GITEA_SSH_PORT = require_env("SCITEX_HUB_GITEA_SSH_PORT")

# ---------------------------------------
# Logging
# ---------------------------------------
LOGGING = merge_logging(
    LOGGING,
    {
        "handlers": {
            # Production-specific handlers. The base's handlers are kept by the
            # merge; only the entries named here are added or replaced.
            "file_app": {
                "level": "INFO",
                "class": "logging.handlers.RotatingFileHandler",
                "filename": os.path.join(LOG_DIR, "app.log"),
                "maxBytes": 1024 * 1024 * 10,
                "backupCount": 10,
                "formatter": "verbose",
            },
            # Deliberately REDEFINES the base's "django_file" rather than
            # adding a second handler under a new name. Both wrote to
            # LOG_DIR/django.log; two RotatingFileHandlers on one file rotate
            # against each other. Now the base's entry is refined -- bigger
            # files, more backups, verbose format -- and there is still exactly
            # one writer.
            "django_file": {
                "level": "INFO",
                "class": "logging.handlers.RotatingFileHandler",
                "filename": os.path.join(LOG_DIR, "django.log"),
                "maxBytes": 1024 * 1024 * 10,
                "backupCount": 10,
                "formatter": "verbose",
            },
            "file_error": {
                "level": "ERROR",
                "class": "logging.handlers.RotatingFileHandler",
                "filename": os.path.join(LOG_DIR, "error.log"),
                "maxBytes": 1024 * 1024 * 10,
                "backupCount": 10,
                "formatter": "verbose",
            },
            "file_security": {
                "level": "INFO",
                "class": "logging.handlers.RotatingFileHandler",
                "filename": os.path.join(LOG_DIR, "security.log"),
                "maxBytes": 1024 * 1024 * 10,
                "backupCount": 10,
                "formatter": "verbose",
            },
        },
        "loggers": {
            # Loggers redefined for production. Every logger NOT named here --
            # scitex.errors and the four app loggers among them -- keeps the
            # base's handlers, mail_admins included.
            "django": {
                "handlers": ["django_file"],
                "level": "INFO",
                "propagate": False,
            },
            # mail_admins is re-listed because redefining a logger replaces its
            # handler list. Dropping it here is the exact defect this file had:
            # a 500 reached error.log and nobody else.
            "django.request": {
                "handlers": ["file_error", "mail_admins"],
                "level": "ERROR",
                "propagate": False,
            },
            "django.security": {
                "handlers": ["file_security", "mail_admins"],
                "level": "INFO",
                "propagate": False,
            },
            "scitex": {
                "handlers": ["file_app", "file_error"],
                "level": "INFO",
                "propagate": False,
            },
        },
        # Root logger catches everything else. Deliberately NOT on the operator
        # rail: root is the catch-all for loggers nobody enumerated, so its
        # message set is unbounded and mostly third-party. Mailing an unbounded
        # message set is how an operator learns to mute the channel, which is
        # the same outcome as sending nothing. hub's own failure paths are the
        # enumerated loggers above.
        "root": {
            "handlers": ["file_error"],
            "level": "ERROR",
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
