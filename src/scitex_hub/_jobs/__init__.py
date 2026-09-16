#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: src/scitex_hub/_jobs/__init__.py

"""hub's federated scheduled jobs (``scitex_dev.jobs``) and where they run.

WHY THIS JOB EXISTS
-------------------
Operator ask, 2026-09-02: 「本番反映の前に develop で確認させてもらえると開発が早い」
— *let me check develop before it reaches production, development goes
faster*. The develop preview of scitex-hub already serves on
``scitex-compute-03`` (docker compose project ``scitex-hub-dev``, from the
bind-mounted clone :data:`PREVIEW_CLONE` on branch ``develop``), and
``runserver`` autoreload + the template watcher make Python / template / CSS
edits live with no action at all. What was missing is the PULL: nothing
updated the clone, so on 2026-09-05 it was measured 10 days behind
``origin/develop`` — the preview was "live" and showed nothing new.

This module declares ONE periodic job that closes that gap:

* ``scitex-hub-dev-preview-sync`` (``kind="timer"``, every :data:`CADENCE`)
  runs ``scitex-hub dev-preview sync --clone <PREVIEW_CLONE>``. The verb
  fast-forwards the clone to ``origin/develop``, classifies what changed,
  and does exactly the follow-up the change needs — nothing for ``.py`` /
  ``.html`` / ``.css`` (autoreload), ``make ENV=dev reload`` for compose /
  entrypoint / env changes, ``make ENV=dev YES=1 rebuild`` for Dockerfile /
  dependency changes, ``manage.py migrate`` for new migrations (the dev
  entrypoint SKIPS migrate on a hot-reload restart — see
  :mod:`scitex_hub._dev_preview._classify`), and ``npm run build`` for
  TypeScript (the bundle behind the tunnel is pre-built, not served by the
  Vite dev server). See :mod:`scitex_hub._dev_preview` for the mechanics.

THE OPERATOR LOOP THIS BUYS
---------------------------
1. Merge a PR to ``develop``.
2. Within ~2 minutes it is live on ``compute-03-net.scitex.ai``; a
   TypeScript change rebuilds the bundle automatically, a migration is
   applied automatically, a Dockerfile change rebuilds the image (10-25 min).

FLEET DOCTRINE (constitution, operator ruling 2026-08-20)
---------------------------------------------------------
Every periodic SciTeX job is a scitex-dev ``JobSpec`` published through the
``scitex_dev.jobs`` entry-point group and run by the host supervisor's
PeriodicRunner (``scitex-dev ecosystem run``); cron is retired. Placement is
a SEPARATE entry-point group, ``scitex_dev.host_placement``: an unplaced job
arms on EVERY host, so the :class:`PlacementRecord` returned by
:func:`provide_placement` is what keeps this job off nas-03 (prod) and
compute-04. ``JobSpec`` itself has no host field.

WHAT THE SUPERVISOR DOES WITH THE SPEC (measured on 0.56.3 and 0.59.0)
----------------------------------------------------------------------
* ``argv = shlex.split(resolve_execstart(job.command))`` — only the FIRST
  token is absolutised. Our first token is ``/usr/bin/timeout`` (already
  absolute), so the SECOND token — the ``scitex-hub`` console script — is
  NOT resolved and must be absolute itself. :func:`scitex_hub_console_script`
  computes it from ``sys.executable`` at provider-call time; the provider
  runs inside the supervisor's interpreter, so on compute-03 this yields
  ``/home/ywatanabe/.env-sac/bin/scitex-hub``.
* ``timeout_sec`` is recorded but NOT enforced by the runner — hence the
  fleet convention of a literal ``/usr/bin/timeout N`` head, mirrored in
  ``timeout_sec`` so ``list`` output tells the truth.
* stdout/stderr are discarded (0.56.3) or captured and logged only on
  failure (0.59.0), so the verb keeps its own JSONL log under
  ``~/.scitex/hub/runtime/dev-preview-sync/``.
* A tick whose previous run is still running is SKIPPED
  (``skipped_still_running``); the verb also holds an ``flock`` so a
  manual run and a timer run cannot interleave.

INSTALL / REFRESH ON THE HOST (compute-03)
------------------------------------------
scitex-hub is already installed EDITABLE in the supervisor's venv
(``/home/ywatanabe/.env-sac`` -> ``/home/ywatanabe/proj/scitex-hub``), so
after this lands on ``develop`` the operator step is only::

    ~/.env-sac/bin/pip install -e /home/ywatanabe/proj/scitex-hub --no-deps

The ``pip install -e`` rewrites the dist-info ``entry_points.txt`` (a pure
``git pull`` does not). No restart or SIGHUP is needed: the supervisor
re-discovers TIMER jobs on every 1 Hz ``tick()``
(``self._periodic.tick(self.discover_periodic_jobs())``, 0.56.3), so the
job arms itself within seconds and first fires after ``on_boot_sec``.

HOW TO VERIFY IT IS ARMED — and what does NOT verify it
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
The ONLY witness for a timer job is its execution record::

    rg '"job": "scitex-hub-dev-preview-sync"' \\
        ~/.scitex/dev/runtime/periodic-executions.jsonl | tail -3

A ``"event": "started"`` line within ~2 min, then a ``"event": "finished"``
with ``"exit_code": 0``, is the proof (the file is per host; on compute-03
it held 0 such lines before install, as expected). ``kill -HUP`` is
harmless but proves NOTHING here: on 0.56.3 ``reconcile()`` starts from
``discover_service_jobs()`` (``kind == "service"`` only) and its
``added`` / ``removed`` / ``restarted`` report and ``state.json``
``children`` never mention a timer job — an operator waiting for
``added`` after a SIGHUP would wrongly conclude the install failed.

LAZY IMPORTS, ON PURPOSE
------------------------
``scitex_dev`` is imported inside the provider functions, never at module
import time — the same pattern as scitex-agent-container's
``_jobs/_jobs_plugin.py``. Entry-point metadata must stay loadable on a
scitex-dev that predates the jobs contract, and ``import scitex_hub._jobs``
must never drag the supervisor's package into a process that only wanted
the constants (the tests pin this with a fresh-subprocess check).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - typing only
    from scitex_dev.jobs import JobSpec
    from scitex_dev.jobs._placement import PlacementRecord

__all__ = [
    "CADENCE",
    "HARD_TIMEOUT_SEC",
    "JOB_NAME",
    "PREVIEW_CLONE",
    "PREVIEW_HOST",
    "provide_jobs",
    "provide_placement",
    "scitex_hub_console_script",
]

#: Package-prefixed, hyphens only (the supervisor derives unit names from it).
JOB_NAME = "scitex-hub-dev-preview-sync"

#: The ONE host that serves the develop preview (docker compose project
#: ``scitex-hub-dev``). Named explicitly: host groups are not declared
#: anywhere machine-readable yet, and prod (nas-03) must never run this.
PREVIEW_HOST = "scitex-compute-03"

#: The bind-mounted clone the preview stack serves from (branch ``develop``).
PREVIEW_CLONE = "/home/ywatanabe/proj/scitex-cloud"

#: ``OnUnitActiveSec`` — a merge is visible on the preview within ~2 min.
CADENCE = "2min"

#: 90 min — a BACKSTOP, not the working bound. The real bounds are the
#: verb's own subprocess budgets (fetch 300 + ff-merge 300 + rebuild 2400 +
#: health 600 + migrate 600 + npm build 600 = 4800 s on the worst-case
#: path, plus local git / board slack; ``_sync.WORST_CASE_TICK_SEC``), each
#: of which records the failure so the retry gate can hold a HEAD after
#: ``max_attempts``. This value MUST exceed that sum (a test pins it): at
#: 2700 s it did not, so a slow-but-alive rebuild was SIGTERMed from the
#: outside — where nothing was recorded — and re-run every tick. Enforced by
#: the literal ``/usr/bin/timeout`` head (the runner does not enforce
#: ``timeout_sec``); GNU timeout signals the whole process group, so the
#: in-flight ``make`` dies with the tick rather than being orphaned.
HARD_TIMEOUT_SEC = 5_400


def scitex_hub_console_script() -> str:
    """Return the ABSOLUTE ``scitex-hub`` console script next to ``sys.executable``.

    The supervisor absolutises only the first argv token, and ours is
    ``/usr/bin/timeout``; the console script is the second token and must
    therefore be absolute on its own. The provider runs inside the
    supervisor's interpreter, so its sibling ``bin/`` is where the
    supervisor's own ``pip install -e`` put the script. Falls back to the
    bare name only when no sibling exists (a supervisor whose venv lacks
    scitex-hub — then PATH is the last hope and the log will say 127).
    """
    candidate = Path(sys.executable).with_name("scitex-hub")
    if candidate.is_file() and os.access(candidate, os.X_OK):
        return str(candidate)
    return "scitex-hub"


def provide_jobs() -> list[JobSpec]:
    """Return hub's federated scheduled jobs (``scitex_dev.jobs`` provider).

    Loaded by ``scitex_dev.jobs.discover_jobs()`` through the entry point
    declared in ``pyproject.toml``. ``scitex_dev`` is imported HERE so a
    supervisor that predates the jobs contract never fails at metadata time.
    """
    from scitex_dev.jobs import JobSpec

    command = (
        f"/usr/bin/timeout {HARD_TIMEOUT_SEC} {scitex_hub_console_script()} "
        f"dev-preview sync --clone {PREVIEW_CLONE}"
    )
    return [
        JobSpec(
            name=JOB_NAME,
            kind="timer",
            schedule="",
            command=command,
            description=(
                "Keep the develop preview on compute-03 current: fast-forward "
                f"{PREVIEW_CLONE} to origin/develop every {CADENCE} and run the "
                "follow-up the change needs (reload / rebuild / migrate / npm "
                "build). Operator loop: merge to develop -> live on "
                "compute-03-net.scitex.ai within ~2 min."
            ),
            on_boot_sec="2min",
            on_unit_active_sec=CADENCE,
            timeout_sec=HARD_TIMEOUT_SEC,
            restart_policy="no",
        )
    ]


def provide_placement() -> list[PlacementRecord]:
    """Return hub's placement records (``scitex_dev.host_placement`` provider).

    ``PlacementRecord`` has no public re-export in scitex-dev (its own
    provider imports it from ``scitex_dev.jobs._placement``), so this does
    the same. Without this record the job would arm on every supervisor
    host — including prod on nas-03, which has no ``scitex-hub-dev`` stack
    and no clone at :data:`PREVIEW_CLONE`.
    """
    from scitex_dev.jobs._placement import PlacementRecord

    return [PlacementRecord(job=JOB_NAME, hosts=(PREVIEW_HOST,))]


# EOF
