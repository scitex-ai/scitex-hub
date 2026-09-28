"""Controls for the shared Git-index source-policy corpus."""
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from tests.tracked_source import (
    EmptyTrackedSetError,
    local_untracked_paths,
    tracked_source_files,
)


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "config", "user.email", "test@example.com")
    _git(tmp_path, "config", "user.name", "Test")
    return tmp_path


def test_staged_content_is_the_canonical_local_and_ci_subject(repo: Path):
    path = repo / "policy.py"
    path.write_text("safe\n")
    _git(repo, "add", "policy.py")
    path.write_text("working-tree violation\n")
    local = tracked_source_files(repo, ("*.py",))
    _git(repo, "commit", "-qm", "snapshot")
    ci = tracked_source_files(repo, ("*.py",))
    assert [(f.path, f.data) for f in local] == [(f.path, f.data) for f in ci]
    assert local[0].data == b"safe\n"


def test_staged_violation_is_seen_before_and_after_commit(repo: Path):
    path = repo / "policy.py"
    path.write_text("violation\n")
    _git(repo, "add", "policy.py")
    before = tracked_source_files(repo, ("*.py",))
    _git(repo, "commit", "-qm", "snapshot")
    after = tracked_source_files(repo, ("*.py",))
    assert b"violation" in before[0].data
    assert before == after


def test_untracked_is_local_preflight_only_and_ignored_is_excluded(repo: Path):
    (repo / ".gitignore").write_text("ignored.py\ndata/\n.old/\n.worktrees/\n")
    _git(repo, "add", ".gitignore")
    (repo / "untracked.py").write_text("violation\n")
    (repo / "ignored.py").write_text("violation\n")
    for directory in ("data", ".old", ".worktrees"):
        (repo / directory).mkdir()
        (repo / directory / "noise.py").write_text("violation\n")
    assert tracked_source_files(repo, ("*.py",), require_nonempty=False) == ()
    assert local_untracked_paths(repo) == ("untracked.py",)


def test_whitespace_and_newline_filenames_are_nul_safe(repo: Path):
    names = ("space name.py", "line\nbreak.py")
    for name in names:
        (repo / name).write_text(name)
    _git(repo, "add", "--", *names)
    assert {f.path for f in tracked_source_files(repo, ("*.py",))} == set(names)


def test_empty_tracked_set_fails_closed(repo: Path):
    (repo / "README").write_text("tracked but not Python\n")
    _git(repo, "add", "README")
    with pytest.raises(EmptyTrackedSetError):
        tracked_source_files(repo, ("*.py",))
