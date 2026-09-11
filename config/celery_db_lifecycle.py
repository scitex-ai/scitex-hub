"""Close Django database connections at Celery task boundaries.

WHY THIS EXISTS (GitHub issue #777, launch-critical).
The dev worker runs ``--pool=threads --concurrency=4``. Django's connections are
THREAD-LOCAL, so every worker thread that touches the database acquires its own
PostgreSQL backend — and nothing was releasing them. Measured on compute-03:
worker-originated idle backends grew by roughly one per minute (2 -> 5 -> 7),
each with ``SELECT 1`` as its last query, until PostgreSQL reached
``max_connections=100`` and ``/auth/signup/`` started returning
``FATAL: sorry, too many clients already``.

``CONN_MAX_AGE=0`` IS NOT SUFFICIENT ON ITS OWN. That setting is enforced by the
request/response lifecycle (``close_old_connections()`` at the start and end of
each request), and **a Celery task is not a request**. The same calls therefore
have to be made at the TASK boundaries instead. With the threads pool the
cleanup must happen per TASK, not per worker process, because a long-lived
worker thread is exactly what accumulates the connection.

Raising ``max_connections`` is explicitly NOT the fix: it moves the ceiling and
leaves the leak in place.
"""

from __future__ import annotations

import logging
import os

from celery.signals import task_postrun, task_prerun, worker_process_init
from django.db import connections

logger = logging.getLogger(__name__)

# Warn once a single process is holding this many connections open. Defaults a
# little above the worker concurrency (4) plus the request threads, so a healthy
# process never warns but a growing one does so before headroom runs out.
_DEFAULT_WARN_THRESHOLD = 8


def warn_threshold() -> int:
    """Connection count at which telemetry escalates to a warning."""
    raw = os.environ.get("CELERY_DB_CONNECTION_WARN_THRESHOLD")
    try:
        return int(raw) if raw else _DEFAULT_WARN_THRESHOLD
    except (TypeError, ValueError):
        return _DEFAULT_WARN_THRESHOLD


def open_connection_count() -> int:
    """Live PostgreSQL backends held by THIS process, right now.

    Counts only aliases with an established connection — ``len(connections.all())``
    would count configured aliases whether or not they are connected, which never
    falls and so could never show the leak being fixed.
    """
    return sum(1 for conn in connections.all() if conn.connection is not None)


def record_task_boundary(*, task_name: str, phase: str) -> int:
    """Emit task-boundary telemetry and return the connection count observed.

    Useful on its own, and the single place the regression test measures through,
    so the test cannot pass while the telemetry it asserts on is fabricated
    somewhere else.
    """
    before = open_connection_count()
    level = logging.WARNING if before > warn_threshold() else logging.INFO
    logger.log(
        level,
        "celery.db phase=%s task=%s open_connections=%d warn_threshold=%d",
        phase,
        task_name,
        before,
        warn_threshold(),
    )
    return before


def task_connection_max_age() -> int:
    """How long a CELERY TASK may hold its DB connection; 0 means "every task".

    A Celery worker is not an HTTP request, so ``CONN_MAX_AGE`` is the wrong knob
    for it: that setting bounds a REQUEST's connection, and the request lifecycle
    is what enforces it. For a pool thread the connection simply lives as long as
    the thread does. The default here is therefore 0 — release after EVERY task —
    and a deployment that genuinely wants persistent task connections can raise
    ``CELERY_DB_CONN_MAX_AGE`` explicitly rather than inheriting the request
    policy by accident.
    """
    raw = os.environ.get("CELERY_DB_CONN_MAX_AGE")
    try:
        return int(raw) if raw else 0
    except (TypeError, ValueError):
        return 0


def release_thread_connections() -> int:
    """Return THIS thread's database connections to PostgreSQL; return how many closed.

    Why not just ``close_old_connections()`` — MEASURED, not reasoned. In this
    environment that call releases NOTHING. ``close_old_connections()`` delegates
    to ``close_if_unusable_or_obsolete()``, which closes a connection only when it
    has errors, has drifted from its autocommit setting, or has outlived
    ``CONN_MAX_AGE`` — and Django computes that deadline as
    ``close_at = time.monotonic() + CONN_MAX_AGE``. Measured here:
    ``CONN_MAX_AGE = 600``, so a healthy worker connection is never obsolete and
    the handler is a silent no-op that still looks like a fix. (Verified directly:
    after ``close_old_connections()`` the thread still held its backend, while an
    explicit ``conn.close()`` took the count 1 -> 0.)

    So the caller decides from ``CELERY_DB_CONN_MAX_AGE``:
      * 0 (default): CLOSE now — the pool thread returns the backend between tasks.
      * > 0: only drop a connection that died or aged out, keeping healthy ones.
    """
    closed = 0
    max_age = task_connection_max_age()
    for conn in connections.all():
        if conn.connection is None:
            continue
        if max_age > 0:
            conn.close_if_unusable_or_obsolete()
            if conn.connection is None:
                closed += 1
        else:
            conn.close()
            closed += 1
    return closed


@task_prerun.connect
def _close_stale_connections_before_task(sender=None, task_id=None, **kwargs):
    """Drop connections that died or aged out while the thread was idle.

    A thread can sit idle far longer than ``CONN_MAX_AGE``, so its connection may
    already be unusable by the time the next task arrives; Django raises from a
    dead connection unless it is checked first.
    """
    task_name = getattr(sender, "name", None) or "unknown"
    record_task_boundary(task_name=task_name, phase="prerun")
    release_thread_connections()


@task_postrun.connect
def _close_connections_after_task(sender=None, task_id=None, **kwargs):
    """RELEASE the thread's connection once the task is done.

    This is what stops the leak: without it the connection stays bound to the
    worker thread, so a long-lived pool thread keeps a PostgreSQL backend for the
    lifetime of the process instead of returning it between tasks.
    """
    task_name = getattr(sender, "name", None) or "unknown"
    before = record_task_boundary(task_name=task_name, phase="postrun")
    released = release_thread_connections()
    after = open_connection_count()
    if released:
        logger.debug(
            "celery.db released %d connection(s) after task=%s (%d -> %d)",
            released,
            task_name,
            before,
            after,
        )


@worker_process_init.connect
def _close_inherited_connections_on_worker_init(**kwargs):
    """A forked child inherits the parent's sockets; close them before use.

    With the threads pool this matters less than under prefork, but a child that
    inherits a live PostgreSQL socket and then also opens its own would count the
    same backend twice — and closing here keeps the pool switch from
    reintroducing the leak.
    """
    count = open_connection_count()
    if count:
        logger.info("celery.db worker init: closing %d inherited connection(s)", count)
    connections.close_all()
