#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Timestamp: 2026-02-04
# File: config/settings/settings_celery.py
"""Celery configuration for SciTeX Hub async task queue."""

import os

# Celery broker and result backend
CELERY_BROKER_URL = os.getenv("SCITEX_HUB_REDIS_URL", "redis://localhost:6379/1")
CELERY_RESULT_BACKEND = "django-db"
CELERY_CACHE_BACKEND = "django-cache"
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = "UTC"
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60  # 30 minutes hard kill (SIGKILL) per task
# Soft limit fires SoftTimeLimitExceeded 5 minutes before hard kill so tasks
# get a window to clean up (close cursors, release locks). Without this, a
# stuck task burns the full 30 minutes before being killed (issue #151).
CELERY_TASK_SOFT_TIME_LIMIT = 25 * 60
# Ack after task finishes so a stuck task that gets killed (worker lost,
# OOM, SIGKILL on hard limit) is requeued instead of silently dropped.
CELERY_TASK_ACKS_LATE = True
# Reject tasks back to the broker when the worker process dies, so the
# next worker picks them up rather than the message being lost (issue #151).
CELERY_TASK_REJECT_ON_WORKER_LOST = True
CELERY_RESULT_EXTENDED = True

# Test-mode eager execution
# ------------------------
# The SQLite test gate (SCITEX_HUB_USE_SQLITE_DEV=1, used by pytest-matrix
# in CI) runs without a Redis broker, so .delay() raises
# kombu.exceptions.OperationalError. Run tasks inline instead of enqueuing.
# EAGER_PROPAGATES=True surfaces task exceptions to the caller — per
# project policy, errors must be loud (no silent fallback).
# In-memory broker keeps Celery's internal probes (canvas, etc.) from
# doing real network I/O at import time.
if os.environ.get("SCITEX_HUB_USE_SQLITE_DEV"):
    CELERY_TASK_ALWAYS_EAGER = True
    CELERY_TASK_EAGER_PROPAGATES = True
    CELERY_BROKER_URL = "memory://"

# Task routing to dedicated queues
CELERY_TASK_ROUTES = {
    "apps.workspace.writer_app.tasks.*": {"queue": "ai_queue"},
    "apps.workspace.scholar_app.tasks.*": {"queue": "search_queue"},
    "apps.workspace.console_app.tasks.*": {"queue": "compute_queue"},
}

# Fair scheduling: Rate limits per task
CELERY_TASK_ANNOTATIONS = {
    "apps.workspace.writer_app.tasks.ai_suggest": {"rate_limit": "10/m"},
    "apps.workspace.writer_app.tasks.ai_generate": {"rate_limit": "5/m"},
    "apps.workspace.scholar_app.tasks.search_papers": {"rate_limit": "30/m"},
    "apps.workspace.scholar_app.tasks.process_pdf": {"rate_limit": "20/m"},
}

# Worker configuration for fairness
CELERY_WORKER_PREFETCH_MULTIPLIER = 1  # One task at a time for fair scheduling
CELERY_WORKER_CONCURRENCY = 4  # Parallel workers
CELERY_WORKER_MAX_TASKS_PER_CHILD = (
    100  # Auto-restart after 100 tasks (prevents memory leaks)
)
CELERY_WORKER_MAX_MEMORY_PER_CHILD = (
    500_000  # Auto-restart if worker exceeds 500MB (KB units)
)

# Beat scheduler for periodic tasks
CELERY_BEAT_SCHEDULER = "django_celery_beat.schedulers:DatabaseScheduler"

# Periodic task schedule
CELERY_BEAT_SCHEDULE = {
    # Clean up expired visitor allocations every 5 minutes
    "cleanup-expired-visitor-allocations": {
        "task": "apps.infra.public_app.tasks.cleanup_expired_visitor_allocations",
        "schedule": 300.0,  # Every 5 minutes (in seconds)
        "options": {
            "expires": 270.0,  # Expire after 4.5 minutes if not started
        },
    },
    # Generate server status charts every 1 minute
    "generate-status-charts": {
        "task": "apps.infra.public_app.tasks.generate_status_charts",
        "schedule": 60.0,  # Every 1 minute
        "options": {
            "expires": 55.0,  # Expire after 55 seconds if not started
        },
    },
    # Check site health every 1 minute and notify on failures
    "check-site-health": {
        "task": "apps.infra.public_app.tasks.check_site_health",
        "schedule": 60.0,  # Every 1 minute
        "options": {
            "expires": 55.0,  # Expire after 55 seconds if not started
        },
    },
    # Check for request flood patterns every 1 minute
    "check-request-flood": {
        "task": "apps.infra.public_app.tasks.check_request_flood",
        "schedule": 60.0,  # Every 1 minute
        "options": {
            "expires": 55.0,  # Expire after 55 seconds if not started
        },
    },
    # Warm /status page cache every 1 minute so user-facing visitors
    # never hit the ~17s cold path (scitex-orochi#82).
    "warm-public-status-cache": {
        "task": "apps.infra.public_app.tasks.warm_public_status_cache",
        "schedule": 60.0,  # Every 1 minute
        "options": {
            "expires": 55.0,
        },
    },
}

# EOF
