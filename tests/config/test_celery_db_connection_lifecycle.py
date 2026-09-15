"""Regression for the Celery PostgreSQL connection leak (issue #777).

WHAT THIS MUST PROVE. The leak is a ONE-PROCESS, MANY-THREADS accumulation:
``--pool=threads`` keeps worker threads alive, each holds a thread-local backend,
and nothing returns it. So the tests use
  * REAL worker threads,
  * driven by REAL Celery signal dispatch (not by calling the private handler —
    otherwise a handler that is never REGISTERED would pass), and
  * measured SERVER-SIDE, because ``connections`` is thread-local and cannot see
    another thread's backend at all.

An earlier version closed every thread's connections in a ``finally`` and counted
AFTER joining; that passes with no handler at all, because joining tears the thread
state down before the measurement. Another gated the database reading on a
thread-local threshold, which suppressed it in exactly the many-threads case it
existed to reveal.
"""

from __future__ import annotations

import logging
import threading
import time

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
    with connections["default"].cursor() as cursor:
        cursor.execute("SELECT 1")
        cursor.fetchone()


def _run_a_task(*, task_name: str = "tests.task") -> None:
    """A task as Celery runs it: prerun signal, work, postrun signal."""
    sender = _Task(task_name)
    task_prerun.send(sender=sender)
    _use_the_database()
    task_postrun.send(sender=sender)


def _database_backend_count() -> int:
    """PostgreSQL's view. Read with this thread's connections closed first, so the
    query's own backend is the same +1 in every measurement and cancels out."""
    connections.close_all()
    with connections["default"].cursor() as cursor:
        cursor.execute(
            "SELECT count(*) FROM pg_stat_activity WHERE datname = current_database()"
        )
        return cursor.fetchone()[0]


def _parked_pool(*, use_cleanup: bool):
    """A REAL thread pool that stays ALIVE while measured.

    Threads each run ``ROUNDS`` tasks through the real signals, then PARK. While
    parked, whatever they still hold is genuinely held — the state the live leak
    lives in, and the only state where it can be measured. Joined-then-measured
    cannot see it. Returns (measure, stop).
    """
    parked = threading.Barrier(CONCURRENCY + 1)
    release = threading.Event()

    def _worker() -> None:
        try:
            for _ in range(ROUNDS):
                if use_cleanup:
                    _run_a_task(task_name="tests.pooled_task")
                else:
                    task_prerun.send(sender=_Task("tests.pooled_task"))
                    _use_the_database()
                    # postrun deliberately NOT dispatched: the cleanup that lives
                    # there is the thing under test.
            parked.wait(timeout=30)
            release.wait(timeout=30)
        finally:
            connections.close_all()

    threads = [threading.Thread(target=_worker) for _ in range(CONCURRENCY)]
    for thread in threads:
        thread.start()

    def measure() -> int:
        parked.wait(timeout=30)
        return _database_backend_count()

    def stop() -> None:
        release.set()
        for thread in threads:
            thread.join(timeout=30)

    return measure, stop


# ---------------------------------------------------------------------------
# Real threads, real signals, deterministic repeats.
# ---------------------------------------------------------------------------


@pytest.mark.django_db(transaction=True)
def test_repeated_tasks_never_accumulate_on_a_worker_thread():
    """REPEATS tasks on ONE thread; after EVERY one the thread holds nothing."""
    for iteration in range(REPEATS):
        _run_a_task(task_name=f"tests.repeat_{iteration}")

        held = lifecycle.thread_connection_count()
        assert held == 0, (
            f"after task {iteration + 1} of {REPEATS} the thread still held {held} "
            "connection(s); repeated tasks must not accumulate"
        )


@pytest.mark.django_db(transaction=True)
def test_the_same_repeats_accumulate_when_postrun_cleanup_is_absent():
    """CONTROL — the repeats above must not pass for free.

    The postrun RECEIVER is disconnected rather than a flag flipped, which is the
    only faithful model of "postrun cleanup is absent".
    """
    task_postrun.disconnect(lifecycle._close_connections_after_task)
    try:
        for iteration in range(REPEATS):
            sender = _Task(f"tests.leaky_{iteration}")
            task_prerun.send(sender=sender)
            _use_the_database()

            held = lifecycle.thread_connection_count()
            assert held == 1, (
                f"without postrun cleanup the thread held {held} after task "
                f"{iteration + 1}; it must hold exactly one and never release it"
            )
    finally:
        task_postrun.connect(
            lifecycle._close_connections_after_task,
            weak=False,
            dispatch_uid="celery_db_lifecycle.close_after_task",
        )
        connections.close_all()


@pytest.mark.django_db(transaction=True)
def test_a_task_that_raises_still_releases_its_connection():
    """POSTRUN IS FINALLY-SHAPED: a failing task releases too."""
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
# The live shape: parked pool, server-side, BOTH arms compared directly.
# ---------------------------------------------------------------------------


@pytest.mark.django_db(transaction=True)
def test_cleanup_removes_the_leak_the_pool_would_otherwise_hold():
    """Both arms in one test, compared with a STRICT inequality.

    Asserting each arm against a constant independently allows the test to pass
    when the two numbers are EQUAL — which is precisely the case that means the
    cleanup did nothing. Comparing them directly removes that escape: equality
    fails.
    """
    before = _database_backend_count()
    measure, stop = _parked_pool(use_cleanup=True)
    try:
        after_clean = measure()
    finally:
        stop()
    clean_growth = after_clean - before

    before = _database_backend_count()
    measure, stop = _parked_pool(use_cleanup=False)
    try:
        after_leaky = measure()
    finally:
        stop()
    leaky_growth = after_leaky - before

    assert clean_growth <= 1, (
        f"a parked pool WITH cleanup left {clean_growth} extra backend(s); each "
        "task must return its backend, so a parked pool should hold none "
        "(the +1 allowance is the measuring connection itself)"
    )
    assert leaky_growth > clean_growth, (
        f"the pool WITHOUT cleanup grew by {leaky_growth} and the pool WITH it by "
        f"{clean_growth}. These must differ — if they are equal, the cleanup is not "
        "the thing being measured and the assertion above proves nothing"
    )
    assert leaky_growth >= CONCURRENCY, (
        f"a parked pool that never released grew by only {leaky_growth}; each "
        f"parked thread should still hold one ({CONCURRENCY}), so this measurement "
        "cannot see the leak at all"
    )


# ---------------------------------------------------------------------------
# CELERY_DB_CONN_MAX_AGE must be applied, not delegated to CONN_MAX_AGE.
# ---------------------------------------------------------------------------


@pytest.mark.django_db(transaction=True)
def test_a_task_age_shorter_than_conn_max_age_is_honoured(monkeypatch):
    """A 1-second budget releases a connection older than 1 second.

    The old code delegated to ``close_if_unusable_or_obsolete()``, which measures
    Django's ``CONN_MAX_AGE`` (600 here), so this connection was kept and the
    setting did nothing.
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
def test_the_task_age_still_works_when_conn_max_age_is_none(monkeypatch):
    """CONN_MAX_AGE=None must NOT disable the Celery age.

    That setting leaves Django's ``close_at`` unset, which is exactly the
    configuration where deriving the age from Django is impossible — and where a
    delegation-based implementation silently kept every connection forever.
    """
    monkeypatch.setenv("CELERY_DB_CONN_MAX_AGE", "1")
    conn = connections["default"]
    monkeypatch.setitem(conn.settings_dict, "CONN_MAX_AGE", None)
    monkeypatch.setattr(conn, "close_at", None, raising=False)

    _use_the_database()
    time.sleep(1.2)

    assert lifecycle.release_thread_connections() == 1, (
        "with CONN_MAX_AGE=None a connection older than the Celery budget was "
        "kept, so a non-zero CELERY_DB_CONN_MAX_AGE is a no-op in that config"
    )
    connections.close_all()


@pytest.mark.django_db(transaction=True)
def test_a_task_age_longer_than_the_connection_age_keeps_it(monkeypatch):
    """CONTROL: a connection younger than the budget is KEPT."""
    monkeypatch.setenv("CELERY_DB_CONN_MAX_AGE", "3600")
    _use_the_database()

    assert lifecycle.release_thread_connections() == 0, (
        "a fresh connection was released despite a 3600s task budget, so the "
        "setting is not honoured in this direction"
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
# The created-connection receiver must actually be attached.
# ---------------------------------------------------------------------------


@pytest.mark.django_db(transaction=True)
def test_a_new_connection_is_stamped_so_its_age_is_known():
    """The receiver must be STRONGLY retained and actually firing.

    Django's ``connect()`` stores a weak reference by default, so a receiver can be
    collected and stop firing without anything failing — the age then reads as
    unknown and a configured budget silently keeps every connection. Asserting the
    stamp directly is what makes that visible.
    """
    connections.close_all()
    _use_the_database()

    conn = connections["default"]
    assert getattr(conn, "_celery_created_at", None) is not None, (
        "a newly created connection carries no stamp, so the connection_created "
        "receiver is not firing and CELERY_DB_CONN_MAX_AGE cannot be applied"
    )
    connections.close_all()


# ---------------------------------------------------------------------------
# Telemetry: two numbers, named for what they actually measure.
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_telemetry_names_both_numbers_honestly(caplog):
    """Neither number may be presented as a process count."""
    _use_the_database()

    with caplog.at_level(logging.INFO, logger=lifecycle.__name__):
        lifecycle.record_task_boundary(task_name="tests.telemetry", phase="postrun")

    messages = [record.getMessage() for record in caplog.records]
    assert any(
        "thread_connections=" in m and "database_connections=" in m for m in messages
    ), f"telemetry did not report both numbers distinctly: {messages}"
    assert any("tests.telemetry" in m for m in messages), "the task name is not logged"
    assert not any(
        "open_connections=" in m or "process_connections=" in m for m in messages
    ), "telemetry still labels a thread-local or database-wide count as a process one"

    connections.close_all()


@pytest.mark.django_db(transaction=True)
def test_the_database_number_can_see_more_than_this_thread():
    """It is genuinely database-wide, not thread-local."""
    _use_the_database()
    in_thread = lifecycle.thread_connection_count()

    on_database = lifecycle.database_connection_count()

    assert on_database is not None, "the database count could not be read"
    assert on_database >= in_thread, (
        f"database count ({on_database}) is below this thread's own count "
        f"({in_thread}), so it is not a database-wide measurement"
    )
    connections.close_all()


@pytest.mark.django_db
def test_the_database_number_is_read_on_every_boundary_not_suppressed(
    caplog, monkeypatch
):
    """A HEALTHY thread-local count must not suppress the database reading.

    Gating it on the thread-local threshold hid the real leak: many threads each
    holding one never make any single thread cross the threshold, so the expensive
    reading was skipped in exactly the case it existed to expose.
    """
    called = {"n": 0}
    real = lifecycle.database_connection_count

    def _spy():
        called["n"] += 1
        return real()

    monkeypatch.setattr(lifecycle, "database_connection_count", _spy)
    _use_the_database()

    with caplog.at_level(logging.INFO, logger=lifecycle.__name__):
        lifecycle.record_task_boundary(task_name="tests.quiet", phase="postrun")

    assert called["n"] == 1, (
        "the database count was not read on a boundary whose thread-local count "
        "looked healthy, so a many-threads leak would be invisible"
    )
    connections.close_all()


@pytest.mark.django_db
def test_telemetry_escalates_when_the_DATABASE_is_above_the_threshold(
    caplog, monkeypatch
):
    """Alerting keys off the database number, not the thread-local one."""
    monkeypatch.setattr(lifecycle, "warn_threshold", lambda: 0)
    _use_the_database()

    with caplog.at_level(logging.INFO, logger=lifecycle.__name__):
        lifecycle.record_task_boundary(task_name="tests.loud", phase="postrun")

    assert any(record.levelno >= logging.WARNING for record in caplog.records), (
        "the database being over the threshold logged nothing at WARNING level, so "
        "exhaustion would arrive unannounced"
    )
    connections.close_all()
