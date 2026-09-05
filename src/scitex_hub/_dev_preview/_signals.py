#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: src/scitex_hub/_dev_preview/_signals.py

"""Make a SIGTERM mid-tick catchable, so the in-flight action gets recorded.

The job runs under ``/usr/bin/timeout``, which SIGTERMs the whole process
group when it fires. Without a handler Python dies between two bytecodes
with no frame to catch anything in; the write-ahead attempt (``_state``)
still counts the tick as failed, but the log would end at ``phase: start``
with no ``killed`` line and no signal number. With the handler the act loop
sees :class:`TickInterrupted`, records ``rc=-15`` and the action's name,
saves, and exits cleanly (``timeout`` still reports 124 to the supervisor).

``BaseException``, like its SIGINT twin ``KeyboardInterrupt``: an action's
own ``except Exception`` must not swallow it.
"""

from __future__ import annotations

import signal
from contextlib import contextmanager
from typing import Any, Iterator

__all__ = ["TickInterrupted", "signum_of", "sigterm_raises"]


class TickInterrupted(BaseException):
    """SIGTERM arrived; raised from the handler so the act loop can record it."""

    def __init__(self, signum: int) -> None:
        self.signum = int(signum)
        super().__init__(f"interrupted by signal {self.signum}")


@contextmanager
def sigterm_raises() -> Iterator[None]:
    """Turn SIGTERM into :class:`TickInterrupted` for the ``with`` body.

    Python only allows installing a handler from the main thread; anywhere
    else the body runs with the process default and the write-ahead attempt
    alone covers a kill.
    """

    def handler(signum: int, frame: Any) -> None:
        raise TickInterrupted(signum)

    try:
        previous = signal.signal(signal.SIGTERM, handler)
    except ValueError:
        yield
        return
    try:
        yield
    finally:
        signal.signal(signal.SIGTERM, previous)


def signum_of(exc: BaseException) -> int:
    """The signal behind a :class:`TickInterrupted` or ``KeyboardInterrupt``."""
    return exc.signum if isinstance(exc, TickInterrupted) else int(signal.SIGINT)


# EOF
