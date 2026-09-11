"""Database lifecycle regression for the detailed server-status executor."""

from concurrent.futures import ThreadPoolExecutor
from threading import Event, local

import pytest

import apps.infra.public_app.views.status.server as server
import config.django_db_threads as django_db_threads


class _ThreadLocalAlias:
    def __init__(self):
        self.state = local()

    def open(self):
        self.state.is_open = True

    def close(self):
        self.state.is_open = False

    @property
    def is_open(self):
        return getattr(self.state, "is_open", False)


class _ThreadLocalConnections:
    """Small two-alias stand-in for Django's thread-local handler."""

    def __init__(self):
        self.aliases = {
            "default": _ThreadLocalAlias(),
            "status_replica": _ThreadLocalAlias(),
        }

    def open_all(self):
        for connection in self.aliases.values():
            connection.open()

    def close_all(self):
        for connection in self.aliases.values():
            connection.close()

    def open_count(self):
        return sum(connection.is_open for connection in self.aliases.values())


@pytest.mark.parametrize("raises", [False, True], ids=["success", "caught-exception"])
def test_server_status_task_closes_every_alias_in_its_worker_thread(
    monkeypatch, raises
):
    """A completed child task must return every alias before thread reuse."""
    handler = _ThreadLocalConnections()
    monkeypatch.setattr(django_db_threads, "connections", handler)
    opened = []

    def database_check(status_data):
        handler.open_all()
        opened.append(handler.open_count())
        if raises:
            raise RuntimeError("expected check failure")

    with ThreadPoolExecutor(max_workers=1) as pool:
        pool.submit(server._run_check, database_check).result(timeout=10)
        held_after_task = pool.submit(handler.open_count).result(timeout=10)

    assert opened == [2], "the check did not exercise both configured aliases"
    assert held_after_task == 0, (
        "the completed server-status task retained a child-thread database connection"
    )


def test_deadline_straggler_closes_connections_when_it_eventually_finishes(monkeypatch):
    """Returning UNKNOWN early must not strand a late task's DB connections."""
    handler = _ThreadLocalConnections()
    original_close_all = handler.close_all
    started = Event()
    release = Event()
    cleanup_finished = Event()

    def observed_close_all():
        original_close_all()
        cleanup_finished.set()

    monkeypatch.setattr(handler, "close_all", observed_close_all)
    monkeypatch.setattr(django_db_threads, "connections", handler)

    def slow_database_check(status_data):
        handler.open_all()
        assert handler.open_count() == 2
        started.set()
        assert release.wait(timeout=10)

    try:
        status_data = server._collect_status_data(
            None,
            {"check_database": slow_database_check},
            deadline_seconds=0.05,
        )
        assert started.is_set(), "the straggler never opened its database connections"
        assert status_data["database"]["status"] == "unknown"
        assert not cleanup_finished.is_set(), "cleanup ran before the check finished"

        release.set()
        assert cleanup_finished.wait(timeout=10), (
            "the post-deadline task finished without closing its database aliases"
        )
    finally:
        release.set()
        original_close_all()
