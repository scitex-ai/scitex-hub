#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: ./tests/security/test_origin_scrub_is_git_free.py

"""The origin-credential scrub must work where GIT DOES NOT.

WHY THIS FILE EXISTS
--------------------
``sanitize_origin_url`` had a passing unit test and had NEVER RUN IN
PRODUCTION. Measured on the running prod container 2026-07-29::

    git remote get-url origin -> rc=128
    fatal: detected dubious ownership in repository at
           '/app/data/users/<user>/proj/<repo>'

The container uid differs from the bind-mounted file owner, so git's
``safe.directory`` guard rejected every user repo. The scrub shelled out to
git, so it returned failure for every repo -- and its caller discarded that.
6 of 46 user ``.git/config`` files still held credentials, 4 of them the live
platform admin token, while the function, its test, and its card all reported
the leak fixed.

The old test passed because its fixture repo was owned by the test user. It
exercised the function in an environment the function never actually ran in.

So these tests remove git FOR REAL (``no_git_on_path`` empties PATH, it does
not patch anything) and require the scrub to work anyway. If someone
reintroduces a subprocess call, ``git`` will not be found and these go red.
That is the barrier: the defect was never "git was configured wrong", it was
"a security control depended on an external tool whose environment
assumptions its test could not see".

Card: hub-git-safedir-durable / sec-gitea-admin-token-plaintext-in-user-gitconfig
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from apps.infra.gitea_app.services.origin_scrub import (
    OriginScrubResult,
    OriginScrubStatus,
    sanitize_origin_url,
    strip_url_credentials,
)

TOKEN = "aaaabbbbccccddddeeeeffff00001111"
POISONED_URL = f"http://scitex_admin:{TOKEN}@gitea:3000/u/p.git"
CLEAN_URL = "http://gitea:3000/u/p.git"


def _write_repo(root: Path, url: str) -> Path:
    """Create a repo whose .git/config carries ``url`` as origin."""
    git_dir = root / ".git"
    git_dir.mkdir(parents=True, exist_ok=True)
    config = git_dir / "config"
    config.write_text(
        "[core]\n"
        "\trepositoryformatversion = 0\n"
        "\tbare = false\n"
        '[remote "origin"]\n'
        f"\turl = {url}\n"
        "\tfetch = +refs/heads/*:refs/remotes/origin/*\n"
        '[branch "develop"]\n'
        "\tremote = origin\n",
        encoding="utf-8",
    )
    return config


@pytest.fixture
def no_git_on_path(tmp_path):
    """Make ``git`` genuinely unreachable by emptying PATH.

    Real environment substitution, not a patch: any subprocess call to git
    raises FileNotFoundError. A test that stays green here proves the scrub
    never needed git -- which is the whole point of the fix.
    """
    empty_bin = tmp_path / "empty-bin"
    empty_bin.mkdir()
    original = os.environ.get("PATH")
    os.environ["PATH"] = str(empty_bin)
    yield
    if original is None:
        os.environ.pop("PATH", None)
    else:
        os.environ["PATH"] = original


@pytest.fixture
def poisoned_repo(tmp_path):
    """A pre-fix repo whose origin still embeds the platform token."""
    root = tmp_path / "poisoned"
    _write_repo(root, POISONED_URL)
    return root


@pytest.fixture
def clean_repo(tmp_path):
    root = tmp_path / "clean"
    _write_repo(root, CLEAN_URL)
    return root


# --------------------------------------------------------------------------
# THE REGRESSION BARRIER: works with no git available at all
# --------------------------------------------------------------------------


def test_scrub_succeeds_without_git_available(no_git_on_path, poisoned_repo):
    # Arrange: PATH is empty, so any `git` invocation would fail.
    expected = OriginScrubStatus.SCRUBBED
    # Act
    result = sanitize_origin_url(poisoned_repo)
    # Assert
    assert result.status is expected


def test_token_is_gone_from_config_without_git_available(
    no_git_on_path, poisoned_repo
):
    # Arrange
    config = poisoned_repo / ".git" / "config"
    # Act
    sanitize_origin_url(poisoned_repo)
    # Assert
    assert TOKEN not in config.read_text(encoding="utf-8")


def test_origin_keeps_working_url_after_scrub(no_git_on_path, poisoned_repo):
    # Arrange
    config = poisoned_repo / ".git" / "config"
    # Act
    sanitize_origin_url(poisoned_repo)
    # Assert
    assert CLEAN_URL in config.read_text(encoding="utf-8")


# --------------------------------------------------------------------------
# IN-PLACE REWRITE: a tenant's file must keep its identity
# --------------------------------------------------------------------------


def test_scrub_preserves_inode(poisoned_repo):
    # Arrange
    config = poisoned_repo / ".git" / "config"
    before = config.stat().st_ino
    # Act
    sanitize_origin_url(poisoned_repo)
    # Assert
    assert config.stat().st_ino == before


def test_scrub_preserves_mode(poisoned_repo):
    # Arrange
    config = poisoned_repo / ".git" / "config"
    before = config.stat().st_mode
    # Act
    sanitize_origin_url(poisoned_repo)
    # Assert
    assert config.stat().st_mode == before


# --------------------------------------------------------------------------
# OUTCOMES ARE DISTINCT -- "could not look" must never read as "clean"
# --------------------------------------------------------------------------


def test_clean_origin_reports_already_clean(clean_repo):
    # Arrange
    expected = OriginScrubStatus.ALREADY_CLEAN
    # Act
    result = sanitize_origin_url(clean_repo)
    # Assert
    assert result.status is expected


def test_clean_origin_file_is_byte_identical_afterwards(clean_repo):
    # Arrange
    config = clean_repo / ".git" / "config"
    original = config.read_text(encoding="utf-8")
    # Act
    sanitize_origin_url(clean_repo)
    # Assert
    assert config.read_text(encoding="utf-8") == original


def test_missing_config_reports_unreadable(tmp_path):
    # Arrange
    absent = tmp_path / "not-a-repo"
    # Act
    result = sanitize_origin_url(absent)
    # Assert
    assert result.status is OriginScrubStatus.UNREADABLE


def test_missing_config_is_not_considered_safe(tmp_path):
    # Arrange: the critical three-valued case -- unknown is not clean.
    absent = tmp_path / "not-a-repo"
    # Act
    result = sanitize_origin_url(absent)
    # Assert
    assert not result.is_safe


def test_gitdir_pointer_is_not_silently_treated_as_done(tmp_path):
    # Arrange: a worktree/submodule .git FILE, not a directory.
    root = tmp_path / "worktree"
    root.mkdir()
    (root / ".git").write_text("gitdir: /elsewhere/.git/worktrees/x\n")
    # Act
    result = sanitize_origin_url(root)
    # Assert
    assert not result.is_safe


def test_repo_without_origin_reports_no_origin(tmp_path):
    # Arrange
    root = tmp_path / "no-origin"
    (root / ".git").mkdir(parents=True)
    (root / ".git" / "config").write_text("[core]\n\tbare = false\n")
    # Act
    result = sanitize_origin_url(root)
    # Assert
    assert result.status is OriginScrubStatus.NO_ORIGIN


def test_second_scrub_reports_already_clean(poisoned_repo):
    # Arrange
    sanitize_origin_url(poisoned_repo)
    # Act
    second = sanitize_origin_url(poisoned_repo)
    # Assert
    assert second.status is OriginScrubStatus.ALREADY_CLEAN


def test_other_remotes_are_left_intact(tmp_path):
    # Arrange
    root = tmp_path / "two-remotes"
    (root / ".git").mkdir(parents=True)
    config = root / ".git" / "config"
    config.write_text(
        '[remote "origin"]\n'
        f"\turl = {POISONED_URL}\n"
        '[remote "upstream"]\n'
        "\turl = http://gitea:3000/u/up.git\n",
        encoding="utf-8",
    )
    # Act
    sanitize_origin_url(root)
    # Assert
    assert "http://gitea:3000/u/up.git" in config.read_text(encoding="utf-8")


# --------------------------------------------------------------------------
# URL PARSING -- authority only
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "poisoned,clean",
    [
        (f"http://user:{TOKEN}@gitea:3000/a/b.git", "http://gitea:3000/a/b.git"),
        (f"http://{TOKEN}@gitea:3000/a/b.git", "http://gitea:3000/a/b.git"),
        ("http://gitea:3000/a/b.git", "http://gitea:3000/a/b.git"),
        # An '@' in the PATH is not userinfo -- must survive intact.
        ("http://gitea:3000/u/re@po.git", "http://gitea:3000/u/re@po.git"),
        # SSH carries no userinfo to strip.
        ("git@github.com:scitex-ai/x.git", "git@github.com:scitex-ai/x.git"),
    ],
)
def test_strip_url_credentials_only_removes_userinfo(poisoned, clean):
    # Arrange
    subject = poisoned
    # Act
    stripped = strip_url_credentials(subject)
    # Assert
    assert stripped == clean


def test_repo_named_with_at_sign_survives_end_to_end(tmp_path):
    # Arrange
    root = tmp_path / "at-sign"
    config = _write_repo(root, "http://gitea:3000/u/re@po.git")
    # Act
    sanitize_origin_url(root)
    # Assert
    assert "http://gitea:3000/u/re@po.git" in config.read_text(encoding="utf-8")


# --------------------------------------------------------------------------
# THE RESULT SHAPE VALIDATES ITSELF
# --------------------------------------------------------------------------


def test_unreadable_result_without_detail_is_rejected(tmp_path):
    # Arrange
    status = OriginScrubStatus.UNREADABLE
    # Act
    build = lambda: OriginScrubResult(tmp_path, status)  # noqa: E731
    # Assert -- fail where the answer is BUILT, not three layers downstream.
    with pytest.raises(ValueError):
        build()


def test_failed_result_without_detail_is_rejected(tmp_path):
    # Arrange
    status = OriginScrubStatus.FAILED
    # Act
    # Assert
    with pytest.raises(ValueError):
        OriginScrubResult(tmp_path, status)


def test_status_must_be_the_enum_not_a_bare_string(tmp_path):
    # Arrange
    bogus = "already-clean"
    # Act
    # Assert
    with pytest.raises(TypeError):
        OriginScrubResult(tmp_path, bogus)  # type: ignore[arg-type]
