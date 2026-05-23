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
Production settings for SciTeX Cloud project.
Optimized for deployment with Cloudflare Tunnel.
"""

from dotenv import load_dotenv

from .settings_shared import *

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

SECRET_KEY = os.environ.get("SCITEX_CLOUD_DJANGO_SECRET_KEY")

ALLOWED_HOSTS = os.environ.get(
    "SCITEX_CLOUD_ALLOWED_HOSTS", "127.0.0.1,localhost"
).split(",")
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
    os.environ.get("SCITEX_CLOUD_ENABLE_SSL_REDIRECT", "false").lower() == "true"
)
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
X_FRAME_OPTIONS = "SAMEORIGIN"  # Allow same-site iframes (needed for PDF viewer)
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"

# ---------------------------------------
# Cookie
# ---------------------------------------
SESSION_COOKIE_SECURE = (
    os.environ.get("SCITEX_CLOUD_FORCE_HTTPS_COOKIES", "true").lower() == "true"
)
CSRF_COOKIE_SECURE = (
    os.environ.get("SCITEX_CLOUD_FORCE_HTTPS_COOKIES", "true").lower() == "true"
)
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True

# ---------------------------------------
# Database
# ---------------------------------------
if os.environ.get("SCITEX_CLOUD_USE_SQLITE_PROD"):
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "data" / "db" / "sqlite" / "scitex_hub_prod.db",
        }
    }
else:
    # PostgreSQL (default for production)
    DB_PASSWORD = os.environ.get("SCITEX_CLOUD_DB_PASSWORD")

    if DB_PASSWORD and DB_PASSWORD != "CHANGE-THIS-DATABASE-PASSWORD-FOR-PROD":
        # Remote PostgreSQL via PgBouncer (for production deployment)
        DATABASES = {
            "default": {
                "ENGINE": "django.db.backends.postgresql",
                "NAME": os.environ.get("SCITEX_CLOUD_DB_NAME", "scitex_hub_prod"),
                "USER": os.environ.get("SCITEX_CLOUD_DB_USER", "scitex_prod"),
                "PASSWORD": DB_PASSWORD,
                # Connect via PgBouncer for connection pooling
                "HOST": os.environ.get("SCITEX_CLOUD_DB_HOST", "pgbouncer"),
                "PORT": os.environ.get("SCITEX_CLOUD_DB_PORT", "6432"),
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
                "NAME": os.environ.get("SCITEX_CLOUD_POSTGRES_DB", "scitex_hub_prod"),
                "USER": os.environ.get("SCITEX_CLOUD_POSTGRES_USER", "scitex_prod"),
                "PASSWORD": os.environ.get(
                    "SCITEX_CLOUD_POSTGRES_PASSWORD", "CHANGE_THIS_IN_PROD"
                ),
                # Connect via PgBouncer for connection pooling
                "HOST": os.environ.get("SCITEX_CLOUD_DB_HOST", "pgbouncer"),
                "PORT": os.environ.get("SCITEX_CLOUD_DB_PORT", "6432"),
                "ATOMIC_REQUESTS": False,
                "CONN_MAX_AGE": 0,
                "CONN_HEALTH_CHECKS": True,
                "DISABLE_SERVER_SIDE_CURSORS": True,
            }
        }

# ---------------------------------------
# Email
# ---------------------------------------
ADMINS = [
    ("Admin", "admin@scitex.ai"),
    ("Yusuke Watanabe", "ywatanabe@scitex.ai"),
]

# ---------------------------------------
# Integration
# ---------------------------------------
# Gitea - Always enabled (core feature)
GITEA_URL = os.environ.get("SCITEX_CLOUD_GITEA_URL", "https://git.scitex.ai")
GITEA_API_URL = os.environ.get(
    "SCITEX_CLOUD_GITEA_API_URL", "https://git.scitex.ai/api/v1"
)
GITEA_TOKEN = os.environ.get("SCITEX_CLOUD_GITEA_TOKEN", "")
GITEA_INTEGRATION_ENABLED = True  # Core feature, always enabled

# Gitea Clone URLs (for user-facing clone button)
SCITEX_CLOUD_GITEA_URL = os.environ.get(
    "SCITEX_CLOUD_GITEA_URL", "https://git.scitex.ai"
)
SCITEX_CLOUD_GIT_DOMAIN = os.environ.get("SCITEX_CLOUD_GIT_DOMAIN", "git.scitex.ai")
SCITEX_CLOUD_GITEA_SSH_PORT = require_env("SCITEX_CLOUD_GITEA_SSH_PORT")

# ---------------------------------------
# Logging
# ---------------------------------------
LOGGING.update(
    {
        "handlers": {
            # Keep existing handlers from base settings
            **LOGGING.get("handlers", {}),
            # Add production-specific handlers
            "file_app": {
                "level": "INFO",
                "class": "logging.handlers.RotatingFileHandler",
                "filename": os.path.join(LOG_DIR, "app.log"),
                "maxBytes": 1024 * 1024 * 10,
                "backupCount": 10,
                "formatter": "verbose",
            },
            "file_django": {
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
            # Update existing loggers
            "django": {
                "handlers": ["file_django"],
                "level": "INFO",
                "propagate": False,
            },
            "django.request": {
                "handlers": ["file_error"],
                "level": "ERROR",
                "propagate": False,
            },
            "django.security": {
                "handlers": ["file_security"],
                "level": "INFO",
                "propagate": False,
            },
            "scitex": {
                "handlers": ["file_app", "file_error"],
                "level": "INFO",
                "propagate": False,
            },
        },
        # Root logger catches everything else
        "root": {
            "handlers": ["file_error"],
            "level": "ERROR",
        },
    }
)

# EOF
