#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""End-to-end queue-liveness beacon.

WHY (measured on prod, 2026-07-14 and again 2026-07-17): the celery
workers intermittently stop dispatching — ``inspect reserved`` shows a
full prefetch window (``time_start=None``, ``worker_pid=None``),
``inspect active`` is empty, the fork children idle, and the control
channel still answers. In that state the old container healthcheck (a
plain redis ping) stays green forever while the queue silently stops
draining — for ``vis_queue`` that means the visitor-slot re-clean never
runs and the pool cannot self-heal.

The beacon closes that gap end-to-end: celery beat enqueues
``queue_liveness_beacon(<queue>)`` ONTO the watched queue every 120s,
and the task stamps ``scitex:liveness:<queue>`` in the broker redis at
EXECUTION time. A stamp can only be fresh if the whole chain works:
beat scheduled it, the broker carried it, and the worker actually
dispatched and ran it. ``check_queue_liveness.sh`` (the container
healthcheck) compares the stamp's age against a budget and fails LOUD
when it is missing or stale — catching any wedge variant, not just the
one measured.

Contract: ``queue_name`` names the queue this beacon CLAIMS to prove
alive, so the dispatcher MUST route the task onto that same queue.
The ``CELERY_BEAT_SCHEDULE`` entries in
``config/settings/settings_celery.py`` do this via
``options={"queue": ...}`` (which django_celery_beat upserts into
``PeriodicTask.queue``). Never ``.delay()`` this task manually with a
mismatched queue — the stamp would vouch for a queue that never
carried it.
"""

from __future__ import annotations

import logging
import time

import redis
from celery import shared_task
from django.conf import settings

logger = logging.getLogger(__name__)

# Key prefix shared with deployment/docker/common/scripts/
# check_queue_liveness.sh — change them together or the healthcheck
# reads a key nobody writes (= permanently unhealthy, loudly).
LIVENESS_KEY_PREFIX = "scitex:liveness:"


def liveness_key(queue_name: str) -> str:
    """Return the redis key carrying the liveness stamp for ``queue_name``.

    Raises ``ValueError`` on a blank name: a beacon stamping
    ``scitex:liveness:`` would vouch for no queue at all, so refuse
    loudly instead of writing garbage.
    """
    if not queue_name or not queue_name.strip():
        raise ValueError(
            "queue_name must be a non-empty queue name "
            f"(got {queue_name!r}); refusing to write a liveness stamp "
            "that vouches for no queue"
        )
    return f"{LIVENESS_KEY_PREFIX}{queue_name}"


def write_liveness_stamp(client, queue_name: str, timestamp: float) -> str:
    """Write ``timestamp`` to ``queue_name``'s liveness key; return the key.

    Pure core of the beacon, with the redis client injected so it is
    testable against a hand-rolled fake (repo policy: no mock
    libraries). ``client`` needs only ``.set(key, value)`` —
    ``redis.Redis`` in production.

    No TTL on the key: a missing key must mean "never executed here",
    never "expired quietly". Errors propagate: if redis is unreachable
    the beacon fails loudly and the stamp goes stale — redis being down
    IS an unhealthy worker.
    """
    key = liveness_key(queue_name)
    client.set(key, timestamp)
    return key


@shared_task(
    name="apps.infra.public_app.tasks.queue_liveness_beacon",
    ignore_result=True,
    soft_time_limit=10,
    time_limit=20,
)
def queue_liveness_beacon(queue_name: str) -> dict:
    """Stamp ``scitex:liveness:<queue_name>`` with the current time.

    Runs on the watched queue itself (see module docstring). The stamp
    is written at EXECUTION time — a late run still proves the worker
    is dispatching, which is exactly the property the healthcheck
    measures.

    Writes to the CELERY BROKER redis DB (``settings.CELERY_BROKER_URL``,
    prod: ``redis://redis:6379/1``) so the reader
    (``check_queue_liveness.sh``) shares one connection contract with
    the queue it is judging.
    """
    timestamp = time.time()
    client = redis.Redis.from_url(
        settings.CELERY_BROKER_URL,
        socket_connect_timeout=5,
        socket_timeout=5,
    )
    key = write_liveness_stamp(client, queue_name, timestamp)
    logger.debug("[QueueLiveness] stamped %s = %s", key, timestamp)
    return {"queue": queue_name, "timestamp": timestamp}


# EOF
