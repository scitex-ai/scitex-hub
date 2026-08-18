#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""A script invoked as ``./path`` must be executable IN GIT, not just on disk.

`chmod +x` in a working tree does not put the bit in the index. So a script can
be executable for the person who wrote it and 100644 for everyone who clones —
and the failure lands on whoever runs the make target next, as "Permission
denied" from a Makefile line that looks perfectly correct.

Measured on develop, 2026-08-16:

    Makefile:837        @./scripts/testing/setup_pytest.sh
    git ls-files -s     100644 scripts/testing/setup_pytest.sh

so ``make setup-pytest`` — and ``make setup-testing``, which depends on it —
could not run from a clean clone. ``scripts/maintenance/check_status_live.sh``
had the identical defect and broke ``make status-live`` the same way; that one
was found only because a section registry landed on top of it.

WHAT THIS ASSERTS, and why it is narrow on purpose. Only scripts INVOKED as
``./path`` need the bit: ``bash path`` and ``sh path`` work at any mode, and a
great many tracked scripts are libraries that are only ever sourced. Demanding
+x on all 148 tracked ``.sh`` files would be a rule nobody could keep, and a
rule nobody keeps is one that gets bypassed. So the gate follows the CALL SITE:
if something tracked runs it as ``./path``, it must be executable in git.

Self-references count. A script whose own header says
``# Usage: ./scripts/foo.sh`` is documentation telling a human to invoke it that
way, and that instruction fails on a fresh clone exactly as a Makefile line
would.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]

#: Paths whose contents are historical and not run from this tree.
_IGNORED_PREFIXES = ("deployment/.archive/",)

#: Files worth scanning for call sites. Deliberately not the whole tree: these
#: are where a `./path` invocation is an instruction rather than prose.
_CALLER_GLOBS = ("Makefile", "*.sh", "*.yml", "*.yaml")


def _tracked_shell_scripts() -> dict[str, str]:
    """Map tracked ``*.sh`` path -> git mode."""
    proc = subprocess.run(
        ["git", "-C", str(REPO), "ls-files", "-s", "--", "*.sh"],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert proc.returncode == 0, f"git ls-files failed: {proc.stderr.strip()}"

    scripts: dict[str, str] = {}
    for line in proc.stdout.splitlines():
        if not line.strip():
            continue
        meta, _, path = line.partition("\t")
        mode = meta.split()[0]
        if not path.startswith(_IGNORED_PREFIXES):
            scripts[path] = mode
    return scripts


def _invoked_by_path() -> set[str]:
    """Tracked script paths that something runs as ``./path``."""
    proc = subprocess.run(
        ["git", "-C", str(REPO), "grep", "-hoE", r"\./[A-Za-z0-9_./-]+\.sh"]
        + ["--"]
        + list(_CALLER_GLOBS),
        capture_output=True,
        text=True,
        timeout=120,
    )
    # git grep exits 1 when there are no matches; that is not an error here.
    assert proc.returncode in (0, 1), f"git grep failed: {proc.stderr.strip()}"
    return {m.lstrip("./") for m in re.findall(r"\./[A-Za-z0-9_./-]+\.sh", proc.stdout)}


@pytest.fixture(name="scripts", scope="module")
def _scripts() -> dict[str, str]:
    found = _tracked_shell_scripts()
    # Guards every assertion below: an empty map would make them all vacuous.
    assert len(found) > 50, (
        f"only {len(found)} tracked .sh files found — the listing looks broken, "
        "and every check in this file would pass for the wrong reason."
    )
    return found


def test_scripts_invoked_by_path_are_executable_in_git(
    scripts: dict[str, str],
) -> None:
    # Arrange
    invoked = _invoked_by_path() & set(scripts)

    # Act
    broken = sorted(p for p in invoked if scripts[p] != "100755")

    # Assert
    assert broken == [], (
        "these scripts are invoked as ./path but are NOT executable in git, so "
        f"they fail with 'Permission denied' from a clean clone: {broken}. Fix "
        "with `git update-index --chmod=+x <path>` — chmod alone only changes "
        "your working tree."
    )


def test_the_call_site_scan_finds_something(scripts: dict[str, str]) -> None:
    # Arrange — POSITIVE CONTROL. If the scan silently matched nothing (a moved
    # Makefile, a changed glob, a regex typo), the test above would pass while
    # checking an empty set — the same "green because it measured nothing"
    # failure this suite exists to prevent elsewhere.
    # Act
    invoked = _invoked_by_path() & set(scripts)

    # Assert
    assert len(invoked) >= 3, (
        f"the ./path scan matched only {len(invoked)} tracked script(s): "
        f"{sorted(invoked)}. Expected several. Either the callers moved or the "
        "scan is broken — check before relaxing this number."
    )
