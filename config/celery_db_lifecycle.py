"""Close Django database connections at Celery task boundaries.

WHY THIS EXISTS (GitHub issue #777, launch-critical).
The dev worker runs ``--pool=threads --concurrency=4``. Django's connections are
THREAD-LOCAL, so every worker thread that touches the database acquires its own
PostgreSQL backend — and nothing was releasing them. Measured on compute-03:
worker-originated idle backends grew (2 -> 5 -> 7), each with ``SELECT 1`` as its
last query, until PostgreSQL reached ``max_connections=100`` and ``/auth/signup/``
started returning ``FATAL: sorry, too many clients already``.

``CONN_MAX_AGE`` IS NOT SUFFICIENT ON ITS OWN. That setting is enforced by the
request/response lifecycle, and **a Celery task is not a request**. With the
threads pool the cleanup must happen per TASK, not per worker process.

Raising ``max_connections`` is explicitly NOT the fix: it moves the ceiling and
leaves the leak.

TWO NUMBERS, AND NEITHER IS CALLED A "PROCESS" COUNT ANY MORE.
Django's ``connections`` object is THREAD-LOCAL, so counting it says what THIS
THREAD holds and nothing about anything else. A field called "process
connections" backed by it reads ~1 forever while the server refuses clients. And
the database-wide number is not this process's either — it counts every backend
serving the database, including other containers:

  * ``thread_connection_count()`` — cheap, thread-local, what a boundary can act on;
  * ``database_connection_count()`` — the whole DATABASE, from ``pg_stat_activity``.
    It costs a query, and it is now read on EVERY boundary rather than only when
    the thread count looked wrong: gating it on the thread-local number meant the
    real leak — many threads, each holding one — was exactly the case that
    suppressed the telemetry meant to reveal it.
"""

from __future__ import annotations

import logging
import os
import time

from celery.signals import task_postrun, task_prerun, worker_process_init
from django.db import close_old_connections, connections
from django.db.backends.signals import connection_created

logger = logging.getLogger(__name__)

# Warn once the DATABASE is serving this many backends. Defaults a little above the
# worker concurrency (4) plus the request threads, so a healthy deployment never
# warns but a growing one does so before headroom runs out.
_DEFAULT_WARN_THRESHOLD = 8


def warn_threshold() -> int:
    """Database backend count at which telemetry escalates to a warning."""
    raw = os.environ.get("CELERY_DB_CONNECTION_WARN_THRESHOLD")
    try:
        return int(raw) if raw else _DEFAULT_WARN_THRESHOLD
    except (TypeError, ValueError):
        return _DEFAULT_WARN_THRESHOLD


def task_connection_max_age() -> int:
    """How long a CELERY TASK may hold its DB connection; 0 means "every task"."""
    raw = os.environ.get("CELERY_DB_CONN_MAX_AGE")
    try:
        return int(raw) if raw else 0
    except (TypeError, ValueError):
        return 0


def thread_connection_count() -> int:
    """Connections held by THIS THREAD right now.

    ``connections.all()`` is thread-local, so this is NOT a database or process
    count; see ``database_connection_count()``. Only aliases with an established
    connection are counted — counting configured aliases would never fall and could
    never show the leak being fixed.
    """
    return sum(1 for conn in connections.all() if conn.connection is not None)


def database_connection_count() -> int | None:
    """Backends serving this DATABASE, from PostgreSQL's own view.

    Not thread-local and not per-process: it counts every backend on the database,
    including other containers. Returns None rather than raising, because telemetry
    must never be the reason a task fails.
    """
    try:
        with connections["default"].cursor() as cursor:
            cursor.execute(
                "SELECT count(*) FROM pg_stat_activity WHERE datname = current_database()"
            )
            row = cursor.fetchone()
            return int(row[0]) if row else None
    except Exception:  # noqa: BLE001 — telemetry must not break the task
        logger.debug("celery.db could not read the database count", exc_info=True)
        return None


def _stamp_new_connection(sender=None, connection=None, **kwargs):
    """Record when a connection was established, so a CELERY age can be applied.

    Without a stamp the age of a connection is unknowable in the configurations
    that matter most — Django's ``close_at`` is derived from the request-oriented
    ``CONN_MAX_AGE`` and is simply ``None`` when that setting is ``None`` — so a
    configured ``CELERY_DB_CONN_MAX_AGE`` silently degrades into "keep it".
    """
    if connection is not None:
        connection._celery_created_at = time.monotonic()


# STRONGLY RETAINED, deliberately. Django's ``connect()`` stores a WEAK reference
# by default, so a receiver can be garbage-collected and silently stop firing —
# a leak fix that stops working without failing anything. ``weak=False`` plus an
# explicit ``dispatch_uid`` keeps exactly one strong registration even if this
# module is imported or reloaded more than once.
connection_created.connect(
    _stamp_new_connection,
    weak=False,
    dispatch_uid="celery_db_lifecycle.stamp_new_connection",
)


def _connection_age_seconds(conn) -> float:
    """Age of this thread's connection in seconds.

    The stamp is authoritative. Where it is missing — a connection established
    before this module was imported, or one whose receiver was not yet attached —
    the connection is stamped NOW and reported as age 0, rather than falling back
    to Django's ``close_if_unusable_or_obsolete()``. That fallback measures
    ``CONN_MAX_AGE``, which is ``None`` in some configurations and never expires a
    healthy connection in any of them, so delegating to it made a non-zero
    ``CELERY_DB_CONN_MAX_AGE`` a no-op precisely where it was configured.
    """
    stamped = getattr(conn, "_celery_created_at", None)
    if stamped is None:
        conn._celery_created_at = time.monotonic()
        return 0.0
    return time.monotonic() - stamped


def release_thread_connections() -> int:
    """Return THIS thread's database connections to PostgreSQL; return how many closed.

    Why not just ``close_old_connections()`` — MEASURED, not reasoned. In this
    environment that call releases NOTHING: it delegates to
    ``close_if_unusable_or_obsolete()``, which closes a connection only when it has
    errors, has drifted from its autocommit setting, or has outlived
    ``CONN_MAX_AGE`` — and Django computes that deadline as
    ``close_at = time.monotonic() + CONN_MAX_AGE``. Measured here:
    ``CONN_MAX_AGE = 600``, so a healthy worker connection is never obsolete and
    the handler is a silent no-op that still looks like a fix. (Verified directly:
    after ``close_old_connections()`` the thread still held its backend, while an
    explicit ``conn.close()`` took the count 1 -> 0.)

    ``CELERY_DB_CONN_MAX_AGE`` is therefore applied HERE against our own stamp.
    """
    closed = 0
    max_age = task_connection_max_age()
    for conn in connections.all():
        if conn.connection is None:
            continue
        if max_age > 0:
            if _connection_age_seconds(conn) >= max_age:
                conn.close()
        else:
            conn.close()
        if _released(conn):
            closed += 1
            # Drop the stamp so a reused wrapper starts its next connection fresh
            # rather than inheriting the age of the one just released.
            if hasattr(conn, "_celery_created_at"):
                del conn._celery_created_at
    return closed


def _released(conn) -> bool:
    """Did ``close()`` actually release this connection?

    NOT simply ``conn.connection is None``. Inside an ATOMIC BLOCK Django's
    ``close()`` runs ``_close()`` and then sets ``closed_in_transaction = True``
    while deliberately LEAVING ``connection`` non-None, so the socket is gone but
    the attribute is not. Counting only the attribute reports "released nothing"
    for a close that worked.
    """
    return conn.connection is None or getattr(conn, "closed_in_transaction", False)


def record_task_boundary(*, task_name: str, phase: str) -> int:
    """Emit task-boundary telemetry; return the THREAD-local count observed.

    The DATABASE count is read and logged on EVERY boundary. Gating it on the
    thread-local number was wrong: the live leak is many threads each holding one,
    so no single thread ever crosses the threshold, and the expensive reading was
    suppressed in exactly the situation it existed to expose.
    """
    in_thread = thread_connection_count()
    on_database = database_connection_count()
    threshold = warn_threshold()
    escalate = on_database is not None and on_database > threshold
    logger.log(
        logging.WARNING if escalate else logging.INFO,
        "celery.db phase=%s task=%s thread_connections=%d database_connections=%s "
        "threshold=%d",
        phase,
        task_name,
        in_thread,
        on_database,
        threshold,
    )
    return in_thread


def _close_stale_connections_before_task(sender=None, task_id=None, **kwargs):
    """Drop connections that died or aged out while the thread was idle."""
    task_name = getattr(sender, "name", None) or "unknown"
    record_task_boundary(task_name=task_name, phase="prerun")
    close_old_connections()


def _close_connections_after_task(sender=None, task_id=None, **kwargs):
    """RELEASE the thread's connection once the task is done.

    This is what stops the leak: without it the connection stays bound to the
    worker thread, so a long-lived pool thread keeps a PostgreSQL backend for the
    lifetime of the process instead of returning it between tasks.
    """
    task_name = getattr(sender, "name", None) or "unknown"
    before = record_task_boundary(task_name=task_name, phase="postrun")
    released = release_thread_connections()
    if released:
        logger.debug(
            "celery.db released %d connection(s) after task=%s (%d -> %d)",
            released,
            task_name,
            before,
            thread_connection_count(),
        )


def _close_inherited_connections_on_worker_init(**kwargs):
    """A forked child inherits the parent's sockets; close them before use."""
    count = thread_connection_count()
    if count:
        logger.info("celery.db worker init: closing %d inherited connection(s)", count)
    connections.close_all()


# EVERY receiver is registered with `weak=False` and a `dispatch_uid`, deliberately.
# Signal `connect()` stores a WEAK reference by default, so a receiver can be
# garbage-collected and silently stop firing — a leak fix that stops working
# without failing anything, which is the worst possible failure mode for this one.
# The uid keeps the registration unique even if this module is imported twice.
task_prerun.connect(
    _close_stale_connections_before_task,
    weak=False,
    dispatch_uid="celery_db_lifecycle.close_before_task",
)
task_postrun.connect(
    _close_connections_after_task,
    weak=False,
    dispatch_uid="celery_db_lifecycle.close_after_task",
)
worker_process_init.connect(
    _close_inherited_connections_on_worker_init,
    weak=False,
    dispatch_uid="celery_db_lifecycle.close_on_worker_init",
)
