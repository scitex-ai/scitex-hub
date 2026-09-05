#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: tests/scitex_hub/_jobs/test_dev_preview_sync_is_a_declared_job.py

"""The develop-preview sync is a DECLARED federated job, placed on ONE host.

Fleet doctrine (constitution, operator ruling 2026-08-20): every periodic
SciTeX job is a scitex-dev ``JobSpec`` published through the
``scitex_dev.jobs`` entry-point group and run by the host supervisor;
placement is the SEPARATE ``scitex_dev.host_placement`` group, and an
UNPLACED job arms on every supervisor host — prod (nas-03) included. Each
test here pins one clause of that contract so the job cannot silently stop
being a job, stop being bounded, or start running where the preview is not:

* ``provide_jobs`` returns exactly one spec, package-prefixed, ``kind="timer"``,
  firing every 2 minutes;
* the command is self-bounding (a literal ``/usr/bin/timeout <HARD_TIMEOUT_SEC>``
  head — the runner does NOT enforce ``timeout_sec``) and ends in the exact
  verb the supervisor must run against the preview clone;
* that outer bound EXCEEDS the verb's worst-case sum of inner budgets
  (``WORST_CASE_TICK_SEC``): the inner timeouts record the failure the retry
  gate needs, the outer SIGTERM records nothing — so the outer one must never
  be the first to fire (at 2700 s over 4800 s of budgets it was);
* the command's SECOND token is absolute when the sibling console script
  exists, because ``resolve_execstart`` absolutises only the first token;
* ``provide_placement`` pins the job to ``scitex-compute-03`` and names the
  spec it places;
* importing ``scitex_hub._jobs`` in a FRESH interpreter does not import
  ``scitex_dev`` — entry-point metadata must stay loadable on a scitex-dev
  that predates the jobs contract;
* ``pyproject.toml`` declares both groups and each target string resolves,
  by importlib, to a callable.

No mocks: the providers are called for real (scitex-dev is a declared
dependency), the subprocess is a real interpreter, and the toml is the real
file resolved from this test's location.
"""

from __future__ import annotations

import importlib
import os
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest

from scitex_hub._dev_preview._sync import WORST_CASE_TICK_SEC
from scitex_hub._jobs import (
    CADENCE,
    HARD_TIMEOUT_SEC,
    JOB_NAME,
    PREVIEW_CLONE,
    PREVIEW_HOST,
    provide_jobs,
    provide_placement,
    scitex_hub_console_script,
)

WORKTREE_ROOT = Path(__file__).resolve().parents[3]
PYPROJECT = WORKTREE_ROOT / "pyproject.toml"

ENTRY_POINTS = [
    ("scitex_dev.jobs", "scitex_hub._jobs:provide_jobs"),
    ("scitex_dev.host_placement", "scitex_hub._jobs:provide_placement"),
]


def test_provide_jobs_returns_exactly_one_spec():
    """hub declares ONE periodic job, no more and no fewer."""
    # Arrange
    expected_count = 1
    # Act
    jobs = provide_jobs()
    # Assert
    assert len(jobs) == expected_count


def test_job_is_named_after_the_package():
    """The unit name the supervisor derives comes from this package-prefixed name."""
    # Arrange
    expected = "scitex-hub-dev-preview-sync"
    # Act
    job = provide_jobs()[0]
    # Assert
    assert (job.name, JOB_NAME) == (expected, expected)


def test_job_kind_is_timer():
    """A periodic job is a timer, not a service."""
    # Arrange
    expected = "timer"
    # Act
    job = provide_jobs()[0]
    # Assert
    assert job.kind == expected


def test_job_fires_every_two_minutes():
    """A merge must be visible on the preview within ~2 min (the operator loop)."""
    # Arrange
    expected = "2min"
    # Act
    job = provide_jobs()[0]
    # Assert
    assert (job.on_unit_active_sec, CADENCE) == (expected, expected)


def test_command_is_bounded_by_a_literal_timeout_head():
    """The runner ignores ``timeout_sec``; only a literal ``/usr/bin/timeout`` bounds a hung rebuild."""
    # Arrange
    expected_prefix = f"/usr/bin/timeout {HARD_TIMEOUT_SEC} "
    # Act
    job = provide_jobs()[0]
    # Assert
    assert (job.command.startswith(expected_prefix), job.timeout_sec) == (
        True,
        HARD_TIMEOUT_SEC,
    )


def test_hard_timeout_exceeds_the_ticks_worst_case_budget():
    """The outer kill records nothing; every inner timeout does — so inner must fire first."""
    # Arrange
    outer = HARD_TIMEOUT_SEC
    # Act
    inner = WORST_CASE_TICK_SEC
    # Assert
    assert outer > inner, f"outer {outer}s must exceed worst-case inner {inner}s"


def test_command_ends_with_the_sync_verb_on_the_preview_clone():
    """The supervisor runs exactly the verb the CLI exposes, against the real clone."""
    # Arrange
    expected_suffix = "dev-preview sync --clone /home/ywatanabe/proj/scitex-cloud"
    # Act
    job = provide_jobs()[0]
    # Assert
    assert (job.command.endswith(expected_suffix), PREVIEW_CLONE) == (
        True,
        "/home/ywatanabe/proj/scitex-cloud",
    )


@pytest.mark.skipif(
    not Path(sys.executable).with_name("scitex-hub").is_file(),
    reason="no scitex-hub console script beside this interpreter",
)
def test_command_second_token_is_absolute_when_the_sibling_script_exists():
    """``resolve_execstart`` absolutises only argv[0]; argv[2] must already be absolute."""
    # Arrange
    expected = str(Path(sys.executable).with_name("scitex-hub"))
    # Act
    second_token = provide_jobs()[0].command.split()[2]
    # Assert
    assert (second_token, scitex_hub_console_script()) == (expected, expected)


def test_placement_pins_the_job_to_compute_03():
    """Without this record the job would arm on prod, which has no preview stack."""
    # Arrange
    expected_hosts = ("scitex-compute-03",)
    # Act
    record = provide_placement()[0]
    # Assert
    assert (record.hosts, PREVIEW_HOST) == (expected_hosts, "scitex-compute-03")


def test_placement_names_the_declared_job():
    """A placement for a differently-spelled name would place nothing."""
    # Arrange
    job_name = provide_jobs()[0].name
    # Act
    record = provide_placement()[0]
    # Assert
    assert record.job == job_name


def test_importing_the_jobs_module_does_not_import_scitex_dev():
    """Entry-point metadata must load on a scitex-dev that predates the jobs contract."""
    # Arrange
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join(
        [str(WORKTREE_ROOT / "src"), env.get("PYTHONPATH", "")]
    ).rstrip(os.pathsep)
    probe = "import sys, scitex_hub._jobs; print('scitex_dev' in sys.modules)"
    # Act
    completed = subprocess.run(
        [sys.executable, "-c", probe],
        capture_output=True,
        text=True,
        env=env,
        timeout=120,
        check=True,
    )
    # Assert
    assert completed.stdout.strip() == "False"


@pytest.mark.parametrize("group,target", ENTRY_POINTS)
def test_pyproject_declares_the_entry_point(group: str, target: str):
    """The provider is only a provider if pyproject publishes it under the group."""
    # Arrange
    data = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
    # Act
    declared = data["project"]["entry-points"][group]["scitex-hub"]
    # Assert
    assert declared == target


@pytest.mark.parametrize("group,target", ENTRY_POINTS)
def test_entry_point_target_resolves_to_a_callable(group: str, target: str):
    """A typo in the target string would fail only at supervisor discovery time."""
    # Arrange
    module_name, attr = target.split(":")
    # Act
    resolved = getattr(importlib.import_module(module_name), attr)
    # Assert
    assert callable(resolved)


# EOF
