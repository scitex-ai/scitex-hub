#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: tests/config/test_asgi_request_threads_release_db_connections.py
"""A request thread must hand its Postgres backend back when the request ends.

Site-audit blocker D2 (2026-09-14, compute-03 dev): pages returned 500
"OperationalError ... too many clients" under three parallel browsers, and a
single FigRecipe thumbnail fan-out produced 120 errors in 15 minutes.
pg_stat_activity showed one runserver process holding 36 idle backends 21
minutes after it started.

Mechanism: the dev server is ASGI (daphne via runserver), so each request runs
its sync code in its own thread. With CONN_MAX_AGE=600 Django's
request_finished handler (close_old_connections) keeps that thread's
connection "for reuse", but the thread is never reused, so the backend is
orphaned until garbage collection happens to reach the wrapper. Django
documents that persistent connections must be disabled under ASGI.

These tests reproduce the request lifecycle on a REAL separate thread and ask
that thread, not the test thread, whether it still holds a connection, since
``connections`` is thread-local.
"""

from __future__ import annotations

import threading

import pytest
from django.conf import settings
from django.core.signals import request_finished
from django.db import connections


def _request_on_its_own_thread(make_connection) -> bool:
    """Run one request's DB lifecycle on a fresh thread.

    Returns whether that thread still held an open connection after
    request_finished fired, which is exactly the backend an ASGI request
    thread would leave behind.
    """
    result: dict[str, bool] = {}

    def _request() -> None:
        conn = make_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
            request_finished.send(sender=None)
            conn.close_if_unusable_or_obsolete()
            result["held"] = conn.connection is not None
        finally:
            conn.close()

    thread = threading.Thread(target=_request)
    thread.start()
    thread.join(timeout=30)
    return result["held"]


def _standalone_connection_with_age(conn_max_age: int):
    """A wrapper outside the handler, so a non-default age needs no patching."""
    default = connections["default"]
    settings_dict = {**default.settings_dict, "CONN_MAX_AGE": conn_max_age}
    return type(default)(settings_dict, alias=f"age_{conn_max_age}")


def test_dev_settings_disable_persistent_connections_under_asgi():
    # Arrange
    database = settings.DATABASES["default"]

    # Act
    conn_max_age = database["CONN_MAX_AGE"]

    # Assert
    assert conn_max_age == 0, (
        f"CONN_MAX_AGE is {conn_max_age!r}. Under ASGI every request thread is "
        "new, so a persistent connection is never reused and leaks one Postgres "
        "backend per request until max_connections is exhausted"
    )


@pytest.mark.django_db
def test_a_request_thread_releases_its_connection_when_the_request_finishes():
    # Arrange
    configured = lambda: connections["default"]  # noqa: E731 - the thread's own

    # Act
    held = _request_on_its_own_thread(configured)

    # Assert
    assert held is False, (
        "a request thread still held its Postgres connection after "
        "request_finished, so every ASGI request orphans one backend"
    )


@pytest.mark.django_db
def test_control_a_persistent_age_keeps_the_connection_the_fix_releases():
    # Arrange
    persistent = lambda: _standalone_connection_with_age(600)  # noqa: E731

    # Act
    held = _request_on_its_own_thread(persistent)

    # Assert
    assert held is True, (
        "with CONN_MAX_AGE=600 the thread released its connection anyway, so "
        "the test above cannot tell the leaking setting from the fixed one"
    )


# EOF
