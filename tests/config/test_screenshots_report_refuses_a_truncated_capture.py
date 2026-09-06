#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""A truncated screenshot capture must not read as a clean measurement.

WHY THIS TEST EXISTS. Measured 2026-09-06 on three consecutive develop pushes
(runs 34030453842 / 34031946558 / 34039423420): ``Capture screenshots`` was
killed at 22-24 minutes by the job's ``timeout-minutes``, and the
``Content report`` step then ran over the partial output in ZERO SECONDS and
exited 0. The run's own conclusion was ``cancelled`` -- indistinguishable from a
human pressing cancel, which is exactly what I assumed on first reading.

So nothing anywhere said the artifact was partial. A P1 card
(hub-capture-records-browser-errors-but-asserts-nothing-20260817) was waiting on
two defects observable ONLY in that artifact, and would have waited forever: a
card blocked on a measurement that stopped running looks identical to a card
blocked on slow progress.

WHAT IS ASSERTED. The shell is EXTRACTED FROM THE WORKFLOW and executed, rather
than restated here. A test that re-typed the logic would keep passing after
someone edited the real step -- the drift this file exists to prevent. The only
substitution is the ``${{ steps.capture.outcome }}`` expression, which only
GitHub can expand.
"""

from __future__ import annotations

import re
import shlex
import subprocess

import pytest
import yaml

from ._compose_helpers import REPO_ROOT

WORKFLOW = REPO_ROOT / ".github" / "workflows" / "screenshots.yml"
OUTCOME_EXPR = "${{ steps.capture.outcome }}"
REPORT_RELPATH = "GITIGNORED/e2e_screenshots/content-report.txt"
EXIT_MARKER = "___SCRIPT_EXIT="


def _job():
    return yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))["jobs"]["screenshots"]


def _step(name: str) -> dict:
    for step in _job()["steps"]:
        if step.get("name") == name:
            return step
    raise AssertionError(
        f"no step named {name!r} in {WORKFLOW.name}. If it was renamed, this "
        "gate is no longer watching the thing it claims to."
    )


def _run_report(outcome: str, tmp_path, report_text: str | None):
    """Execute the REAL Content report script with a given capture outcome."""
    script = _step("Content report")["run"].replace(OUTCOME_EXPR, outcome)
    if report_text is not None:
        report = tmp_path / REPORT_RELPATH
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text(report_text)
    # The exit status is read INSIDE the shell, not from Popen.returncode.
    #
    # apps/workspace/console_app/views/terminal/consumer.py installs a
    # process-wide SIGCHLD handler AT IMPORT TIME that calls
    # os.waitpid(-1, WNOHANG) -- ANY child, not just its own PTYs. Once any
    # test in this run has imported the URLconf, that reaper collects
    # subprocess.run's child first and Popen.wait() reports 0 no matter what
    # the process actually exited with. Measured 2026-09-06: this file passed
    # alone and failed in a full tests/config run for exactly that reason, and
    # `bash -c "exit 1"` returned 0.
    #
    # That defect is carded separately. Reading `$?` in an outer shell is not a
    # workaround for it -- it is the correct measurement either way, because it
    # asks the shell what the script returned instead of asking Python what it
    # managed to reap.
    wrapped = f"bash -c {shlex.quote(script)}; echo {EXIT_MARKER}$?"
    proc = subprocess.run(
        ["bash", "-c", wrapped],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=60,
    )
    match = re.search(rf"^{re.escape(EXIT_MARKER)}(\d+)$", proc.stdout, re.M)
    assert match, (
        "the exit marker is missing, so the script's status was never "
        f"observed. stdout={proc.stdout!r} stderr={proc.stderr!r}"
    )
    return proc, int(match.group(1))


# ---------------------------------------------------------------------------
# Controls
# ---------------------------------------------------------------------------


def test_the_capture_step_is_addressable():
    """The report reads steps.capture.outcome; that id must exist."""
    assert _step("Capture screenshots").get("id") == "capture", (
        "the capture step lost its `id: capture`, so "
        f"{OUTCOME_EXPR} silently resolves to an empty string and the "
        "truncation check below can never fire correctly."
    )


def test_the_report_still_consults_the_capture_outcome():
    """Extraction control: if this expression is gone, the test proves nothing."""
    assert OUTCOME_EXPR in _step("Content report")["run"], (
        f"the Content report step no longer references {OUTCOME_EXPR}. Either "
        "the truncation check was removed, or it was rewritten in a way this "
        "gate cannot see -- both mean a partial capture can read as clean again."
    )


def test_a_completed_capture_still_passes(tmp_path):
    """POSITIVE CONTROL. A check that always failed would satisfy the rule below."""
    proc, status = _run_report("success", tmp_path, "Cards  OK  11 images\n")

    assert status == 0, (
        f"a SUCCESSFUL capture was rejected. stdout={proc.stdout!r} "
        f"stderr={proc.stderr!r}"
    )
    assert "TRUNCATED" not in (tmp_path / REPORT_RELPATH).read_text()


# ---------------------------------------------------------------------------
# The rule
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("outcome", ["cancelled", "failure"])
def test_a_truncated_capture_fails_the_step(outcome, tmp_path):
    proc, status = _run_report(outcome, tmp_path, "Cards  OK  11 images\n")

    assert status != 0, (
        f"capture outcome {outcome!r} left the Content report GREEN. That is "
        "the exact 2026-09-06 failure: a partial artifact presented as a "
        "complete measurement."
    )
    assert "::error::" in proc.stdout, (
        "the log carries no ::error:: annotation, so whoever opens the run "
        "sees a cancelled job and no statement that the capture was truncated."
    )


@pytest.mark.parametrize(
    "outcome,banner",
    [("cancelled", "TRUNCATED"), ("failure", "INCOMPLETE")],
)
def test_the_artifact_distinguishes_killed_from_failed(outcome, banner, tmp_path):
    """A finished-but-failing capture must NOT be labelled unmeasured.

    GitHub reports `cancelled` when the job budget kills the step mid-run and
    `failure` when it ran and its assertions failed. Measured on this PR's own
    CI run: the capture COMPLETED in 28:55 with 56 real failures, and the first
    draft of this workflow called that "TRUNCATED ... every absence is
    UNMEASURED". The pages had been measured. Calling a finished measurement
    unmeasured is the same class of error as calling a partial one clean, so
    the two get different words.
    """
    _run_report(outcome, tmp_path, "Cards  OK  11 images\n")

    text = (tmp_path / REPORT_RELPATH).read_text()
    assert banner in text, (
        f"capture outcome {outcome!r} should be reported as {banner!r}; the "
        f"artifact says: {text!r}"
    )


@pytest.mark.parametrize("outcome", ["cancelled", "failure"])
def test_the_artifact_itself_records_that_it_is_not_clean(outcome, tmp_path):
    """The log is gone in a week; the artifact is what cards read later."""
    _run_report(outcome, tmp_path, "Cards  OK  11 images\n")

    text = (tmp_path / REPORT_RELPATH).read_text()
    assert ("TRUNCATED" in text) or ("INCOMPLETE" in text), (
        "the uploaded content report does not say it is partial. Anyone "
        "reading the artifact later -- which is how the blocked P1 card "
        "consumes it -- cannot tell a clean run from a killed one."
    )
    assert "Cards  OK  11 images" in text, (
        "the truncation banner destroyed the partial measurement. Keep it: "
        "half a measurement labelled half is useful; deleting it is not."
    )


def test_a_truncated_capture_with_no_report_at_all_still_fails(tmp_path):
    """The capture can die before writing anything. That must not read as clean."""
    _proc, status = _run_report("cancelled", tmp_path, None)

    assert status != 0
    assert "TRUNCATED" in (tmp_path / REPORT_RELPATH).read_text(), (
        "no report file existed, so the step must CREATE one carrying the "
        "banner -- otherwise the artifact is simply empty, which reads as "
        "'nothing to report'."
    )
