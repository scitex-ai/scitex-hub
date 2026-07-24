#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Timestamp: 2026-02-04
# File: config/settings/settings_celery.py
"""Celery configuration for SciTeX Hub async task queue."""

import os

# Celery broker and result backend.
#
# The broker MUST be a DEDICATED redis DB, NOT the shared
# SCITEX_HUB_REDIS_URL (which the cache + channel layer also read).
# Reusing that shared var caused a silent producer/consumer DB mismatch:
# SCITEX_HUB_REDIS_URL was set to redis://redis:6379/0 for the cache, which
# moved the celery PRODUCER (this Django app, via .delay()) onto DB 0 --
# while the celery_worker / celery_beat containers consume DB 1 (their
# compose command hardcodes --broker=redis://redis:6379/1). Every enqueued
# task (visitor-slot re-clean resets, etc.) landed in DB 0 where nothing
# consumed it and piled up unrun (861 stranded on staging), leaving the
# whole visitor pool permanently quarantined. Pinning celery to its own
# DB 1 -- matching the worker/beat -- is what makes .delay() actually run.
# See incident hub-visitor-pool-celery-broker-db-mismatch (2026-07-11).
#
# Dedicated override var; default DB 1 matches the worker/beat --broker.
CELERY_BROKER_URL = os.getenv(
    "SCITEX_HUB_CELERY_BROKER_URL", "redis://redis:6379/1"
)
CELERY_RESULT_BACKEND = "django-db"
CELERY_CACHE_BACKEND = "django-cache"
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = "UTC"
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60  # 30 minutes max per task
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
    # Visitor-pool slot maintenance (reset_visitor_slot, initialize_visitor_workspace)
    # MUST run on the dedicated, near-empty vis_queue — NOT the default "celery"
    # queue. The default queue periodically accumulates a large backlog of expired
    # beat tasks (check_site_health / warm_public_status_cache / generate_status_charts,
    # ~40k deep in the 2026-07-11 incident). A boot-time `reconcile_visitor_slots
    # --async` re-clean enqueued behind that backlog never runs, so every idle slot
    # stays QUARANTINED and every visitor is downgraded to the read-only fallback —
    # the root cause of the pool-wide readonly outage. The worker already consumes
    # vis_queue (compose `--queues=...,vis_queue`), so routing here makes the async
    # re-clean process within seconds of boot regardless of default-queue depth.
    "apps.infra.project_app.tasks.visitor_workspace_tasks.*": {"queue": "vis_queue"},
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
#
# Expiry MUST be spelled "expire_seconds" here, NOT celery's producer-side
# "expires" keyword: beat runs django_celery_beat's DatabaseScheduler (see
# CELERY_BEAT_SCHEDULER above), whose ModelEntry._unpack_options() maps ONLY
# expire_seconds onto the seeded PeriodicTask row — an "expires" key falls
# into **kwargs and is SILENTLY DISCARDED, so every periodic message ships
# immortal. That exact spelling let the default queue backlog to 50,199
# messages on prod (~6,000 copies of each minute-ly task ≈ 4 days), which
# starved the queue-liveness beacon, tripped the container healthcheck and
# put autoheal into a restart loop. See incident
# hub-default-queue-immortal-beat-backlog (2026-07-21); regression gate:
# tests/apps/public_app/test_beat_schedule_expiry.py.
CELERY_BEAT_SCHEDULE = {
    # Clean up expired visitor allocations every 5 minutes
    "cleanup-expired-visitor-allocations": {
        "task": "apps.infra.public_app.tasks.cleanup_expired_visitor_allocations",
        "schedule": 300.0,  # Every 5 minutes (in seconds)
        "options": {
            "expire_seconds": 270,  # Expire after 4.5 minutes if not started
        },
    },
    # Generate server status charts every 1 minute
    "generate-status-charts": {
        "task": "apps.infra.public_app.tasks.generate_status_charts",
        "schedule": 60.0,  # Every 1 minute
        "options": {
            "expire_seconds": 55,  # Expire after 55 seconds if not started
        },
    },
    # Check site health every 1 minute and notify on failures
    "check-site-health": {
        "task": "apps.infra.public_app.tasks.check_site_health",
        "schedule": 60.0,  # Every 1 minute
        "options": {
            "expire_seconds": 55,  # Expire after 55 seconds if not started
        },
    },
    # Check for request flood patterns every 1 minute
    "check-request-flood": {
        "task": "apps.infra.public_app.tasks.check_request_flood",
        "schedule": 60.0,  # Every 1 minute
        "options": {
            "expire_seconds": 55,  # Expire after 55 seconds if not started
        },
    },
    # Warm /status page cache every 1 minute so user-facing visitors
    # never hit the ~17s cold path (scitex-orochi#82).
    "warm-public-status-cache": {
        "task": "apps.infra.public_app.tasks.warm_public_status_cache",
        "schedule": 60.0,  # Every 1 minute
        "options": {
            "expire_seconds": 55,
        },
    },
    # Collect server metrics every 1 minute. Owned HERE, by settings, not by
    # a hand-made PeriodicTask row: prod ran this minute-ly ONLY via an
    # unmanaged DB row that no settings file declared (SSoT violation
    # surfaced by the 2026-07-21 backlog incident). settings_dev.py
    # overrides the cadence to 10s for development.
    "collect-server-metrics": {
        "task": "apps.infra.public_app.tasks.collect_server_metrics",
        "schedule": 60.0,  # Every 1 minute
        "options": {
            "expire_seconds": 55,  # Expire after 55 seconds if not started
        },
    },
    # End-to-end queue-liveness beacons — the watchdog for wedged workers.
    #
    # Prod workers intermittently stop dispatching while every control-plane
    # probe stays green (measured 2026-07-14 / 2026-07-17: full `inspect
    # reserved` window with time_start=None, empty `inspect active`, redis
    # ping fine). Each beacon is routed ONTO the watched queue (`options.queue`
    # → PeriodicTask.queue via django_celery_beat) and stamps
    # `scitex:liveness:<queue>` at EXECUTION time; the container healthcheck
    # (deployment/docker/common/scripts/check_queue_liveness.sh) fails when
    # the stamp is missing or older than its budget (600s).
    #
    # Seeding: prod beat runs django_celery_beat's DatabaseScheduler, whose
    # setup_schedule() upserts every entry here into a PeriodicTask row by
    # name (update_or_create) at each beat boot — same idempotent mechanism
    # that seeds all the entries above; no data migration needed.
    #
    # Deliberately NO expiry (no expire_seconds), unlike the entries above:
    # a LATE beacon still proves the worker dispatches (it stamps execution
    # time), whereas expiring beacons on a merely-slow queue would silently
    # shrink the healthcheck's 600s budget to this 120s interval and restart
    # busy-but-healthy workers.
    "queue-liveness-beacon-celery": {
        "task": "apps.infra.public_app.tasks.queue_liveness_beacon",
        "schedule": 120.0,  # Every 2 minutes
        "args": ["celery"],
        "options": {"queue": "celery"},
    },
    "queue-liveness-beacon-vis-queue": {
        "task": "apps.infra.public_app.tasks.queue_liveness_beacon",
        "schedule": 120.0,  # Every 2 minutes
        "args": ["vis_queue"],
        "options": {"queue": "vis_queue"},
    },
}

# EOF
