#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""`make status` must END with a verdict and EXIT with one.

Until 2026-09-05 check-status.sh ran every section, discarded every exit code
(`|| true`), and finished by printing `date`. So a full disk — the check that
was added after compute-04 went down on 2026-08-09 — produced a red [FAIL]
somewhere in the middle of ~15 chunks printed in completion order, followed by
a timestamp, and an exit status of 0. check_disk_space.sh's own header says
"this check GATES, it does not merely print"; the orchestrator made that claim
false for anyone running `make status`.

These tests run the REAL orchestrator against a FAKE registry: a temp copy of
check-status.sh with a sections.sh beside it that registers tiny scripts. The
orchestrator finds its registry relative to its own path, so a copy in a temp
directory is a full integration run of the shipped file with no docker, no
host and no real checks — the wiring is what broke, and the wiring is what is
exercised.

WHAT EACH TEST IS FOR
  summary_counts / names_fail / names_warn / summary_is_last
        one FAIL, one WARN, one OK: the summary line counts them, names which
        is which, and is the last thing before the date — where the eye lands.
  fail_makes_make_status_exit_one
        the gate is real: a [FAIL] section turns the whole run non-zero.
  all_green_exits_zero / all_green_prints_no_red_lines
        the positive control for the gate — a run with nothing red must NOT be
        red, or the exit code is noise rather than signal.
  a_section_that_cannot_run_is_a_fail / ..._is_named
        a registered command that does not exist is the silent failure this
        file is about; it must count as FAIL and be named.
  a_warn_does_not_gate / a_warn_is_still_reported
        exit 2 / [WARN] is reported but does not fail the run — the disk
        check's own convention, kept on purpose.
  a_fail_token_wins_over_a_zero_exit
        several shipped checks print [FAIL] and exit 0; the token is the
        verdict the admin reads, so it is the verdict the summary counts.
"""

from __future__ import annotations

import os
import shutil
import stat
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
ORCHESTRATOR = REPO / "deployment" / "host-setup" / "checks" / "check-status.sh"

OK_BODY = "#!/bin/bash\necho 'thing: [OK] fine'\nexit 0\n"
WARN_BODY = "#!/bin/bash\necho 'thing: [WARN] 9% free'\nexit 2\n"
FAIL_BODY = "#!/bin/bash\necho 'thing: [FAIL] 1% free'\nexit 1\n"
POLITE_FAIL_BODY = "#!/bin/bash\necho 'x: [FAIL] but polite exit'\nexit 0\n"


def _write_executable(path: Path, body: str) -> None:
    path.write_text(body, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def _fake_checks_dir(tmp_path: Path, sections: dict[str, str | None]) -> Path:
    """Copy the shipped orchestrator next to a fake registry of `sections`.

    ``sections`` maps a section name to the BODY of a bash script, or ``None``
    to register the name against a file that is deliberately never written.
    The orchestrator derives PROJECT_ROOT as ``../../..`` of its own directory,
    so the copy lives three levels deep to keep that path resolvable.
    """
    checks = tmp_path / "deployment" / "host-setup" / "checks"
    checks.mkdir(parents=True)
    shutil.copy2(ORCHESTRATOR, checks / "check-status.sh")
    rows = []
    for name, body in sections.items():
        if body is not None:
            _write_executable(checks / f"{name}.sh", body)
        rows.append(f'        "{name}" "${{d}}/{name}.sh" \\')
    registry = (
        "#!/bin/bash\n"
        "set -uo pipefail\n"
        "status_sections() {\n"
        '    local d="${SECTIONS_SCRIPT_DIR:?}"\n'
        "    printf '%s\\t%s\\n' \\\n" + "\n".join(rows).rstrip(" \\") + "\n"
        "}\n"
    )
    _write_executable(checks / "sections.sh", registry)
    return checks


def _run(tmp_path: Path, sections: dict[str, str | None]) -> subprocess.CompletedProcess[str]:
    checks = _fake_checks_dir(tmp_path, sections)
    return subprocess.run(
        ["bash", str(checks / "check-status.sh")],
        capture_output=True,
        text=True,
        timeout=60,
        env={**os.environ, "LC_ALL": "C"},
    )


def _nonblank_lines(proc: subprocess.CompletedProcess[str]) -> list[str]:
    return [line for line in proc.stdout.splitlines() if line.strip()]


@pytest.fixture(name="mixed_run")
def _mixed_run(tmp_path: Path) -> subprocess.CompletedProcess[str]:
    return _run(
        tmp_path, {"01-green": OK_BODY, "02-amber": WARN_BODY, "03-red": FAIL_BODY}
    )


@pytest.fixture(name="mixed_lines")
def _mixed_lines(mixed_run) -> list[str]:
    return _nonblank_lines(mixed_run)


@pytest.fixture(name="mixed_summary_index")
def _mixed_summary_index(mixed_lines: list[str]) -> int:
    return next(i for i, line in enumerate(mixed_lines) if line.startswith("SUMMARY:"))


@pytest.fixture(name="all_green_run")
def _all_green_run(tmp_path: Path) -> subprocess.CompletedProcess[str]:
    return _run(tmp_path, {"01-a": OK_BODY, "02-b": OK_BODY})


@pytest.fixture(name="missing_script_run")
def _missing_script_run(tmp_path: Path) -> subprocess.CompletedProcess[str]:
    return _run(tmp_path, {"01-a": OK_BODY, "02-gone": None})


@pytest.fixture(name="warn_only_run")
def _warn_only_run(tmp_path: Path) -> subprocess.CompletedProcess[str]:
    return _run(tmp_path, {"01-a": OK_BODY, "02-amber": WARN_BODY})


# ── one FAIL, one WARN, one OK ──────────────────────────────


def test_summary_counts_every_verdict(mixed_lines: list[str], mixed_summary_index: int) -> None:
    # Arrange — one section of each verdict, registered in that order.
    summary = mixed_lines[mixed_summary_index]
    # Act
    counted = summary == "SUMMARY: 1 FAIL, 1 WARN, 1 OK of 3 sections"
    # Assert
    assert counted, summary


def test_summary_names_the_failing_section(mixed_lines: list[str], mixed_summary_index: int) -> None:
    # Arrange
    fail_line = mixed_lines[mixed_summary_index + 1]
    # Act
    named = fail_line == "  FAIL: 03-red"
    # Assert
    assert named, fail_line


def test_summary_names_the_warning_section(mixed_lines: list[str], mixed_summary_index: int) -> None:
    # Arrange
    warn_line = mixed_lines[mixed_summary_index + 2]
    # Act
    named = warn_line == "  WARN: 02-amber"
    # Assert
    assert named, warn_line


def test_summary_is_the_last_thing_before_the_date(mixed_lines: list[str], mixed_summary_index: int) -> None:
    # Arrange — SUMMARY, FAIL, WARN, then exactly one more line: the date.
    trailing = mixed_lines[mixed_summary_index + 3 :]
    # Act
    only_the_date = len(trailing) == 1
    # Assert
    assert only_the_date, trailing


def test_fail_makes_make_status_exit_one(mixed_run) -> None:
    # Arrange — the mixed run holds one [FAIL] section.
    rc = mixed_run.returncode
    # Act
    gated = rc == 1
    # Assert
    assert gated, mixed_run.stdout


# ── positive control: nothing red ──────────────────────────


def test_all_green_exits_zero(all_green_run) -> None:
    # Arrange
    rc = all_green_run.returncode
    # Act
    green = rc == 0
    # Assert
    assert green, all_green_run.stdout


def test_all_green_prints_no_red_lines(all_green_run) -> None:
    # Arrange
    out = all_green_run.stdout
    # Act
    clean = (
        "SUMMARY: 0 FAIL, 0 WARN, 2 OK of 2 sections" in out
        and "  FAIL:" not in out
        and "  WARN:" not in out
    )
    # Assert
    assert clean, out


# ── a registered command that is not there ─────────────────


def test_a_section_that_cannot_run_is_a_fail(missing_script_run) -> None:
    # Arrange — before this change the missing section printed an empty
    # chunk and the run exited 0.
    rc = missing_script_run.returncode
    # Act
    gated = rc == 1
    # Assert
    assert gated, missing_script_run.stdout


def test_a_section_that_cannot_run_is_named(missing_script_run) -> None:
    # Arrange
    out = missing_script_run.stdout
    # Act
    named = "SUMMARY: 1 FAIL, 0 WARN, 1 OK of 2 sections" in out and "  FAIL: 02-gone" in out
    # Assert
    assert named, out


# ── WARN is reported, not gated ────────────────────────────


def test_a_warn_does_not_gate(warn_only_run) -> None:
    # Arrange — exit 2 is the disk check's own "warn" code.
    rc = warn_only_run.returncode
    # Act
    not_gated = rc == 0
    # Assert
    assert not_gated, warn_only_run.stdout


def test_a_warn_is_still_reported(warn_only_run) -> None:
    # Arrange
    out = warn_only_run.stdout
    # Act
    reported = "SUMMARY: 0 FAIL, 1 WARN, 1 OK of 2 sections" in out and "  WARN: 02-amber" in out
    # Assert
    assert reported, out


# ── the token is the verdict ───────────────────────────────


def test_a_fail_token_wins_over_a_zero_exit(tmp_path: Path) -> None:
    # Arrange — a section that prints [FAIL] but exits 0.
    proc = _run(tmp_path, {"01-a": POLITE_FAIL_BODY})
    # Act
    gated_and_named = proc.returncode == 1 and "  FAIL: 01-a" in proc.stdout
    # Assert
    assert gated_and_named, proc.stdout
