#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""A pty reaper may collect only the children it forked.

WHY THIS TEST EXISTS. console_app's SIGCHLD handler called
``os.waitpid(-1, os.WNOHANG)`` — reap ANY child of this process — and was
installed at IMPORT time, so importing the URLconf armed it. Every
``subprocess.run`` in the Django process then raced it: when the handler won,
``Popen.wait()`` found the child already collected, got ECHILD, and Python
reported **returncode 0 for a command that failed**.

Measured 2026-09-06, found by bisecting 39 test files after one of my own tests
passed alone and failed in a full run::

    pytest tests/config/test_every_pane_names_its_tab.py <probe>
        (that file only calls get_resolver(), which imports the URLconf)
      subprocess.run(["bash", "-c", "echo hi; exit 1"]) -> returncode 0
    the probe alone
      subprocess.run(same)                              -> returncode 1

hub shells out for git, Gitea, apptainer, npm, PDF tooling and the visitor
pool's template clone. Any ``if result.returncode != 0:`` in the serving
process could stop being able to fail — silently, and as a race.

No mocks: real subprocesses, a real fork, the real handler. A mocked waitpid
cannot exhibit the ECHILD race that caused this.
"""

from __future__ import annotations

import os
import re
import signal
import subprocess
import sys
import time
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
TERMINAL_DIR = (
    REPO_ROOT / "apps" / "workspace" / "console_app" / "views" / "terminal"
)


# ---------------------------------------------------------------------------
# The rule: foreign children are not touched
# ---------------------------------------------------------------------------


def _await_zombie(pid: int, timeout: float = 5.0) -> bool:
    """Block until `pid` has EXITED but is NOT yet reaped, without reaping it.

    Reading /proc rather than waitpid() is the whole point: any wait call here
    would collect the child and destroy the very race under test.
    """
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            stat = Path(f"/proc/{pid}/stat").read_text()
        except FileNotFoundError:
            return False
        # state is the field after the ")" that closes comm
        if stat.rsplit(") ", 1)[1].split()[0] == "Z":
            return True
        time.sleep(0.005)
    return False


@pytest.mark.parametrize("exit_code", [1, 3, 42])
def test_the_handler_does_not_steal_a_foreign_childs_exit_status(exit_code):
    """THE REGRESSION, in the order it actually happens.

    ORDERING IS THE WHOLE TEST. The first version of this file called
    proc.wait() BEFORE firing the handler -- so Popen had already collected the
    status, nothing was left to steal, and the test passed against the BROKEN
    waitpid(-1) implementation. It was a gate that could not fail, and only
    restoring the old code and seeing 10/10 still green exposed it.

    The real race is: child exits -> SIGCHLD fires -> handler reaps -> only
    then does the caller wait(), and gets ECHILD.
    """
    # Arrange -- a child that has exited and is NOT yet reaped.
    from apps.workspace.console_app.views.terminal.consumer import _sigchld_handler

    proc = subprocess.Popen([sys.executable, "-c", f"raise SystemExit({exit_code})"])
    assert _await_zombie(proc.pid), (
        f"child {proc.pid} never became a zombie; the race this test needs was "
        "not set up, so a pass below would mean nothing."
    )

    # Act -- the handler fires BEFORE anyone waits.
    _sigchld_handler(signal.SIGCHLD, None)

    # Assert -- the status must still be there for its owner.
    assert proc.wait(timeout=5) == exit_code, (
        f"the pty SIGCHLD handler collected a child it did not fork: expected "
        f"exit {exit_code}, got {proc.returncode}. With waitpid(-1) this is how "
        "a failed git/npm/apptainer call reports success inside Django."
    )


def _registered():
    from apps.workspace.console_app.views.terminal.pty_children import (
        registered_pty_children,
    )

    return registered_pty_children()


# ---------------------------------------------------------------------------
# Positive control: it must still reap what it OWNS, or it is not a reaper
# ---------------------------------------------------------------------------


def test_the_handler_still_reaps_a_registered_child():
    """Otherwise the fix is 'do nothing', which passes every test above."""
    # Arrange -- a real forked child, registered the way a pty site does.
    from apps.workspace.console_app.views.terminal.consumer import _sigchld_handler
    from apps.workspace.console_app.views.terminal.pty_children import (
        register_pty_child,
        registered_pty_children,
    )

    pid = os.fork()
    if pid == 0:  # pragma: no cover - child never returns
        os._exit(0)
    register_pty_child(pid)
    assert pid in registered_pty_children()

    # Act -- poll with a real delay. A tight loop can complete before the
    # child is even scheduled to exit, which fails this control for a reason
    # that has nothing to do with the reaper (measured: 200 tight iterations
    # finished first).
    deadline = time.monotonic() + 5.0
    while time.monotonic() < deadline:
        _sigchld_handler(signal.SIGCHLD, None)
        if pid not in registered_pty_children():
            break
        time.sleep(0.01)

    # Assert
    assert pid not in registered_pty_children(), (
        f"registered pty child {pid} was never reaped. A reaper that collects "
        "nothing leaks a zombie per terminal session."
    )


def test_registering_the_child_side_of_a_fork_is_a_noop():
    """pid 0 is the child; the call site is one line with no branch."""
    from apps.workspace.console_app.views.terminal.pty_children import (
        register_pty_child,
        registered_pty_children,
    )

    register_pty_child(0)
    assert 0 not in registered_pty_children()


# ---------------------------------------------------------------------------
# The gate: a new fork site cannot silently forget to register
# ---------------------------------------------------------------------------


def _fork_sites():
    """(path, line) for every real pty.fork() call under the terminal views."""
    found = []
    for path in sorted(TERMINAL_DIR.glob("*.py")):
        for n, line in enumerate(path.read_text().splitlines(), 1):
            if re.search(r"=\s*pty\.fork\(\)", line):
                found.append((path, n))
    return found


def test_the_sweep_found_the_fork_sites():
    """A glob matching nothing would make the gate below pass vacuously."""
    sites = _fork_sites()
    assert len(sites) >= 3, (
        f"expected at least 3 pty.fork() sites under {TERMINAL_DIR}, found "
        f"{len(sites)}. Either they moved or the scan broke — and a scan that "
        "finds nothing reports clean."
    )


@pytest.mark.parametrize(
    "path,line", _fork_sites(), ids=lambda v: getattr(v, "name", str(v))
)
def test_every_fork_site_registers_its_child(path, line):
    """The reaper can only collect pids it was told about."""
    window = "\n".join(path.read_text().splitlines()[line : line + 8])

    assert "register_pty_child(" in window, (
        f"{path.name}:{line} calls pty.fork() and does not register the child "
        "within the next 8 lines. The SIGCHLD handler only reaps registered "
        "pids, so this fork leaks a zombie per session. Add "
        "`register_pty_child(consumer.pid)` immediately after the fork — it is "
        "a no-op in the child."
    )
