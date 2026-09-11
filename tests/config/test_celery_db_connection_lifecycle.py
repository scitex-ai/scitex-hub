"""Regression for the Celery PostgreSQL connection leak (issue #777).

MEASUREMENT NOTES — what each test proves, and what it cannot.

Django's ``connections`` object is THREAD-LOCAL, so a test in one thread cannot
count the backends held by worker threads by inspecting it. Any claim about the
SERVER is therefore made against PostgreSQL's own ``pg_stat_activity``.

Django also REUSES a thread's connection, so a fixed set of N threads peaks at N
backends whether or not the fix is present. That is why the server-side tests do
not simply run a pool and count afterwards — such a test passes trivially and
cannot fail, which is worse than no test. They keep the pool ALIVE while
measuring, so an unreleased connection is actually observable, and they pair a
control that MUST show the leak with the case that must not.
"""

from __future__ import annotations

import logging
import threading
import time
from types import SimpleNamespace

import pytest
from django.db import connections

from config import celery_db_lifecycle as lifecycle

CONCURRENCY = 4
ROUNDS = 4
TOTAL_TASKS = CONCURRENCY * ROUNDS


def _run_a_task_step() -> None:
    """One task execution as far as the database is concerned: acquire, use, done."""
    with connections["default"].cursor() as cursor:
        cursor.execute("SELECT 1")
        cursor.fetchone()


def _server_side_backend_count() -> int:
    """PostgreSQL's view of how many backends serve this database.

    Read with this thread's connections CLOSED first, so the query's own backend
    is the same +1 in every measurement and cancels out of the comparison.
    """
    connections.close_all()
    with connections["default"].cursor() as cursor:
        cursor.execute(
            "SELECT count(*) FROM pg_stat_activity WHERE datname = current_database()"
        )
        return cursor.fetchone()[0]


def _hold_a_pool_alive(*, use_handler: bool):
    """Run a REAL pool that stays alive until told to stop.

    Threads run ``ROUNDS`` tasks each, then PARK. While they are parked, whatever
    they are still holding is genuinely held — which is the state the production
    leak lived in and the only state in which it can be measured. Returns
    (measure, release).
    """
    parked = threading.Barrier(CONCURRENCY + 1)
    release = threading.Event()

    def _worker() -> None:
        try:
            for _ in range(ROUNDS):
                _run_a_task_step()
                if use_handler:
                    lifecycle._close_connections_after_task(
                        sender=SimpleNamespace(name="tests.pooled_task")
                    )
            parked.wait(timeout=30)
            release.wait(timeout=30)
        finally:
            # Never leak from the TEST itself.
            connections.close_all()

    threads = [threading.Thread(target=_worker) for _ in range(CONCURRENCY)]
    for thread in threads:
        thread.start()

    def measure() -> int:
        parked.wait(timeout=30)  # every thread has finished its tasks and parked
        return _server_side_backend_count()

    def stop() -> None:
        release.set()
        for thread in threads:
            thread.join(timeout=30)

    return measure, stop


# ---------------------------------------------------------------------------
# Single task boundary — the fix, and its control.
# ---------------------------------------------------------------------------


@pytest.mark.django_db(transaction=True)
def test_a_finished_task_releases_the_thread_connection():
    """THE FIX: once the task ends, the thread holds no backend."""
    _run_a_task_step()
    assert lifecycle.thread_connection_count() == 1, (
        "precondition: this thread should be holding a real backend"
    )

    lifecycle._close_connections_after_task(
        sender=SimpleNamespace(name="tests.single_task")
    )

    assert lifecycle.thread_connection_count() == 0, (
        "the postrun handler left the thread's connection open — that is the "
        "leak: the next task on this thread reuses a backend that should have "
        "been returned"
    )


@pytest.mark.django_db
def test_without_the_handler_the_connection_stays_held():
    """CONTROL: the handler is what releases it, not the test harness."""
    _run_a_task_step()
    # deliberately no handler call
    assert lifecycle.thread_connection_count() == 1, (
        "a task that reaches the database and is never closed must keep holding "
        "its backend; if this passes at 0 the test above proves nothing"
    )
    connections.close_all()


# ---------------------------------------------------------------------------
# Non-zero CELERY_DB_CONN_MAX_AGE must actually be applied.
# ---------------------------------------------------------------------------


@pytest.mark.django_db(transaction=True)
def test_a_task_age_shorter_than_conn_max_age_is_honoured(monkeypatch):
    """THE BUG THIS PINS: the age check must use OUR setting, not Django's.

    ``close_if_unusable_or_obsolete()`` measures against ``CONN_MAX_AGE`` (600
    here). A connection younger than 600s therefore survived a
    ``CELERY_DB_CONN_MAX_AGE`` that asked for it to be dropped — a configured
    value that looked honoured and changed nothing. With the age applied
    directly, a 1-second budget releases a connection older than 1 second.
    """
    monkeypatch.setenv("CELERY_DB_CONN_MAX_AGE", "1")
    _run_a_task_step()
    time.sleep(1.2)

    released = lifecycle.release_thread_connections()

    assert released == 1, (
        "a connection older than CELERY_DB_CONN_MAX_AGE was kept, so the age is "
        "being evaluated against CONN_MAX_AGE instead of the Celery setting"
    )
    connections.close_all()


@pytest.mark.django_db(transaction=True)
def test_a_task_age_longer_than_the_connection_age_keeps_it(monkeypatch):
    """CONTROL the other way: a connection younger than the budget is KEPT.

    Without this, an unconditional ``conn.close()`` would satisfy the test above
    while silently defeating persistent task connections for anyone who
    configures them.
    """
    monkeypatch.setenv("CELERY_DB_CONN_MAX_AGE", "3600")
    _run_a_task_step()

    released = lifecycle.release_thread_connections()

    assert released == 0, (
        "a fresh connection was released despite a 3600s task budget, so "
        "CELERY_DB_CONN_MAX_AGE is not being honoured in this direction"
    )
    assert lifecycle.thread_connection_count() == 1
    connections.close_all()


@pytest.mark.django_db(transaction=True)
def test_zero_task_age_releases_every_task(monkeypatch):
    """The default: 0 means release after every task."""
    monkeypatch.delenv("CELERY_DB_CONN_MAX_AGE", raising=False)
    _run_a_task_step()

    assert lifecycle.release_thread_connections() == 1
    assert lifecycle.thread_connection_count() == 0


# ---------------------------------------------------------------------------
# Repeated tasks over a live pool — measured SERVER-SIDE, both directions.
# ---------------------------------------------------------------------------


@pytest.mark.django_db(transaction=True)
def test_a_pool_that_releases_does_not_grow_the_server_side_count():
    """THE FIX, measured where the leak actually showed up."""
    before = _server_side_backend_count()
    measure, stop = _hold_a_pool_alive(use_handler=True)
    try:
        after = measure()
    finally:
        stop()

    assert after <= before + 1, (
        f"{TOTAL_TASKS} task executions across a parked {CONCURRENCY}-thread pool "
        f"left the database serving {after - before} extra backend(s) (before="
        f"{before}, after={after}). Each task must return its backend, so a parked "
        "pool should hold none."
    )


@pytest.mark.django_db(transaction=True)
def test_a_pool_that_never_releases_IS_grown_and_so_the_measurement_can_fail():
    """CONTROL — and the reason the test above is not vacuous.

    The same parked pool WITHOUT the handler must show the leak. An earlier
    version of this file closed every thread's connections in a ``finally`` in
    both arms, which made the server-side assertion unfalsifiable: it would pass
    whether or not the fix existed. This arm is what stops that happening again.
    """
    before = _server_side_backend_count()
    measure, stop = _hold_a_pool_alive(use_handler=False)
    try:
        after = measure()
    finally:
        stop()

    assert after >= before + CONCURRENCY, (
        f"a parked pool that never released only moved the backend count from "
        f"{before} to {after}; each parked thread should still hold one, so this "
        "measurement cannot see the leak at all and the fixed-path assertion "
        "above proves nothing"
    )


# ---------------------------------------------------------------------------
# Telemetry — and the two numbers must not be confused.
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_telemetry_reports_the_THREAD_count_by_name(caplog):
    """The cheap number is reported as a THREAD count, not a process count."""
    _run_a_task_step()

    with caplog.at_level(logging.INFO, logger=lifecycle.__name__):
        observed = lifecycle.record_task_boundary(
            task_name="tests.telemetry", phase="postrun"
        )

    assert observed >= 1
    messages = [record.getMessage() for record in caplog.records]
    assert any(
        "phase=postrun" in message and "thread_connections=" in message
        for message in messages
    ), f"no usable thread-scoped telemetry was emitted: {messages}"
    assert not any("open_connections=" in message for message in messages), (
        "telemetry still labels a thread-local count as if it were process-wide"
    )

    connections.close_all()


@pytest.mark.django_db
def test_the_process_count_is_authoritative_and_not_thread_local():
    """CONTROL for the distinction: the server count sees the whole database.

    A thread-local count can only ever report this thread's one connection, so if
    the two numbers agree the "process" figure is not measuring what it claims.
    """
    _run_a_task_step()
    in_thread = lifecycle.thread_connection_count()

    server_side = lifecycle.process_connection_count()

    assert server_side is not None, "the authoritative count could not be read"
    assert server_side >= in_thread, (
        f"server-side count ({server_side}) is below this thread's own count "
        f"({in_thread}), so it is not a server-wide measurement"
    )
    connections.close_all()


@pytest.mark.django_db
def test_telemetry_escalates_and_only_then_pays_for_the_server_query(
    caplog, monkeypatch
):
    """Alerting is loud, and the expensive number is fetched only when it matters."""
    monkeypatch.setattr(lifecycle, "warn_threshold", lambda: 0)
    called = {"n": 0}
    real = lifecycle.process_connection_count

    def _spy():
        called["n"] += 1
        return real()

    monkeypatch.setattr(lifecycle, "process_connection_count", _spy)
    _run_a_task_step()

    with caplog.at_level(logging.INFO, logger=lifecycle.__name__):
        lifecycle.record_task_boundary(task_name="tests.loud", phase="postrun")

    assert any(record.levelno >= logging.WARNING for record in caplog.records), (
        "holding more connections than the configured threshold logged nothing at "
        "WARNING level, so exhaustion would arrive unannounced"
    )
    assert called["n"] == 1, (
        "the server-side count was not read when the threshold was crossed, so the "
        "warning cannot say whether the server is filling up"
    )
    connections.close_all()


@pytest.mark.django_db
def test_the_server_query_is_not_paid_for_when_nothing_is_wrong(caplog, monkeypatch):
    """CONTROL: below the threshold, telemetry stays free."""
    called = {"n": 0}

    def _spy():
        called["n"] += 1
        return 0

    monkeypatch.setattr(lifecycle, "process_connection_count", _spy)
    _run_a_task_step()

    with caplog.at_level(logging.INFO, logger=lifecycle.__name__):
        lifecycle.record_task_boundary(task_name="tests.quiet", phase="postrun")

    assert called["n"] == 0, (
        "a healthy task boundary paid for a server-side query on every task"
    )
    connections.close_all()
