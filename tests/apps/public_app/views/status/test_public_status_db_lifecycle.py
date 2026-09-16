"""Regression for database connections opened by public-status worker threads."""

from concurrent.futures import ThreadPoolExecutor

import pytest
from django.db import connections

from apps.infra.public_app.views.status.public_status import _run_check_safe


def _thread_connection_count() -> int:
    return sum(1 for conn in connections.all() if conn.connection is not None)


@pytest.mark.django_db(transaction=True)
def test_status_executor_task_closes_its_child_thread_database_connection():
    """The nested executor must return its backend before its next task.

    Keep one worker alive and inspect that same thread after the status check.
    Measuring after executor shutdown would be vacuous because thread teardown
    can discard thread-local state without proving the task boundary closed it.
    """

    opened = []

    def database_check(status_data):
        with connections["default"].cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        opened.append(_thread_connection_count())
        status_data["database"] = {"is_running": True}

    with ThreadPoolExecutor(max_workers=1) as pool:
        pool.submit(_run_check_safe, database_check, {}).result(timeout=10)
        held_after_task = pool.submit(_thread_connection_count).result(timeout=10)

    assert opened == [1], "the child-thread check did not open a database connection"
    assert held_after_task == 0, (
        "the completed status executor task still held its child-thread database "
        "connection"
    )
