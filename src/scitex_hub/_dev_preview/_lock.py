#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: src/scitex_hub/_dev_preview/_lock.py

"""One sync at a time: a non-blocking ``flock`` on ``<state_dir>/lock``.

The supervisor already skips a tick whose previous run is still going
(``skipped_still_running``), but that only covers ITS runs. An operator
running ``scitex-hub dev-preview sync`` by hand while a timer run is
mid-rebuild would otherwise race it on the same clone and the same compose
project. ``flock(LOCK_EX | LOCK_NB)`` is held for the whole run and is
released by the kernel if the process dies, so a crash never leaves a stale
lock behind (unlike a pid file).
"""

from __future__ import annotations

import fcntl
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

__all__ = ["AlreadyRunning", "LOCK_FILE", "hold_lock"]

LOCK_FILE = "lock"


class AlreadyRunning(RuntimeError):
    """Another sync holds the lock; this run must exit without touching anything."""


@contextmanager
def hold_lock(state_dir: Path) -> Iterator[Path]:
    """Hold ``<state_dir>/lock`` exclusively for the ``with`` body.

    Raises :class:`AlreadyRunning` immediately (no waiting) when another
    process — or another open file description in this one — holds it.
    """
    state_dir.mkdir(parents=True, exist_ok=True)
    path = state_dir / LOCK_FILE
    fh = path.open("a+")
    try:
        try:
            fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise AlreadyRunning(f"lock held: {path}") from exc
        yield path
    finally:
        try:
            fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
        finally:
            fh.close()


# EOF
