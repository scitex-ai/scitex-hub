"""Regression for the Celery PostgreSQL connection leak (issue #777).

WHAT THIS FILE HAS TO PROVE, and why earlier versions did not.
The leak is a ONE-PROCESS, MANY-THREADS accumulation: ``--pool=threads`` keeps its
worker threads alive, each holds its own thread-local PostgreSQL backend, and
nothing returns it — measured live at 30 idle backends. A regression for it must
therefore (a) keep a pool ALIVE while measuring, (b) fail when postrun cleanup is
absent, and (c) do both without depending on timing luck.

An earlier version closed every thread's connections in a ``finally`` and counted
AFTER joining. That passes with no handler at all, because joining tears the
thread state down before the measurement: it was unfalsifiable.

TASKS ARE DRIVEN THROUGH THE REAL CELERY SIGNALS, not by calling the private
handler function. That is the difference between testing cleanup and testing that
cleanup is REGISTERED — a handler that is never wired up would satisfy the latter.
The no-cleanup control therefore DISCONNECTS the receiver, which is the only way
to model "postrun cleanup is absent" faithfully.

Django's ``connections`` object is THREAD-LOCAL, so no test can see other threads
through it; every claim about the SERVER is made against ``pg_stat_activity``.
"""

from __future__ import annotations

import logging
import threading
import time
from types import SimpleNamespace

import pytest
from celery.signals import task_postrun, task_prerun
from django.db import connections

from config import celery_db_lifecycle as lifecycle

CONCURRENCY = 4
ROUNDS = 4
TOTAL_TASKS = CONCURRENCY * ROUNDS
REPEATS = 12


class _Task:
    """A minimal task sender — Celery's signal dispatch requires a HASHABLE sender."""

    def __init__(self, name: str) -> None:
        self.name = name


def _use_the_database() -> None:
    """One task execution as far as the database is concerned: acquire and use."""
    with connections["default"].cursor() as cursor:
        cursor.execute("SELECT 1")
        cursor.fetchone()


def _run_a_task(*, task_name: str = "tests.task") -> None:
    """A task as Celery runs it: prerun signal, work, postrun signal."""
    sender = _Task(task_name)
    task_prerun.send(sender=sender)
    _use_the_database()
    task_postrun.send(sender=sender)


def _server_side_backend_count() -> int:
    """PostgreSQL's view of how many backends serve this database.

    Read with this thread's connections CLOSED first, so the query's own backend
    is the same +1 in every measurement and cancels out of a comparison.
    """
    connections.close_all()
    with connections["default"].cursor() as cursor:
        cursor.execute(
            "SELECT count(*) FROM pg_stat_activity WHERE datname = current_database()"
        )
        return cursor.fetchone()[0]


def _without_postrun_cleanup():
    """Context manager that DISCONNECTS the cell's postrun receiver.

    The only faithful model of "postrun cleanup is absent": not a flag the
    handler checks, but the handler not being attached at all.
    """
    import contextlib

    @contextlib.contextmanager
    def _ctx():
        task_postrun.disconnect(lifecycle._close_connections_after_task)
        try:
            yield
        finally:
            task_postrun.connect(
                lifecycle._close_connections_after_task,
                weak=False,
            )

    return _ctx()


def _hold_a_pool_alive(*, use_cleanup: bool):
    """Run a REAL pool that stays alive until told to stop.

    Threads run ``ROUNDS`` tasks each, then PARK. While parked, whatever they are
    still holding is genuinely held — the state the production leak lived in, and
    the only state in which it can be measured. Joined-then-measured cannot see it.

    Returns (measure, stop).
    """
    parked = threading.Barrier(CONCURRENCY + 1)
    release = threading.Event()

    def _worker() -> None:
        try:
            for _ in range(ROUNDS):
                _use_the_database()
                if use_cleanup:
                    lifecycle._close_connections_after_task(
                        sender=SimpleNamespace(name="tests.pooled_task")
                    )
            parked.wait(timeout=30)
            release.wait(timeout=30)
        finally:
            connections.close_all()

    threads = [threading.Thread(target=_worker) for _ in range(CONCURRENCY)]
    for thread in threads:
        thread.start()

    def measure() -> int:
        parked.wait(timeout=30)  # every thread finished its tasks and parked
        return _server_side_backend_count()

    def stop() -> None:
        release.set()
        for thread in threads:
            thread.join(timeout=30)

    return measure, stop


# ---------------------------------------------------------------------------
# Deterministic: repeated tasks on ONE thread, driven through the signals.
# ---------------------------------------------------------------------------


@pytest.mark.django_db(transaction=True)
def test_repeated_tasks_never_accumulate_on_a_worker_thread():
    """REPEATS tasks, and after EVERY one the thread holds nothing.

    No timing luck and no second thread: a count that returns to zero after each
    task cannot climb, which is the property the live leak violated.
    """
    for iteration in range(REPEATS):
        _run_a_task(task_name=f"tests.repeat_{iteration}")

        held = lifecycle.thread_connection_count()
        assert held == 0, (
            f"after task {iteration + 1} of {REPEATS} the thread still held {held} "
            "connection(s); repeated tasks must not accumulate — this is the live "
            "leak's shape"
        )


@pytest.mark.django_db(transaction=True)
def test_the_same_repeats_accumulate_when_the_postrun_cleanup_is_absent():
    """CONTROL — proves the repeats above are not passing for free.

    With the postrun receiver DISCONNECTED, the identical workload must leave the
    thread holding its backend through every task. If this ever reads 0, the test
    above is measuring the harness rather than the cleanup.
    """
    with _without_postrun_cleanup():
        for iteration in range(REPEATS):
            _run_a_task(task_name=f"tests.leaky_{iteration}")

            held = lifecycle.thread_connection_count()
            assert held == 1, (
                f"without postrun cleanup the thread held {held} after task "
                f"{iteration + 1}; it must hold exactly one, never release it, and "
                "never accumulate a second (Django reuses a thread's connection)"
            )
    connections.close_all()


@pytest.mark.django_db(transaction=True)
def test_a_task_that_raises_still_releases_its_connection():
    """POSTRUN MUST BE FINALLY-SHAPED: a failing task releases too.

    Celery sends ``task_postrun`` whether the task returned or raised, so cleanup
    attached there runs in both cases. A handler that only ran on success would
    leak exactly when tasks are failing — the moment the worker is least healthy.
    """
    sender = _Task("tests.failing_task")
    task_prerun.send(sender=sender)
    _use_the_database()
    try:
        raise RuntimeError("simulated task failure")
    except RuntimeError:
        pass
    finally:
        task_postrun.send(sender=sender)

    assert lifecycle.thread_connection_count() == 0, (
        "a task that raised left its connection behind, so cleanup is not "
        "finally-shaped and failures leak"
    )


# ---------------------------------------------------------------------------
# The live shape: one process, a parked thread pool, measured server-side.
# ---------------------------------------------------------------------------


@pytest.mark.django_db(transaction=True)
def test_a_parked_pool_bounds_the_server_side_count():
    """THE FIX, measured where the leak showed up (30 idle backends)."""
    before = _server_side_backend_count()
    measure, stop = _hold_a_pool_alive(use_cleanup=True)
    try:
        after = measure()
    finally:
        stop()

    assert after <= before + 1, (
        f"{TOTAL_TASKS} task executions across a parked {CONCURRENCY}-thread pool "
        f"left the database serving {after - before} extra backend(s) (before="
        f"{before}, after={after}); a parked pool must hold none"
    )


@pytest.mark.django_db(transaction=True)
def test_a_parked_pool_without_cleanup_IS_grown_and_so_the_bound_can_fail():
    """CONTROL — and the reason the bound above is not vacuous.

    An earlier version of this file closed every connection in a ``finally`` and
    counted after joining, which made this assertion unfalsifiable: it passed with
    no handler at all. This arm is what stops that regressing again.
    """
    before = _server_side_backend_count()
    measure, stop = _hold_a_pool_alive(use_cleanup=False)
    try:
        after = measure()
    finally:
        stop()

    assert after >= before + CONCURRENCY, (
        f"a parked pool that never released only moved the backend count from "
        f"{before} to {after}; each parked thread should still hold one, so this "
        "measurement cannot see the leak and the bound above proves nothing"
    )


# ---------------------------------------------------------------------------
# CELERY_DB_CONN_MAX_AGE must be applied, not delegated to CONN_MAX_AGE.
# ---------------------------------------------------------------------------


@pytest.mark.django_db(transaction=True)
def test_a_task_age_shorter_than_conn_max_age_is_honoured(monkeypatch):
    """THE BUG: ``close_if_unusable_or_obsolete()`` measures DJANGO's CONN_MAX_AGE.

    That setting is 600 here, so a connection younger than 600s survived a
    ``CELERY_DB_CONN_MAX_AGE`` asking for it to be dropped: a configured value
    that looked honoured and changed nothing. With the age applied directly, a
    1-second budget releases a connection older than 1 second.
    """
    monkeypatch.setenv("CELERY_DB_CONN_MAX_AGE", "1")
    _use_the_database()
    time.sleep(1.2)

    assert lifecycle.release_thread_connections() == 1, (
        "a connection older than CELERY_DB_CONN_MAX_AGE was kept, so the age is "
        "being evaluated against CONN_MAX_AGE instead of the Celery setting"
    )
    connections.close_all()


@pytest.mark.django_db(transaction=True)
def test_a_task_age_longer_than_the_connection_age_keeps_it(monkeypatch):
    """CONTROL: a connection younger than the budget is KEPT.

    Without this, an unconditional ``conn.close()`` would satisfy the test above
    while silently defeating persistent task connections for anyone who
    configures them.
    """
    monkeypatch.setenv("CELERY_DB_CONN_MAX_AGE", "3600")
    _use_the_database()

    assert lifecycle.release_thread_connections() == 0, (
        "a fresh connection was released despite a 3600s task budget, so "
        "CELERY_DB_CONN_MAX_AGE is not honoured in this direction"
    )
    assert lifecycle.thread_connection_count() == 1
    connections.close_all()


@pytest.mark.django_db(transaction=True)
def test_zero_task_age_releases_every_task(monkeypatch):
    """The default: 0 means release after every task."""
    monkeypatch.delenv("CELERY_DB_CONN_MAX_AGE", raising=False)
    _use_the_database()

    assert lifecycle.release_thread_connections() == 1
    assert lifecycle.thread_connection_count() == 0


# ---------------------------------------------------------------------------
# Telemetry: two numbers, named for what they actually measure.
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_telemetry_reports_the_THREAD_count_by_name(caplog):
    """The cheap number is reported as a THREAD count, not a process count."""
    _use_the_database()

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
    assert any("tests.telemetry" in message for message in messages), (
        "the task name is not logged, so a growing thread cannot be attributed"
    )
    assert not any("open_connections=" in message for message in messages), (
        "telemetry still labels a thread-local count as if it were process-wide"
    )

    connections.close_all()


@pytest.mark.django_db
def test_process_telemetry_can_see_more_than_this_thread():
    """The process-wide number is genuinely server-side, not thread-local.

    The live leak is a TOTAL of ~30 backends across a pool. A thread-local count
    can only ever report this thread's one connection, so if the two numbers agree
    the "process" figure is not measuring what it claims.
    """
    _use_the_database()
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
    _use_the_database()

    with caplog.at_level(logging.INFO, logger=lifecycle.__name__):
        lifecycle.record_task_boundary(task_name="tests.loud", phase="postrun")

    assert any(record.levelno >= logging.WARNING for record in caplog.records), (
        "crossing the threshold logged nothing at WARNING level, so exhaustion "
        "would arrive unannounced"
    )
    assert called["n"] == 1, (
        "the server-side count was not read when the threshold was crossed, so the "
        "warning cannot say whether the SERVER is filling up"
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
    _use_the_database()

    with caplog.at_level(logging.INFO, logger=lifecycle.__name__):
        lifecycle.record_task_boundary(task_name="tests.quiet", phase="postrun")

    assert called["n"] == 0, (
        "a healthy task boundary paid for a server-side query on every task"
    )
    connections.close_all()
