#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Regression: git rev/ref/hash args must not be parsable as git OPTIONS.

Confirmed finding (CWE-88 argument injection -> arbitrary host-file write):
user-supplied git revisions reach ``git`` as BARE positional argv tokens in
several project_app views. Even with a list argv and ``shell=False``, a token
that BEGINS with ``-`` is parsed by git as an OPTION, not a revision. For
``git diff`` / ``git show`` an option such as ``--output=<abs-path>`` writes or
truncates an attacker-chosen file OUTSIDE the tenant project directory.

Two sinks were live-verified:

* ``api_git_diff`` (repository/api/git_history.py) reads ``?from=`` / ``?to=``.
* ``commit_detail`` (repository/commit_detail.py and directory_views/history.py)
  reads ``<str:commit_hash>`` from the URL (regex ``[^/]+`` permits a leading
  ``-``). The PR compare views feed request ``base`` / ``head`` into
  ``git diff`` / ``git rev-list`` / ``git merge-tree`` the same way.

The fix is defense-in-depth, exercised by the two test groups below:

1. a shared validator (``services.git_ref_validation``) that REJECTS any value
   git could read as an option (leading ``-``) or range foothold (leading
   ``.``), and
2. git's ``--end-of-options`` sentinel inserted before every user-supplied rev
   so git can never parse a ``-``-leading token as an option.

Group 2 is proved directly against REAL git in a throwaway repo: without the
sentinel ``git diff --output=<f>`` CREATES ``<f>`` (the exploit); with the
sentinel git treats ``--output=<f>`` as a revision and writes nothing.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from apps.infra.project_app.services.git_ref_validation import (
    END_OF_OPTIONS,
    is_valid_git_ref,
    validate_git_ref,
)
from django.core.exceptions import ValidationError

pytestmark = pytest.mark.security


# --- Group 1: the validator, both directions ------------------------------

# Every one of these is parsed by git as an OPTION in a rev position.
INJECTING_REFS = [
    "--output=/tmp/pwned",              # git diff --output= : arbitrary write
    "--output=/home/agent/.bashrc",     # the live exploit target
    "-O/tmp/orderfile",                 # short option form
    "--upload-pack=/tmp/x",             # option that runs a program
    "--no-index",                       # switches diff to two-path mode
    "-",                                # bare leading dash
    "--",                               # bare option terminator, not a rev
    "-rf",                              # leading dash
    "..--output=/tmp/x",                # leading dot (range) + option
]

# Legitimate single revisions the endpoints are documented to receive.
VALID_REFS = [
    "HEAD",
    "HEAD~2",
    "HEAD^",
    "main",
    "0123456789abcdef0123456789abcdef01234567",   # 40-hex sha
    "abc1234",                                     # short sha
    "v1.0.0",
    "feature/new-thing",                           # namespaced branch
    "refs/tags/v1.0.0",
    "origin/develop",
]


@pytest.mark.parametrize("ref", INJECTING_REFS)
def test_option_injecting_ref_is_rejected(ref):
    """A ref git would read as an option must not validate."""
    # Arrange
    hostile = ref
    # Act
    accepted = is_valid_git_ref(hostile)
    # Assert
    assert accepted is False


@pytest.mark.parametrize("ref", VALID_REFS)
def test_legitimate_ref_is_accepted(ref):
    """A syntactically normal revision must still validate."""
    # Arrange
    legit = ref
    # Act
    accepted = is_valid_git_ref(legit)
    # Assert
    assert accepted is True


def test_empty_ref_is_not_valid():
    """The empty string means 'not supplied' — never a valid ref."""
    # Arrange
    empty = ""
    # Act
    accepted = is_valid_git_ref(empty)
    # Assert
    assert accepted is False


def test_validate_git_ref_raises_on_injection():
    """validate_git_ref must raise (never silently coerce) on a hostile ref."""
    # Arrange
    hostile = "--output=/tmp/pwned"
    # Act
    raises_validation_error = pytest.raises(ValidationError)
    # Assert
    with raises_validation_error:
        validate_git_ref(hostile)


def test_validate_git_ref_returns_value_when_valid():
    """validate_git_ref returns the ref unchanged when it is safe."""
    # Arrange
    legit = "HEAD~2"
    # Act
    returned = validate_git_ref(legit)
    # Assert
    assert returned == "HEAD~2"


def test_end_of_options_sentinel_value():
    """The sentinel must be exactly git's ``--end-of-options`` token."""
    # Arrange
    sentinel = END_OF_OPTIONS
    # Act
    value = sentinel
    # Assert
    assert value == "--end-of-options"


# --- Group 2: the ``--end-of-options`` terminator, proved against real git -

def _init_repo(tmp_path: Path) -> Path:
    """Create a throwaway git repo with one commit and a dirty working tree."""
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "t@t"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=repo, check=True)
    (repo / "a.txt").write_text("one\n")
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-qm", "c1"], cwd=repo, check=True)
    (repo / "a.txt").write_text("two\n")  # unstaged change so `git diff` emits
    return repo


def test_without_terminator_output_option_writes_file(tmp_path):
    """RED: the raw exploit — ``git diff --output=<f>`` creates ``<f>``.

    Documents the mechanism the fix defeats so the GREEN tests are a
    meaningful contrast (a gate that cannot fail is not a gate).
    """
    # Arrange
    repo = _init_repo(tmp_path)
    target = tmp_path / "pwned_red.txt"
    # Act — no option terminator: git parses ``--output=<f>`` as an option.
    subprocess.run(
        ["git", "diff", f"--output={target}"],
        cwd=repo, capture_output=True, text=True,
    )
    # Assert
    assert target.exists()


def test_end_of_options_blocks_output_file_write(tmp_path):
    """GREEN: with ``--end-of-options`` the ``--output=`` write does not happen."""
    # Arrange
    repo = _init_repo(tmp_path)
    target = tmp_path / "pwned_green.txt"
    # Act — sentinel before the hostile "rev".
    subprocess.run(
        ["git", "diff", END_OF_OPTIONS, f"--output={target}"],
        cwd=repo, capture_output=True, text=True,
    )
    # Assert
    assert not target.exists()


def test_end_of_options_makes_git_reject_bogus_rev(tmp_path):
    """GREEN corollary: git REFUSES the ``--output=`` token instead of honouring it.

    This asserted ``result.returncode != 0`` until 2026-07-30. That is a proxy
    for refusal, and it is GIT-VERSION-DEPENDENT: on the version running on
    `spartan-cpu-scitex-hub-01` git prints

        fatal: option '--output=...' must come before non-option arguments

    to stderr and still exits 0, so the assertion failed while git was in fact
    refusing exactly as intended. That made this a GREEN-BY-MACHINE gate — it
    passed or failed according to which runner picked up the job, blocking
    unrelated PRs and telling us nothing about the security property.

    The security property itself is asserted by
    ``test_end_of_options_blocks_output_file_write`` above (the file is never
    written) and was passing throughout. What this corollary uniquely adds is
    that git *complained* rather than silently treating the token as a
    pathspec, so it now asserts refusal in a version-stable way: a non-zero
    exit OR a fatal on stderr, AND the file still absent.

    Both halves are required. Without the "no file" half, a future git that
    errored for some unrelated reason while still writing the file would pass.
    Without the "refused" half, a git that silently ignored the token would
    pass. Neither alone is the invariant.
    """
    # Arrange
    repo = _init_repo(tmp_path)
    target = tmp_path / "pwned_rc.txt"
    # Act
    result = subprocess.run(
        ["git", "diff", END_OF_OPTIONS, f"--output={target}"],
        cwd=repo, capture_output=True, text=True,
    )
    # Assert
    refused = result.returncode != 0 or "fatal" in result.stderr.lower()
    assert refused and not target.exists(), (
        "git neither refused the --output= token nor left the file unwritten: "
        f"returncode={result.returncode!r}, stderr={result.stderr.strip()!r}, "
        f"target_exists={target.exists()}. After --end-of-options git must "
        "treat --output= as a rev/pathspec and must never write that file."
    )


# EOF
