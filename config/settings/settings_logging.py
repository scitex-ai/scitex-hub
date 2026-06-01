#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Timestamp: 2026-02-04
# File: config/settings/settings_logging.py
"""Logging configuration for SciTeX Hub."""

import os
from pathlib import Path

# Get BASE_DIR from parent - this will be set by the importing module
BASE_DIR = Path(__file__).resolve().parent.parent.parent
# Mirror settings_shared.LOG_DIR: GITIGNORED/logs/ by default (PS-102:
# no runtime artifact at repo root); override with SCITEX_HUB_LOG_DIR.
LOG_DIR = Path(os.environ.get("SCITEX_HUB_LOG_DIR", BASE_DIR / "GITIGNORED" / "logs"))
LOG_DIR.mkdir(parents=True, exist_ok=True)

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {module} {process:d} {thread:d} {message}",
            "style": "{",
        },
        "simple": {
            "format": "{levelname} {message}",
            "style": "{",
        },
        "standard": {
            "format": "{asctime} [{levelname}] {name}: {message}",
            "style": "{",
        },
    },
    "filters": {
        "require_debug_true": {
            "()": "django.utils.log.RequireDebugTrue",
        },
        "require_debug_false": {
            "()": "django.utils.log.RequireDebugFalse",
        },
    },
    "handlers": {
        "console": {
            "level": "INFO",
            "filters": ["require_debug_true"],
            "class": "logging.StreamHandler",
            "formatter": "standard",
        },
        "mail_admins": {
            "level": "ERROR",
            "filters": ["require_debug_false"],
            "class": "django.utils.log.AdminEmailHandler",
            "formatter": "verbose",
        },
        "null": {
            "class": "logging.NullHandler",
        },
        # Django app logs
        "django_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": str(LOG_DIR / "django.log"),
            "maxBytes": 5242880,  # 5MB
            "backupCount": 5,
            "formatter": "standard",
            "level": "INFO",
        },
        # Celery task logs
        "celery_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": str(LOG_DIR / "celery.log"),
            "maxBytes": 5242880,  # 5MB
            "backupCount": 5,
            "formatter": "standard",
            "level": "INFO",
        },
        # SLURM job logs
        "slurm_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": str(LOG_DIR / "slurm.log"),
            "maxBytes": 5242880,  # 5MB
            "backupCount": 3,
            "formatter": "standard",
            "level": "INFO",
        },
        # Git operations logs
        "git_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": str(LOG_DIR / "git.log"),
            "maxBytes": 5242880,  # 5MB
            "backupCount": 3,
            "formatter": "standard",
            "level": "INFO",
        },
        # Error logs (all errors)
        "error_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": str(LOG_DIR / "errors.log"),
            "maxBytes": 5242880,  # 5MB
            "backupCount": 5,
            "formatter": "standard",
            "level": "ERROR",
        },
        # App-specific logs
        "writer_app_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": str(LOG_DIR / "writer_app.log"),
            "maxBytes": 5242880,
            "backupCount": 3,
            "formatter": "standard",
            "level": "DEBUG",
        },
        "scholar_app_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": str(LOG_DIR / "scholar_app.log"),
            "maxBytes": 5242880,
            "backupCount": 3,
            "formatter": "standard",
            "level": "DEBUG",
        },
        "console_app_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": str(LOG_DIR / "console_app.log"),
            "maxBytes": 5242880,
            "backupCount": 3,
            "formatter": "standard",
            "level": "DEBUG",
        },
        "project_app_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": str(LOG_DIR / "project_app.log"),
            "maxBytes": 5242880,
            "backupCount": 3,
            "formatter": "standard",
            "level": "DEBUG",
        },
    },
    "loggers": {
        # Django framework
        "django": {
            "handlers": ["django_file", "console"],
            "level": "INFO",
            "propagate": False,
        },
        "django.request": {
            "handlers": ["django_file", "error_file"],
            "level": "INFO",
            "propagate": False,
        },
        "django.security": {
            "handlers": ["error_file"],
            "level": "ERROR",
            "propagate": False,
        },
        # Celery tasks
        "celery": {
            "handlers": ["celery_file", "console"],
            "level": "INFO",
            "propagate": False,
        },
        "celery.task": {
            "handlers": ["celery_file"],
            "level": "INFO",
            "propagate": False,
        },
        # SLURM jobs
        "scitex.slurm": {
            "handlers": ["slurm_file", "console"],
            "level": "INFO",
            "propagate": False,
        },
        # Git operations
        "scitex.git": {
            "handlers": ["git_file"],
            "level": "INFO",
            "propagate": False,
        },
        # SciTeX app (general)
        "scitex": {
            "handlers": ["django_file", "console"],
            "level": "INFO",
            "propagate": False,
        },
        # All errors
        "scitex.errors": {
            "handlers": ["error_file", "console"],
            "level": "ERROR",
            "propagate": False,
        },
        # App-specific loggers
        "apps.workspace.writer_app": {
            "handlers": ["writer_app_file", "console"],
            "level": "DEBUG",
            "propagate": False,
        },
        "apps.workspace.scholar_app": {
            "handlers": ["scholar_app_file", "console"],
            "level": "DEBUG",
            "propagate": False,
        },
        "apps.workspace.console_app": {
            "handlers": ["console_app_file", "console"],
            "level": "DEBUG",
            "propagate": False,
        },
        "apps.infra.project_app": {
            "handlers": ["project_app_file", "console"],
            "level": "DEBUG",
            "propagate": False,
        },
    },
}

# EOF
