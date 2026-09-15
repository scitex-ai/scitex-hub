#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: src/scitex_hub/_dev_preview/_actions.py

"""The four follow-up actions the preview may need, as injectable callables.

:class:`Actions` is a dataclass of callables with defaults that shell out.
The sync engine only ever calls ``actions.<name>(...)``, so a test injects
recording callables (real Python functions that append to a list) and
proves the engine's ORDER and COUNT of calls against a real git clone —
without a docker daemon and without a mock library (forbidden fleet-wide).

WHAT EACH DEFAULT RUNS, AND WHY THAT COMMAND
--------------------------------------------
``reload(clone)``   -> ``make ENV=dev reload`` in the clone. The Makefile
    target runs ``preflight_sibling_floors.sh`` and then
    ``compose up -d --force-recreate django`` — the sanctioned recreate; it
    does NOT wait for health, so the engine calls ``wait_healthy`` after it.
``rebuild(clone)``  -> ``make ENV=dev YES=1 rebuild`` (``scripts/deploy/
    rebuild.sh``: build the image while the old stack serves, preflight the
    NEW image, swap). Measured 10-25 min; bounded at 40 min here.
``migrate(container)`` -> ``docker exec <container> python manage.py migrate
    --noinput``. Needed because the dev entrypoint skips ``migrate`` on every
    restart after the first (see ``_classify``).
``npm_build(container)`` -> ``docker exec <container> npm run build``. The
    bundle behind the tunnel is pre-built; the Vite dev server only serves
    the in-container ports.
``wait_healthy(container, timeout)`` -> polls ``docker inspect --format
    {{.State.Health.Status}}`` every 5 s until ``healthy``; ``unhealthy``
    raises immediately, so does the timeout. The django service declares a
    ``curl -f /healthz/`` healthcheck at 15 s intervals, so "healthy" means
    Django answered, not merely that the process exists.

Every default returns ``0`` or raises :class:`ActionFailed` with the action
name, the exit code and the LAST lines of combined output — the sync log
is the only place a human will read this, so the tail travels with the
error instead of dying in the supervisor's discarded stdout. That includes
the ways a subprocess can fail to RUN: a missing ``docker`` binary or a hung
``docker inspect`` surface as ``ActionFailed`` too, never as a bare
``OSError`` / ``TimeoutExpired`` — an exception the engine does not
recognise would bypass its retry gate (reproduced 2026-09-05: the same
rebuild re-ran on every tick with nothing recorded).

BUDGETS AND THE OUTER TIMEOUT
-----------------------------
The budgets below are the REAL bounds; the job's ``/usr/bin/timeout`` head
(``scitex_hub._jobs.HARD_TIMEOUT_SEC``) is only a backstop and MUST exceed
their worst-case sum (``_sync.WORST_CASE_TICK_SEC``, pinned by a test).
Before 2026-09-05 it did not: 2400 + 600 + 900 + 900 = 4800 s of budgets
under a 2700 s outer kill, so a slow-but-alive rebuild was SIGTERMed by the
outer timeout — which records nothing — instead of timing out inside, where
the failure is recorded and eventually held.
"""

from __future__ import annotations

import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

__all__ = [
    "ActionFailed",
    "Actions",
    "EXEC_TIMEOUT_SEC",
    "HEALTH_TIMEOUT_SEC",
    "REBUILD_TIMEOUT_SEC",
    "RELOAD_TIMEOUT_SEC",
    "tail_of",
]

#: ``make ENV=dev reload``: a recreate takes seconds; 15 min means wedged.
RELOAD_TIMEOUT_SEC = 900
#: ``make ENV=dev YES=1 rebuild``: measured 10-25 min on compute-03.
REBUILD_TIMEOUT_SEC = 2_400
#: One ``docker exec`` (migrate / npm run build) in the dev container; a
#: dev-DB migrate or a Vite build past 10 min is not slow, it is stuck.
EXEC_TIMEOUT_SEC = 600
#: The django healthcheck runs ``curl -f /healthz/`` every 15 s.
HEALTH_TIMEOUT_SEC = 600
#: One ``docker inspect``; local, instantaneous unless the daemon is wedged.
_INSPECT_TIMEOUT_SEC = 60
_HEALTH_POLL_SEC = 5
_TAIL_LINES = 40


class ActionFailed(RuntimeError):
    """An action exited non-zero, timed out, or the container never got healthy."""

    def __init__(self, action: str, rc: int, tail: str) -> None:
        self.action = action
        self.rc = rc
        self.tail = tail.strip()
        super().__init__(f"{action} failed (rc={rc}): {self.tail or '<no output>'}")


def tail_of(text: str, lines: int = _TAIL_LINES) -> str:
    """The last ``lines`` lines of ``text`` (what a human wants to see first)."""
    return "\n".join(text.strip().splitlines()[-lines:])


def _run_action(action: str, argv: list[str], *, cwd: Path | None, timeout: int) -> int:
    try:
        completed = subprocess.run(
            argv,
            cwd=str(cwd) if cwd else None,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        out = (
            exc.stdout.decode() if isinstance(exc.stdout, bytes) else (exc.stdout or "")
        )
        raise ActionFailed(
            action, 124, f"timed out after {timeout}s\n{tail_of(out)}"
        ) from exc
    except OSError as exc:
        raise ActionFailed(action, 127, f"could not start {argv[0]}: {exc}") from exc
    if completed.returncode != 0:
        raise ActionFailed(
            action, completed.returncode, tail_of(completed.stdout or "")
        )
    return 0


def reload(clone: Path) -> int:
    """``make ENV=dev reload`` — recreate the django service from the current image."""
    return _run_action(
        "reload", ["make", "ENV=dev", "reload"], cwd=clone, timeout=RELOAD_TIMEOUT_SEC
    )


def rebuild(clone: Path) -> int:
    """``make ENV=dev YES=1 rebuild`` — build, preflight and swap the image."""
    return _run_action(
        "rebuild",
        ["make", "ENV=dev", "YES=1", "rebuild"],
        cwd=clone,
        timeout=REBUILD_TIMEOUT_SEC,
    )


def migrate(container: str) -> int:
    """``docker exec <container> python manage.py migrate --noinput``."""
    return _run_action(
        "migrate",
        ["docker", "exec", container, "python", "manage.py", "migrate", "--noinput"],
        cwd=None,
        timeout=EXEC_TIMEOUT_SEC,
    )


def npm_build(container: str) -> int:
    """``docker exec <container> npm run build`` — refresh the served TS bundle."""
    return _run_action(
        "npm_build",
        ["docker", "exec", container, "npm", "run", "build"],
        cwd=None,
        timeout=EXEC_TIMEOUT_SEC,
    )


def health_status(container: str) -> str:
    """One ``docker inspect`` of the health status; ``""`` while the container is absent.

    During ``--force-recreate`` the old container is removed before the new
    one exists, so a failed inspect is "not yet", not "broken". A ``docker``
    binary that cannot be started, or an inspect that hangs, IS broken and
    raises :class:`ActionFailed` (rc 127 / 124) so the engine records it.
    """
    argv = ["docker", "inspect", "--format", "{{.State.Health.Status}}", container]
    try:
        completed = subprocess.run(
            argv,
            capture_output=True,
            text=True,
            timeout=_INSPECT_TIMEOUT_SEC,
            check=False,
        )
    except OSError as exc:
        raise ActionFailed(
            "wait_healthy", 127, f"could not start {argv[0]}: {exc}"
        ) from exc
    except subprocess.TimeoutExpired as exc:
        raise ActionFailed(
            "wait_healthy",
            124,
            f"docker inspect {container} hung for {_INSPECT_TIMEOUT_SEC}s",
        ) from exc
    if completed.returncode != 0:
        return ""
    return completed.stdout.strip()


def wait_healthy(container: str, timeout: int = HEALTH_TIMEOUT_SEC) -> None:
    """Poll until ``container`` reports ``healthy``; raise on ``unhealthy`` or timeout."""
    deadline = time.monotonic() + timeout
    last = ""
    while time.monotonic() < deadline:
        last = health_status(container)
        if last == "healthy":
            return
        if last == "unhealthy":
            raise ActionFailed("wait_healthy", 1, f"{container} reports unhealthy")
        time.sleep(_HEALTH_POLL_SEC)
    raise ActionFailed(
        "wait_healthy",
        124,
        f"{container} not healthy after {timeout}s (last status: {last or 'absent'})",
    )


@dataclass
class Actions:
    """The injectable action set; defaults shell out as documented above."""

    reload: Callable[[Path], int] = field(default=reload)
    rebuild: Callable[[Path], int] = field(default=rebuild)
    migrate: Callable[[str], int] = field(default=migrate)
    npm_build: Callable[[str], int] = field(default=npm_build)
    wait_healthy: Callable[..., None] = field(default=wait_healthy)


# EOF
