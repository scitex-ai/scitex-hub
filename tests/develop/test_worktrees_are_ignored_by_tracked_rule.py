#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""``.worktrees/`` must be ignored by the TRACKED .gitignore, not a local exclude.

This repo carries ~175 agent git worktrees under ``.worktrees/``. Until
2026-07-30 the ignore rule existed only in ``.git/info/exclude`` — a per-clone,
**untracked** file that git never shares. The result was a defect that is
invisible from the machine that has the local rule:

    machine with .git/info/exclude entry   ``git status`` clean
    fresh clone / CI checkout              ~175 untracked directories

So "is it ignored?" is the wrong question — it was ignored, here, for me. The
question that matters is **which file the rule comes from**, because only a
tracked rule is true for everyone.

``git check-ignore -v`` answers exactly that: it prints
``<source>:<line>:<pattern>\\t<path>``, naming the file the decision came from.
Asserting on that source is what makes this guard test the real property. A test
that merely asserted the path was ignored would have PASSED throughout the whole
life of the bug, on the very machine where the bug was invisible.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKTREES = ".worktrees/"
# A directory that is tracked and must NOT be ignored — the control that proves
# check-ignore discriminates rather than answering "ignored" to everything.
CONTROL_TRACKED_DIR = "apps/"


def _check_ignore(pathname):
    """Return (returncode, stdout) from ``git check-ignore -v`` for a path."""
    proc = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "check-ignore", "-v", "--no-index", pathname],
        capture_output=True,
        text=True,
        check=False,
    )
    return proc.returncode, proc.stdout.strip()


@pytest.fixture(scope="module")
def worktrees_rule():
    """The ``git check-ignore -v`` result for ``.worktrees/``."""
    return _check_ignore(WORKTREES)


def test_worktrees_directory_is_ignored(worktrees_rule):
    """Anti-vacuity: if nothing ignores it, the source assertion is meaningless."""
    # Arrange
    returncode, output = worktrees_rule

    # Act
    is_ignored = returncode == 0 and bool(output)

    # Assert
    assert is_ignored, (
        f"{WORKTREES} is not ignored at all (git check-ignore rc={returncode}, "
        f"output={output!r}). A fresh clone would show every agent worktree as "
        "untracked. Add '.worktrees/' to the repository .gitignore."
    )


def test_worktrees_ignore_rule_comes_from_the_tracked_gitignore(worktrees_rule):
    """The rule must be shared, not a local per-clone exclude."""
    # Arrange
    _, output = worktrees_rule

    # Act
    source = output.split(":", 1)[0] if output else ""

    # Assert
    assert source.endswith(".gitignore"), (
        f"{WORKTREES} is ignored by {source!r}, not by the tracked .gitignore. "
        "A rule in .git/info/exclude is untracked and per-clone, so it hides the "
        "problem on this machine while a fresh clone or CI checkout still sees "
        "~175 untracked directories. Move the rule into .gitignore."
    )


def test_check_ignore_discriminates_between_ignored_and_tracked_paths():
    """Anti-vacuity: the probe must be capable of returning 'not ignored'."""
    # Arrange
    expected_not_ignored = 1

    # Act
    returncode, _ = _check_ignore(CONTROL_TRACKED_DIR)

    # Assert
    assert returncode == expected_not_ignored, (
        f"git check-ignore reported {CONTROL_TRACKED_DIR!r} as IGNORED "
        f"(rc={returncode}). That is a tracked source directory, so either the "
        "repo's ignore rules are far too broad or this probe is not measuring "
        "what the tests above assume — either way, fix before trusting them."
    )


# EOF
