#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Timestamp: 2026-07-10
# File: config/settings/settings_logging.py
"""Logging configuration for SciTeX Hub."""

import os
from pathlib import Path

from scitex_config._ecosystem import local_state

# Get BASE_DIR from parent - this will be set by the importing module
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# LOG_DIR: hub-wide (NOT per-visitor-project) operational runtime state for
# this Django/Celery process. Resolved via the ecosystem's canonical
# runtime-state-db-layout convention (scitex-dev skill
# general/01_ecosystem/12_local-state-resolution.md +
# 13_runtime-state-db-layout.md): logs are RUNTIME-nature data, so they
# resolve through ``local_state.runtime_path()`` rather than a hand-rolled
# precedence walk (PS-182 forbids the latter). This is deliberately NOT
# the same pattern as the per-visitor ``.scitex/writer`` / ``.scitex/scholar``
# paths (those live under each visitor's own project directory under
# USER_DATA_ROOT) -- server-process logs belong to the hub deployment
# itself, not to any one visitor's project.
#
# ``runtime_path("hub", "logs")`` resolves to
# ``<repo-root>/.scitex/hub/runtime/logs`` when this checkout is a git
# repo with ``.scitex/hub/`` present (dev: repo bind-mounted into /app,
# .git included), else falls back to ``$SCITEX_DIR/hub/runtime/logs``
# (prod/staging: SCITEX_DIR=/app/.scitex is set explicitly in
# docker-compose.yml, so this resolves to the SAME physical path -- a
# persistent named Docker volume that root-init.sh creates + chowns
# unconditionally on every boot). Either way, the directory is also
# created lazily by ``runtime_path()`` itself, so a fallback default can
# never again silently point at a directory nothing prepared. See
# incident hub-prod-outage-celery-log-permission (2026-07-09/10).
#
# SCITEX_HUB_LOG_DIR remains a legitimate operator override (e.g. to
# redirect logs to a different mount); only the *default* changed.
_log_dir_override = os.environ.get("SCITEX_HUB_LOG_DIR")
LOG_DIR = (
    Path(_log_dir_override)
    if _log_dir_override
    else local_state.runtime_path("hub", "logs")
)
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
        # THE OPERATOR NOTIFICATION RAIL. Every logger below that can carry an
        # operational failure attaches this, so a failure reaches a person and
        # not only a rotating file nobody opens. It was defined here and
        # referenced by NO logger until 2026-08-15, which is why the visitor
        # pool sat 14/16 quarantined for four days: the error WAS logged, to
        # errors.log, and nowhere else.
        #
        # Recipients come from ADMINS (settings_shared), which still uses the
        # (name, address) pair form: measured on 2026-08-15, Django 6.0.8
        # delivers to both recipients and emits RemovedInDjango70Warning
        # asking for bare address strings. The pairs stay until pyproject's
        # "Django>=5.2" floor moves to >=6.0 -- 5.2 unpacks the pairs, so
        # switching early would break this rail on the oldest supported
        # version. require_debug_false keeps it off developer machines. The
        # handler class is Django's
        # AdminEmailHandler plus a repeat throttle: the first of each distinct
        # error goes out and its repeats are dropped for the window and counted
        # into the next message, because one crash-looping view sending
        # hundreds of identical emails is a channel the operator mutes -- the
        # same outcome as sending nothing. The throttle is part of the HANDLER
        # rather than a filter so that annotating the message cannot corrupt
        # what the file handlers on the same logger write; see the module
        # docstring in _suppress_repeated_errors.py.
        #
        # Environments refine this config through
        # config.settings._logging_merge.merge_logging, which REFUSES a result
        # where this handler has lost its loggers.
        "mail_admins": {
            "level": "ERROR",
            "filters": ["require_debug_false"],
            "class": (
                "config.settings._suppress_repeated_errors"
                ".ThrottledAdminEmailHandler"
            ),
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
            "handlers": ["django_file", "error_file", "mail_admins"],
            "level": "INFO",
            "propagate": False,
        },
        "django.security": {
            "handlers": ["error_file", "mail_admins"],
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
            "handlers": ["error_file", "console", "mail_admins"],
            "level": "ERROR",
            "propagate": False,
        },
        # App-specific loggers. These sit at DEBUG so their files stay
        # detailed; mail_admins is itself level ERROR, so only failures leave
        # the machine. apps.infra.project_app carries the visitor-pool and
        # template-clone path whose four-day silent failure motivated this.
        "apps.workspace.writer_app": {
            "handlers": ["writer_app_file", "console", "mail_admins"],
            "level": "DEBUG",
            "propagate": False,
        },
        "apps.workspace.scholar_app": {
            "handlers": ["scholar_app_file", "console", "mail_admins"],
            "level": "DEBUG",
            "propagate": False,
        },
        "apps.workspace.console_app": {
            "handlers": ["console_app_file", "console", "mail_admins"],
            "level": "DEBUG",
            "propagate": False,
        },
        "apps.infra.project_app": {
            "handlers": ["project_app_file", "console", "mail_admins"],
            "level": "DEBUG",
            "propagate": False,
        },
    },
}

# EOF
