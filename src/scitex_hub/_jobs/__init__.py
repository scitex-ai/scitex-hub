#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: src/scitex_hub/_jobs/__init__.py

"""Declare Hub timers and their host placement through ``scitex_dev.jobs``.

The preview timer targets :data:`PREVIEW_CLONE` on :data:`PREVIEW_HOST`.
Its command includes ``--yes`` for unattended operation, and a literal
``/usr/bin/timeout`` bounds the complete tick. The CLI performs its own
clone checks, locking, retries, logging and change-specific follow-up.
Source-dirt timers report structured metadata for the named long-lived trees.

These providers describe jobs; they do not prove a supervisor has loaded
or run them. Verify current host placement, checkout state, execution
records and the served revision before reporting preview delivery. The
two-minute cadence does not guarantee a deployment deadline.

The console script is resolved next to the provider's interpreter because
it follows ``timeout`` in the command. Dev imports stay inside provider
functions so importing the constants does not start or import a supervisor.
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
    "SOURCE_DIRT_CADENCE",
    "SOURCE_DIRT_CHECKOUTS",
    "SOURCE_DIRT_TIMEOUT_SEC",
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

#: Intended preview checkout; verify its actual branch and dirt before delivery.
PREVIEW_CLONE = "/home/ywatanabe/proj/scitex-hub"

#: Declared ``OnUnitActiveSec`` cadence; execution and delivery need verification.
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

# Long-lived Hub trees.  Each tuple is (stable identity suffix, supervisor
# host, absolute checkout).  Do not add ephemeral CI/worktree paths here.
SOURCE_DIRT_CHECKOUTS = (
    ("compute-03", "scitex-compute-03", "/home/ywatanabe/proj/scitex-hub"),
    ("nas-03", "scitex-nas-03", "/home/ywatanabe/proj/scitex-hub"),
)
SOURCE_DIRT_CADENCE = "15min"
SOURCE_DIRT_TIMEOUT_SEC = 300


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
        f"dev-preview sync --yes --clone {PREVIEW_CLONE}"
    )
    jobs = [
        JobSpec(
            name=JOB_NAME,
            kind="timer",
            schedule="",
            command=command,
            description=(
                "Keep the develop preview on compute-03 current: fast-forward "
                f"{PREVIEW_CLONE} to origin/develop every {CADENCE} and run the "
                "follow-up the change needs (reload / rebuild / migrate / npm "
                "build). Verify the served revision after each successful tick."
            ),
            on_boot_sec="2min",
            on_unit_active_sec=CADENCE,
            timeout_sec=HARD_TIMEOUT_SEC,
            restart_policy="no",
        )
    ]
    python = sys.executable
    for label, _host, checkout in SOURCE_DIRT_CHECKOUTS:
        jobs.append(
            JobSpec(
                name=f"scitex-hub-source-dirt-{label}",
                kind="timer",
                schedule="",
                command=(
                    f"/usr/bin/timeout {SOURCE_DIRT_TIMEOUT_SEC} {python} -m "
                    "scitex_hub._jobs.source_dirt_tripwire "
                    f"--checkout {checkout}"
                ),
                description=(
                    "Detect vanished/staged/untracked source in the long-lived "
                    f"Hub checkout at {checkout}; emit only structured metadata."
                ),
                on_boot_sec="5min",
                on_unit_active_sec=SOURCE_DIRT_CADENCE,
                timeout_sec=SOURCE_DIRT_TIMEOUT_SEC,
                restart_policy="no",
            )
        )
    return jobs


def provide_placement() -> list[PlacementRecord]:
    """Return hub's placement records (``scitex_dev.host_placement`` provider).

    ``PlacementRecord`` has no public re-export in scitex-dev (its own
    provider imports it from ``scitex_dev.jobs._placement``), so this does
    the same. Without this record the job would arm on every supervisor
    host — including prod on nas-03, which has no ``scitex-hub-dev`` stack
    and no clone at :data:`PREVIEW_CLONE`.
    """
    from scitex_dev.jobs._placement import PlacementRecord

    records = [PlacementRecord(job=JOB_NAME, hosts=(PREVIEW_HOST,))]
    records.extend(
        PlacementRecord(job=f"scitex-hub-source-dirt-{label}", hosts=(host,))
        for label, host, _checkout in SOURCE_DIRT_CHECKOUTS
    )
    return records


# EOF
