"""Close Django database connections at Celery task boundaries.

WHY THIS EXISTS (GitHub issue #777, launch-critical).
The dev worker runs ``--pool=threads --concurrency=4``. Django's connections are
THREAD-LOCAL, so every worker thread that touches the database acquires its own
PostgreSQL backend — and nothing was releasing them. Measured on compute-03:
worker-originated idle backends grew by roughly one per minute (2 -> 5 -> 7),
each with ``SELECT 1`` as its last query, until PostgreSQL reached
``max_connections=100`` and ``/auth/signup/`` started returning
``FATAL: sorry, too many clients already``.

``CONN_MAX_AGE`` IS NOT SUFFICIENT ON ITS OWN. That setting is enforced by the
request/response lifecycle (``close_old_connections()`` at the start and end of
each request), and **a Celery task is not a request**. The same calls therefore
have to be made at the TASK boundaries instead. With the threads pool the cleanup
must happen per TASK, not per worker process, because a long-lived worker thread
is exactly what accumulates the connection.

Raising ``max_connections`` is explicitly NOT the fix: it moves the ceiling and
leaves the leak in place.

TWO DIFFERENT NUMBERS, NAMED SO THEY CANNOT BE CONFUSED.
Django's ``connections`` object is THREAD-LOCAL. Counting it tells you what THIS
THREAD holds and NOTHING about the process or the server, so a field called
"process connections" backed by it is actively misleading — it reads ~1 forever
while the server is refusing clients. This module therefore exposes both, under
names that say which is which:

  * ``thread_connection_count()`` — cheap, thread-local, what the task boundary
    can act on;
  * ``process_connection_count()`` — authoritative, read from PostgreSQL's own
    ``pg_stat_activity``. It costs a query, so it is logged only when the thread
    count suggests something is wrong, rather than on every task.
"""

from __future__ import annotations

import logging
import os
import time

from celery.signals import task_postrun, task_prerun, worker_process_init
from django.db import close_old_connections, connections
from django.db.backends.signals import connection_created

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


def task_connection_max_age() -> int:
    """How long a CELERY TASK may hold its DB connection; 0 means "every task".

    A Celery worker is not an HTTP request, so ``CONN_MAX_AGE`` is the wrong knob
    for it: that setting bounds a REQUEST's connection, and the request lifecycle
    is what enforces it. For a pool thread the connection simply lives as long as
    the thread does. The default here is therefore 0 — release after EVERY task —
    and a deployment that genuinely wants persistent task connections can raise
    ``CELERY_DB_CONN_MAX_AGE``.
    """
    raw = os.environ.get("CELERY_DB_CONN_MAX_AGE")
    try:
        return int(raw) if raw else 0
    except (TypeError, ValueError):
        return 0


def thread_connection_count() -> int:
    """Connections held by THIS THREAD right now.

    Deliberately named for what it measures. ``connections.all()`` is thread-local,
    so this is NOT a process or server count; see ``process_connection_count()``.
    Only aliases with an established connection are counted — counting configured
    aliases would never fall and so could never show the leak being fixed.
    """
    return sum(1 for conn in connections.all() if conn.connection is not None)


def process_connection_count() -> int | None:
    """Backends serving this database SERVER-SIDE, or None if it could not be read.

    Authoritative and not thread-local: it is PostgreSQL's own view, so it sees
    every worker thread and every other process. Returns None rather than raising,
    because telemetry must never be the reason a task fails.
    """
    try:
        with connections["default"].cursor() as cursor:
            cursor.execute(
                "SELECT count(*) FROM pg_stat_activity WHERE datname = current_database()"
            )
            row = cursor.fetchone()
            return int(row[0]) if row else None
    except Exception:  # noqa: BLE001 — telemetry must not break the task
        logger.debug("celery.db could not read process connection count", exc_info=True)
        return None


def _connection_age_seconds(conn) -> float | None:
    """How long this thread's connection has been open, if we can tell.

    Our OWN stamp is preferred, recorded when the connection was created. Django
    does not store a connect time, and its deadline is derived from the
    request-oriented ``CONN_MAX_AGE`` — including being ``None`` when that setting
    is ``None``, which would make a CELERY age unevaluable. Deriving from
    ``close_at`` is kept only as a fallback for connections created before this
    module was imported.
    """
    stamped = getattr(conn, "_celery_created_at", None)
    if stamped is not None:
        return time.monotonic() - stamped

    close_at = getattr(conn, "close_at", None)
    django_max_age = conn.settings_dict.get("CONN_MAX_AGE")
    if close_at is None or django_max_age is None:
        return None
    return time.monotonic() - (close_at - django_max_age)


@connection_created.connect
def _stamp_new_connection(sender=None, connection=None, **kwargs):
    """Record when a connection was established, so a CELERY age can be applied.

    Without this the age of a connection is unknowable in the configurations where
    it matters most, and a configured ``CELERY_DB_CONN_MAX_AGE`` silently degrades
    into "keep it" — the failure this module exists to prevent.
    """
    if connection is not None:
        connection._celery_created_at = time.monotonic()


def _released(conn) -> bool:
    """Did ``close()`` actually release this connection?

    NOT simply ``conn.connection is None``. Inside an ATOMIC BLOCK Django's
    ``close()`` runs ``_close()`` and then sets ``closed_in_transaction = True``
    while deliberately LEAVING ``connection`` non-None, so the socket is gone but
    the attribute is not. Counting only the attribute reports "released nothing"
    for a close that worked — which is exactly the kind of number that makes a
    regression look vacuous in one direction and lie in the other.
    """
    return conn.connection is None or getattr(conn, "closed_in_transaction", False)


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

    ``CELERY_DB_CONN_MAX_AGE`` is applied HERE rather than delegated, because
    ``close_if_unusable_or_obsolete()`` measures against ``CONN_MAX_AGE``: with
    the default 600 a configured ``CELERY_DB_CONN_MAX_AGE=30`` would have had no
    effect at all — the connection would still be held for 600 seconds — so a
    non-zero setting would have looked honoured while changing nothing.
    """
    closed = 0
    max_age = task_connection_max_age()
    for conn in connections.all():
        if conn.connection is None:
            continue
        if max_age > 0:
            age = _connection_age_seconds(conn)
            if age is None:
                # Django is not tracking an age for this connection AND we have no
                # stamp, so ours cannot be evaluated; fall back to the
                # unusable-and-obsolete check rather than closing a connection we
                # may be told to keep.
                conn.close_if_unusable_or_obsolete()
            elif age >= max_age:
                conn.close()
        else:
            conn.close()
        if _released(conn):
            closed += 1
            # Drop our stamp so a reused wrapper starts its next connection fresh
            # rather than inheriting the age of the one just released.
            if hasattr(conn, "_celery_created_at"):
                del conn._celery_created_at
    return closed


def record_task_boundary(*, task_name: str, phase: str) -> int:
    """Emit task-boundary telemetry and return the THREAD-local count observed.

    The thread count is always logged (it is free). The PROCESS count costs a
    query, so it is read only when the thread count has already crossed the
    threshold — which is exactly when an operator needs to know whether the server
    is filling up or the thread is simply busy.
    """
    in_thread = thread_connection_count()
    threshold = warn_threshold()
    if in_thread > threshold:
        logger.warning(
            "celery.db phase=%s task=%s thread_connections=%d threshold=%d "
            "server_connections=%s",
            phase,
            task_name,
            in_thread,
            threshold,
            process_connection_count(),
        )
    else:
        logger.info(
            "celery.db phase=%s task=%s thread_connections=%d threshold=%d",
            phase,
            task_name,
            in_thread,
            threshold,
        )
    return in_thread


@task_prerun.connect
def _close_stale_connections_before_task(sender=None, task_id=None, **kwargs):
    """Drop connections that died or aged out while the thread was idle.

    A thread can sit idle far longer than ``CONN_MAX_AGE``, so its connection may
    already be unusable by the time the next task arrives; Django raises from a
    dead connection unless it is checked first.
    """
    task_name = getattr(sender, "name", None) or "unknown"
    record_task_boundary(task_name=task_name, phase="prerun")
    close_old_connections()


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
    if released:
        logger.debug(
            "celery.db released %d connection(s) after task=%s (%d -> %d)",
            released,
            task_name,
            before,
            thread_connection_count(),
        )


@worker_process_init.connect
def _close_inherited_connections_on_worker_init(**kwargs):
    """A forked child inherits the parent's sockets; close them before use.

    With the threads pool this matters less than under prefork, but a child that
    inherits a live PostgreSQL socket and then also opens its own would count the
    same backend twice — and closing here keeps the pool switch from
    reintroducing the leak.
    """
    count = thread_connection_count()
    if count:
        logger.info("celery.db worker init: closing %d inherited connection(s)", count)
    connections.close_all()
