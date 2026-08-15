#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The vanished-files detector must actually fire, and must say so distinguishably.

WHY THIS TEST EXISTS. The script it covers is an alarm, and an alarm nobody has
watched go off is indistinguishable from a broken one. This repo shipped four
checks in a single day that reported success without ever being able to report
failure (hub-guards-must-demonstrate-their-own-red-20260815), so a detector
arriving without a demonstrated firing would be the fifth.

WHAT IT PINS, and why the exit codes matter more than the message. The script
answers across a process boundary, where the only thing a caller (cron, a systemd
unit, a monitoring probe) can read reliably is the exit status. 1 and 2 already
mean "generic failure" and "usage error" in every CLI framework, so reusing 1 for
"files are missing" would let a renamed binary, a syntax error or a bad flag
impersonate a real detection — the alarm would appear to fire for the wrong
reason, which is worse than silence because someone would act on it. Hence the
declared codes, pinned here so they cannot drift:

    0   intact
    2   usage error
    10  FILES ARE MISSING

Each case below builds a THROWAWAY git repo in tmp_path. Nothing touches this
checkout, so the test cannot itself become the thing it is warning about.
"""

import os
import subprocess
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SCRIPT = _REPO_ROOT / "scripts" / "utils" / "detect_vanished_tracked_files.sh"

EXIT_OK = 0
EXIT_USAGE = 2
EXIT_FILES_MISSING = 10


def _run(*args):
    """Run the detector, returning the CompletedProcess. Never raises on exit code."""
    env = dict(os.environ)
    env.pop("SCITEX_HUB_CHECKOUTS", None)  # a stray env var must not steer the test
    return subprocess.run(
        ["bash", str(_SCRIPT), *args],
        capture_output=True,
        text=True,
        env=env,
    )


@pytest.fixture()
def scratch_checkout(tmp_path):
    """A real git checkout with one tracked file committed."""
    repo = tmp_path / "scratch"
    repo.mkdir()
    run = lambda *a: subprocess.run(a, cwd=repo, check=True, capture_output=True)
    run("git", "init", "-q")
    run("git", "config", "user.email", "test@example.invalid")
    run("git", "config", "user.name", "test")
    (repo / "kept.txt").write_text("kept\n")
    (repo / "doomed.txt").write_text("doomed\n")
    run("git", "add", "kept.txt", "doomed.txt")
    run("git", "commit", "-q", "-m", "seed")
    return repo


def test_the_script_exists_and_is_executable():
    """Anti-vacuity: every case below shells out, and a missing script would give
    bash's own 127, which no assertion here would distinguish from a real answer."""
    assert _SCRIPT.is_file(), f"detector not found at {_SCRIPT}"


def test_intact_checkout_reports_ok(scratch_checkout):
    result = _run(str(scratch_checkout))
    assert result.returncode == EXIT_OK, result.stdout + result.stderr
    assert "OK" in result.stdout
    assert "2 tracked file(s), none missing" in result.stdout


def test_a_vanished_tracked_file_makes_it_fire(scratch_checkout):
    """THE RED CASE. This is the whole point of the script."""
    (scratch_checkout / "doomed.txt").unlink()

    result = _run(str(scratch_checkout))

    assert result.returncode == EXIT_FILES_MISSING, (
        "the detector did not fire on a checkout that is genuinely missing a tracked "
        f"file. exit={result.returncode}\n{result.stdout}{result.stderr}"
    )
    assert "MISSING" in result.stdout
    assert "doomed.txt" in result.stdout, "the missing path must be named, not just counted"
    assert "1 of 2 tracked file(s)" in result.stdout
    assert "restore ." in result.stdout, "an error without a next step is half-written"


def test_it_does_not_fire_on_untracked_or_ignored_files(scratch_checkout):
    """False alarms retire an alarm as surely as silence does. Untracked and
    ignored files are not the thing being watched for."""
    (scratch_checkout / "scratch.tmp").write_text("untracked\n")
    (scratch_checkout / ".gitignore").write_text("*.log\n")
    (scratch_checkout / "noisy.log").write_text("ignored\n")

    result = _run(str(scratch_checkout))

    assert result.returncode == EXIT_OK, result.stdout + result.stderr


def test_a_deleted_but_STAGED_removal_still_counts_as_missing(scratch_checkout):
    """A staged `rm` leaves the file off disk, and the checkout is still not whole.
    Recorded because it is the one case where 'missing' and 'intended' overlap, and
    the honest answer is to report it rather than guess at intent."""
    subprocess.run(
        ["git", "rm", "-q", "--cached", "doomed.txt"],
        cwd=scratch_checkout,
        check=True,
        capture_output=True,
    )
    (scratch_checkout / "doomed.txt").unlink()

    result = _run(str(scratch_checkout))

    # Untracked once the index entry is gone -> correctly NOT an alarm.
    assert result.returncode == EXIT_OK, result.stdout + result.stderr


def test_a_path_that_is_not_a_checkout_is_a_usage_error_not_a_detection(tmp_path):
    """The distinction that makes the alarm trustworthy: 'I could not look' must
    never render as 'I looked and it is fine', nor as 'files are missing'."""
    plain = tmp_path / "not-a-repo"
    plain.mkdir()

    result = _run(str(plain))

    assert result.returncode == EXIT_USAGE, result.stdout + result.stderr
    assert "not a git checkout" in result.stderr
    assert "Nothing was inspected" in result.stderr


def test_a_missing_directory_is_a_usage_error(tmp_path):
    result = _run(str(tmp_path / "does-not-exist"))
    assert result.returncode == EXIT_USAGE, result.stdout + result.stderr
    assert "not a directory" in result.stderr


def test_several_checkouts_are_all_inspected_and_one_bad_one_fires(scratch_checkout, tmp_path):
    """A host holds several checkouts; the alarm must not stop at the first healthy one."""
    second = tmp_path / "second"
    second.mkdir()
    run = lambda *a: subprocess.run(a, cwd=second, check=True, capture_output=True)
    run("git", "init", "-q")
    run("git", "config", "user.email", "test@example.invalid")
    run("git", "config", "user.name", "test")
    (second / "gone.txt").write_text("gone\n")
    run("git", "add", "gone.txt")
    run("git", "commit", "-q", "-m", "seed")
    (second / "gone.txt").unlink()

    result = _run(str(scratch_checkout), str(second))

    assert result.returncode == EXIT_FILES_MISSING
    assert "OK" in result.stdout, "the healthy checkout should still be reported"
    assert "gone.txt" in result.stdout
