#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The parallel pytest-matrix must stay parallel, and must not lose a gate.

CARD: hub-ci-use-available-cores-time-to-signal-20260911 (P1).

WHY THIS FILE EXISTS. On 2026-09-10 the three pytest-matrix legs ran
521s / 897s / 676s wall-clock on PR #771 (run 34541827131, jobs
103085957832 / 103085957666 / 103085957917), of which the "Run tests" step
alone was 469s on py3.11 -- all of it single-process pytest, on a runner with
4 idle vCPUs, while queue delay was only 2-68s. The wall time that delays a
production launch was the serial run, not the queue.

The fix is one flag pair (``-n 4 --dist loadfile``) plus the plugin declaration
that makes the flag exist. Both live in files nothing in the suite reads, which
is exactly the shape that decays: drop the extra from pyproject and each leg
exits 4 with "unrecognized arguments: -n 4"; delete the flags and the matrix
silently returns to 8-15 minutes per PR with every check green. Neither failure
is visible in a green tick, so the properties are asserted here rather than
left to a comment.

WHAT IS DELIBERATELY NOT ASSERTED: the worker COUNT. 4 is right for a
4-vCPU hosted runner and wrong for a 32-core self-hosted one, so pinning it
would make a future routing change fail a test instead of raising a number.
What is asserted is that it is an integer (>= 2) and not ``auto``: ``auto``
reads the host CPU count, so one line would spawn 4 workers on GitHub's runner
and 32+ on a big self-hosted runner, each opening its own test database --
a behaviour that changes with the machine rather than with the repo.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

REPO = Path(__file__).resolve().parents[2]
WORKFLOW = (
    REPO / ".github" / "workflows" / "pytest-matrix-on-ubuntu-py3-11-3-12-3-13.yml"
)

#: The three required status checks on main and develop come from the JOB name
#: built out of this list, so losing a version does not just shrink coverage --
#: it stops publishing a required context.
REQUIRED_PYTHON_VERSIONS = ["3.11", "3.12", "3.13"]


def _workflow() -> dict:
    """The matrix workflow as parsed YAML.

    Raises rather than returning ``{}``: a moved or renamed file must break
    these assertions, not satisfy them vacuously.
    """
    assert WORKFLOW.is_file(), (
        f"{WORKFLOW} does not exist. If the matrix workflow moved, this guard "
        "travels with it -- otherwise it stops guarding anything."
    )
    return yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))


def _job() -> dict:
    data = _workflow()
    jobs = data.get("jobs") or {}
    assert "test" in jobs, f"no 'test' job in {WORKFLOW.name}: {sorted(jobs)}"
    return jobs["test"]


def _step_named(fragment: str) -> dict:
    for step in _job().get("steps") or []:
        if fragment.lower() in str(step.get("name", "")).lower():
            return step
    raise AssertionError(
        f"no step whose name contains {fragment!r} in {WORKFLOW.name}. The "
        "guard reads that step's command; a renamed step would otherwise make "
        "every assertion below vacuous."
    )


def _run_command() -> str:
    command = str(_step_named("Run tests").get("run") or "")
    # CONTROL: the parser saw a real command. An empty or unrelated string
    # would make every `in` assertion below pass for the wrong reason.
    assert "pytest" in command, (
        "the 'Run tests' step does not invoke pytest, so this guard is reading "
        f"the wrong thing:\n{command}"
    )
    return command


def test_pytest_runs_with_an_explicit_worker_count() -> None:
    # Arrange
    command = _run_command()
    # Act
    match = re.search(r"(?:^|\s)-n\s+(\S+)", command)
    # Assert
    assert match is not None, (
        "the matrix runs pytest with no `-n` flag, so every leg is "
        f"single-process again -- 469s of the 521s it takes to learn a result:\n"
        f"{command}"
    )
    workers = match.group(1)
    assert workers != "auto", (
        "`-n auto` sizes itself from the host CPU count, so the same line "
        "spawns 4 workers on the hosted runner and 32+ on a self-hosted one, "
        "each with its own test database. State the number."
    )
    assert workers.isdigit() and int(workers) >= 2, (
        f"`-n {workers}` is not a worker count that can parallelise anything."
    )


def test_the_loader_keeps_each_file_on_one_worker() -> None:
    # Arrange
    command = _run_command()
    # Assert — the suite had never run in parallel before this change, so
    # intra-file ordering and module-level state are preserved by keeping every
    # file whole on one worker. Cross-file parallelism is where the size is.
    assert "--dist loadfile" in command, (
        "the matrix parallelises with the default `--dist load`, which spreads "
        "a single file's tests across workers. This suite has never run in "
        f"parallel; that is a semantics change, not a speed change:\n{command}"
    )


def test_the_plugin_that_provides_the_flag_is_installed() -> None:
    # Arrange — the flag is only legal if pytest-xdist is in the same install
    # graph the workflow uses.
    install = str(_step_named("Install dependencies").get("run") or "")
    # Control: the install step must name the extras it installs, or the
    # declaration check below cannot be tied to anything.
    assert ".[all" in install, (
        f"the install step no longer installs an extra, so pytest-xdist cannot "
        f"be traced to it:\n{install}"
    )
    pyproject = (REPO / "pyproject.toml").read_text(encoding="utf-8")
    # Act
    declared_in_all = (
        re.search(r"pytest-xdist[^\n]*", pyproject) is not None
        and "pytest-xdist>=3.6" in pyproject
    )
    # Assert
    assert declared_in_all, (
        "pytest-xdist is not declared in pyproject.toml. The matrix installs "
        '`-e ".[all,dev]"`, so without the declaration every leg exits 4 with '
        '"unrecognized arguments: -n 4" -- a whole matrix red because one '
        "plugin went missing."
    )


def test_the_gates_the_speedup_must_not_weaken_are_still_there() -> None:
    # Arrange
    command = _run_command()
    job = _job()
    # Act
    versions = (job.get("strategy") or {}).get("matrix", {}).get("python-version")
    services = job.get("services") or {}
    # Assert — the three required status checks are built from this list.
    assert versions == REQUIRED_PYTHON_VERSIONS, (
        f"the python-version matrix is {versions}, not "
        f"{REQUIRED_PYTHON_VERSIONS}. Those three job names ARE the required "
        "contexts on main and develop; dropping one stops publishing a gate."
    )
    # Assert — coverage still runs, now over parallel workers.
    assert "--cov=src/scitex_hub" in command, (
        f"coverage was dropped while making the suite faster:\n{command}"
    )
    # Assert — the database the workers each create their own copy of.
    assert "postgres" in services, (
        "the postgres service is gone, so `_gwN` test databases have nowhere "
        "to be created and the legs would measure a different engine than "
        "production runs."
    )


@pytest.mark.parametrize("marker", ["-n 4", "--dist loadfile"])
def test_the_flags_are_on_the_same_line_as_pytest(marker: str) -> None:
    # Arrange / Act / Assert — prose above the command mentions these flags too
    # (that is what makes the change legible). A guard that searched the whole
    # step would pass on the comment alone after someone deleted the flag.
    run_lines = [
        line.strip()
        for line in _run_command().splitlines()
        if line.strip().startswith(".venv/bin/python")
    ]
    assert run_lines, "no `.venv/bin/python -m pytest` invocation found"
    assert any(marker in line for line in run_lines), (
        f"{marker!r} appears in prose but not on the pytest command line: {run_lines}"
    )
