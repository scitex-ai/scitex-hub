#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: /home/ywatanabe/proj/scitex-cloud/config/settings/settings_staging.py
# ----------------------------------------
from __future__ import annotations
import os
__FILE__ = (
    "./config/settings/settings_staging.py"
)
__DIR__ = os.path.dirname(__FILE__)
# ----------------------------------------

"""
Staging settings for SciTeX Cloud project.
Production-like setup for local testing before deployment.
Uses daphne (ASGI) but without SSL/Cloudflare.
"""

from .settings_shared import *
from dotenv import load_dotenv

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
SCITEX_WRITER_TEMPLATE_BRANCH = os.getenv(
    "SCITEX_WRITER_TEMPLATE_BRANCH", "main"
)
SCITEX_WRITER_TEMPLATE_TAG = os.getenv("SCITEX_WRITER_TEMPLATE_TAG", None)

SECRET_KEY = os.environ.get("SCITEX_CLOUD_DJANGO_SECRET_KEY")

# Allow localhost and internal IPs for staging
ALLOWED_HOSTS = os.environ.get(
    "SCITEX_CLOUD_ALLOWED_HOSTS", "localhost,127.0.0.1,0.0.0.0"
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
CSRF_TRUSTED_ORIGINS = os.environ.get(
    "CSRF_TRUSTED_ORIGINS", "http://localhost:31294,http://127.0.0.1:31294"
).split(",")

# ---------------------------------------
# Database
# ---------------------------------------
# PostgreSQL for staging via PgBouncer (separate from dev and prod)
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("SCITEX_CLOUD_POSTGRES_DB", "scitex_cloud_staging"),
        "USER": os.environ.get("SCITEX_CLOUD_POSTGRES_USER", "scitex_staging"),
        "PASSWORD": os.environ.get("SCITEX_CLOUD_POSTGRES_PASSWORD", "scitex_staging_2025"),
        # Connect via PgBouncer for connection pooling
        "HOST": os.environ.get("SCITEX_CLOUD_DB_HOST", "pgbouncer"),
        "PORT": os.environ.get("SCITEX_CLOUD_DB_PORT", "6432"),
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
EMAIL_BACKEND = os.getenv(
    "SCITEX_CLOUD_EMAIL_BACKEND",
    "django.core.mail.backends.console.EmailBackend"
)

# ---------------------------------------
# Integration
# ---------------------------------------
# Gitea - Local staging instance
GITEA_URL = os.environ.get(
    "SCITEX_CLOUD_GITEA_URL_IN_CONTAINER", "http://gitea:3000"
)
GITEA_API_URL = f"{GITEA_URL}/api/v1"
GITEA_TOKEN = os.environ.get("SCITEX_CLOUD_GITEA_TOKEN", "")
GITEA_INTEGRATION_ENABLED = True

# Gitea Clone URLs (for user-facing clone button)
SCITEX_CLOUD_GITEA_URL = os.environ.get(
    "SCITEX_CLOUD_GITEA_URL_IN_HOST", "http://localhost:3013"
)
SCITEX_CLOUD_GIT_DOMAIN = os.environ.get("SCITEX_CLOUD_GIT_DOMAIN", "127.0.0.1")
SCITEX_CLOUD_GITEA_SSH_PORT = os.environ.get("SCITEX_CLOUD_GITEA_SSH_PORT", "2232")

# ---------------------------------------
# Logging
# ---------------------------------------
LOGGING.update(
    {
        "handlers": {
            # Keep existing handlers from base settings
            **LOGGING.get("handlers", {}),
            # Add staging-specific handlers (similar to prod but more verbose)
            "file_app": {
                "level": "DEBUG",
                "class": "logging.handlers.RotatingFileHandler",
                "filename": os.path.join(LOG_DIR, "app.log"),
                "maxBytes": 1024 * 1024 * 10,
                "backupCount": 5,
                "formatter": "verbose",
            },
            "file_django": {
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
            # Update existing loggers
            "django": {
                "handlers": ["file_django", "console_staging"],
                "level": "INFO",
                "propagate": False,
            },
            "django.request": {
                "handlers": ["file_error", "console_staging"],
                "level": "INFO",
                "propagate": False,
            },
            "scitex": {
                "handlers": ["file_app", "file_error", "console_staging"],
                "level": "DEBUG",
                "propagate": False,
            },
        },
        # Root logger
        "root": {
            "handlers": ["file_error", "console_staging"],
            "level": "INFO",
        },
    }
)

# EOF
