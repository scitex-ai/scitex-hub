"""Repeated-task regression for the Celery PostgreSQL connection leak (issue #777).

MEASUREMENT NOTES — what this proves and what it does not.

  * Django's ``connections`` object is THREAD-LOCAL, so a test in one thread
    cannot count the backends held by worker threads by inspecting it. Where a
    process-wide number is needed, the test queries PostgreSQL's own
    ``pg_stat_activity``.
  * The leak's production shape was a count climbing ~1/minute from a LIVE
    ``--pool=threads`` worker. That exact growth is **not reproducible in this
    process**: Django REUSES a thread's connection, so a fixed set of N threads
    peaks at N backends whether or not the fix is present. What the fix changes
    is whether a task leaves its thread HOLDING that backend — which is what
    these tests assert, deterministically, and what the per-thread control
    measures. The server-side bound is asserted as a ceiling, and the honest
    limit is stated in the PR rather than papered over.
"""

from __future__ import annotations

import logging
import threading
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
    """PostgreSQL's view of how many backends serve this database."""
    with connections["default"].cursor() as cursor:
        cursor.execute(
            "SELECT count(*) FROM pg_stat_activity WHERE datname = current_database()"
        )
        return cursor.fetchone()[0]


def _connections_observed_per_task(
    *, use_handler: bool, thread_count: int
) -> list[int]:
    """Run a REAL thread pool and record, after every task, what that thread holds.

    Recorded from INSIDE each thread, because that is the only place the
    thread-local count is meaningful. The threads are kept alive for the whole
    run, which is what a pool does — so this measures the steady state rather
    than teardown behaviour.
    """
    observed: list[int] = []
    lock = threading.Lock()
    barrier = threading.Barrier(thread_count)

    def _worker() -> None:
        counts: list[int] = []
        try:
            barrier.wait()
            for _ in range(ROUNDS):
                _run_a_task_step()
                if use_handler:
                    lifecycle._close_connections_after_task(
                        sender=SimpleNamespace(name="tests.repeated_task")
                    )
                counts.append(lifecycle.open_connection_count())
        finally:
            # Never leak from the TEST itself.
            connections.close_all()
        with lock:
            observed.extend(counts)

    threads = [threading.Thread(target=_worker) for _ in range(thread_count)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    return observed


# ---------------------------------------------------------------------------
# Single task boundary — the fix, and its control.
# ---------------------------------------------------------------------------


@pytest.mark.django_db(transaction=True)
def test_a_finished_task_releases_the_thread_connection():
    """THE FIX: once the task ends, the thread holds no backend."""
    _run_a_task_step()
    assert lifecycle.open_connection_count() == 1, (
        "precondition: this thread should be holding a real backend"
    )

    lifecycle._close_connections_after_task(
        sender=SimpleNamespace(name="tests.single_task")
    )

    assert lifecycle.open_connection_count() == 0, (
        "the postrun handler left the thread's connection open — that is the "
        "leak: the next task on this thread reuses a backend that should have "
        "been returned"
    )


@pytest.mark.django_db
def test_without_the_handler_the_connection_stays_held():
    """CONTROL: the handler is what releases it, not the test harness."""
    _run_a_task_step()
    # deliberately no handler call
    assert lifecycle.open_connection_count() == 1, (
        "a task that reaches the database and is never closed must keep holding "
        "its backend; if this passes at 0 the test above proves nothing"
    )
    connections.close_all()


# ---------------------------------------------------------------------------
# Repeated tasks across a real thread pool — the actual outage shape.
# ---------------------------------------------------------------------------


@pytest.mark.django_db(transaction=True)
def test_every_task_leaves_its_thread_with_no_connection():
    """N tasks on a pool of threads: after EVERY task, that thread holds nothing.

    This is the repeated-task regression. A count that returns to zero after each
    task cannot climb; the outage was a count that only ever went up.
    """
    observed = _connections_observed_per_task(
        use_handler=True, thread_count=CONCURRENCY
    )

    assert len(observed) == TOTAL_TASKS, f"expected {TOTAL_TASKS} samples: {observed}"
    assert set(observed) == {0}, (
        f"after some tasks the thread still held a connection: {observed}. Every "
        "task must leave its thread holding nothing, or the pool accumulates one "
        "backend per thread and never gives them back (#777)."
    )


@pytest.mark.django_db(transaction=True)
def test_without_the_handler_a_thread_holds_its_connection_across_every_task():
    """CONTROL, and the proof the regression above can fail.

    The identical workload with the task-boundary handlers omitted must leave the
    thread holding its backend after EVERY task. Without this direction a handler
    that silently did nothing would let the bound above pass.
    """
    observed = _connections_observed_per_task(
        use_handler=False, thread_count=CONCURRENCY
    )

    assert set(observed) == {1}, (
        f"without the handlers each thread should hold exactly one backend "
        f"throughout, got {observed} — if these read 0 the measurement is not "
        "observing the thread that ran the task, and the regression proves nothing"
    )


@pytest.mark.django_db(transaction=True)
def test_repeated_tasks_do_not_grow_the_server_side_backend_count():
    """Server-side ceiling: growth is bounded by the POOL, not by the task count."""
    before = _server_side_backend_count()
    connections.close_all()

    _connections_observed_per_task(use_handler=True, thread_count=CONCURRENCY)

    after = _server_side_backend_count()
    connections.close_all()

    assert after <= before + CONCURRENCY, (
        f"{TOTAL_TASKS} task executions grew the database's backend count from "
        f"{before} to {after}; growth must be bounded by the pool size "
        f"({CONCURRENCY}), not by the number of tasks executed ({TOTAL_TASKS})."
    )


# ---------------------------------------------------------------------------
# Telemetry — the leak must be visible before headroom is exhausted.
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_telemetry_reports_the_open_connection_count(caplog):
    """Useful telemetry: every task boundary reports what this process holds."""
    _run_a_task_step()

    with caplog.at_level(logging.INFO, logger=lifecycle.__name__):
        observed = lifecycle.record_task_boundary(
            task_name="tests.telemetry", phase="postrun"
        )

    assert observed >= 1
    messages = [record.getMessage() for record in caplog.records]
    assert any(
        "phase=postrun" in message and "open_connections=" in message
        for message in messages
    ), f"no usable connection telemetry was emitted: {messages}"

    connections.close_all()


@pytest.mark.django_db
def test_telemetry_escalates_to_a_warning_past_the_threshold(caplog, monkeypatch):
    """Alerting, not just logging: crossing the threshold must be loud."""
    monkeypatch.setattr(lifecycle, "warn_threshold", lambda: 0)
    _run_a_task_step()

    with caplog.at_level(logging.INFO, logger=lifecycle.__name__):
        lifecycle.record_task_boundary(task_name="tests.loud", phase="postrun")

    assert any(record.levelno >= logging.WARNING for record in caplog.records), (
        "holding more connections than the configured threshold logged nothing at "
        "WARNING level, so exhaustion would arrive unannounced"
    )

    connections.close_all()
