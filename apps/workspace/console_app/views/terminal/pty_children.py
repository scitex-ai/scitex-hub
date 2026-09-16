#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The set of pty children this process forked, and nothing else.

WHY THIS MODULE EXISTS. The SIGCHLD handler for the direct pty.fork() fallback
used to call ``os.waitpid(-1, os.WNOHANG)`` — reap ANY child of this process.
It is installed at IMPORT time in ``consumer.py``, and importing the URLconf is
enough to install it, which every Django process does.

So the handler reaped children it did not fork. When it won the race,
``subprocess.Popen.wait()`` found its child already collected, got ECHILD, and
Python reported **returncode 0 for a command that failed**. Measured
2026-09-06::

    pytest tests/config/test_every_pane_names_its_tab.py   (imports the URLconf)
      subprocess.run(["bash", "-c", "echo hi; exit 1"])
        -> returncode 0,  stdout 'hi\\n'
    the same probe without that import
        -> returncode 1                                    CONTROL

hub shells out in many places — git and Gitea, apptainer, npm, PDF tooling, the
visitor pool's template clone. Every ``if result.returncode != 0:`` in the
serving process was liable to stop being able to fail, silently and as a race.

THE REGISTRY IS THE FIX. A reaper may only collect what it forked. Registering
is deliberately a no-op for pid 0 so the call site is one identical line in the
parent and harmless in the child, which execs immediately anyway.

A MISSED REGISTRATION LEAKS A ZOMBIE; the old behaviour BROKE EVERY SUBPROCESS
IN THE PROCESS. Those failure modes are not comparable, and
tests/apps/console_app/test_sigchld_reaper_only_reaps_its_own.py gates the call
sites so a new fork site cannot quietly forget.
"""

from __future__ import annotations

import os

# Plain set, no lock. A signal handler that takes a lock can deadlock against
# the thread it interrupted; add/discard on a CPython set are atomic enough for
# this use, and the handler iterates a snapshot.
_pty_child_pids: set[int] = set()


def register_pty_child(pid: int) -> None:
    """Record a pty child so the SIGCHLD handler may reap THAT pid.

    No-op for the child side of a fork (pid 0) and for invalid pids, so the
    call site needs no branch.
    """
    if pid and pid > 0:
        _pty_child_pids.add(pid)


def forget_pty_child(pid: int) -> None:
    """Drop a pid already reaped elsewhere (the consumer reaps its own on close)."""
    _pty_child_pids.discard(pid)


def registered_pty_children() -> frozenset[int]:
    """Snapshot, for tests and diagnostics."""
    return frozenset(_pty_child_pids)


def reap_registered_children() -> list[int]:
    """Reap only registered pty children. Returns the pids actually collected.

    Never ``waitpid(-1)``. Iterates a snapshot so a concurrent registration
    cannot mutate the set under the signal handler.
    """
    reaped: list[int] = []
    for pid in tuple(_pty_child_pids):
        try:
            done, _status = os.waitpid(pid, os.WNOHANG)
        except ChildProcessError:
            # Already reaped by whoever forked it — stop tracking.
            _pty_child_pids.discard(pid)
        except OSError:
            _pty_child_pids.discard(pid)
        else:
            if done:
                _pty_child_pids.discard(pid)
                reaped.append(done)
    return reaped
