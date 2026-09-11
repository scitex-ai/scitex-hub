"""Database-connection lifecycle helpers for application-owned threads."""

from __future__ import annotations

from collections.abc import Callable
from functools import wraps
from typing import ParamSpec, TypeVar

from django.db import connections

P = ParamSpec("P")
R = TypeVar("R")


def close_database_connections_after(
    function: Callable[P, R],
) -> Callable[P, R]:
    """Close connections opened by the current thread after ``function``.

    Django connections are thread-local.  Threads created outside Django's
    request lifecycle therefore need their own explicit boundary; neither the
    request-finished signal nor a surrounding Celery task can see a nested
    thread's connection.
    """

    @wraps(function)
    def wrapped(*args: P.args, **kwargs: P.kwargs) -> R:
        try:
            return function(*args, **kwargs)
        finally:
            connections.close_all()

    return wrapped
