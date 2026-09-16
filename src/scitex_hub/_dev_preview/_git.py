#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: src/scitex_hub/_dev_preview/_git.py

"""Thin argv-list wrappers over ``git -C <clone> ...`` for the preview sync.

Argv lists, never shell strings — the clone path is operator-controlled
and a shell string would make it an injection surface. Every call has a
timeout: the fetch talks to GitHub and a hung network must not hold the
``flock`` until the supervisor's ``/usr/bin/timeout`` fires 45 minutes
later. A non-zero exit raises :class:`GitError` carrying stderr, so the
caller's log says WHAT git objected to, not just that it did.

GitPython is deliberately not used here even though hub depends on it: the
sync runs inside the supervisor's venv and a plain ``git`` binary is the
only thing it should need.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

__all__ = [
    "FETCH_TIMEOUT_SEC",
    "GitError",
    "MERGE_TIMEOUT_SEC",
    "changed_paths",
    "current_branch",
    "fetch",
    "head",
    "is_ancestor",
    "is_commit",
    "is_work_tree",
    "merge_ff_only",
    "rev_parse",
    "tracked_dirt",
]

#: Local plumbing is instantaneous; 60 s only guards a wedged filesystem.
_LOCAL_TIMEOUT = 60
#: Network: GitHub fetches of hub take seconds, but a stalled TCP session
#: can sit for minutes — bound it well under the job's hard timeout. Public
#: because ``_sync.WORST_CASE_TICK_SEC`` sums every budget on the tick's
#: worst-case path and the job's outer ``/usr/bin/timeout`` must exceed it.
FETCH_TIMEOUT_SEC = 300
#: A fast-forward merge touches the work tree; hub's tree is large.
MERGE_TIMEOUT_SEC = 300


class GitError(RuntimeError):
    """A git command exited non-zero (or timed out); ``stderr`` says why."""

    def __init__(self, argv: list[str], returncode: int, stderr: str) -> None:
        self.argv = argv
        self.returncode = returncode
        self.stderr = stderr.strip()
        super().__init__(
            f"{' '.join(argv)} exited {returncode}: {self.stderr or '<no stderr>'}"
        )


def _run(
    clone: Path, *args: str, timeout: int = _LOCAL_TIMEOUT
) -> subprocess.CompletedProcess[str]:
    argv = ["git", "-C", str(clone), *args]
    try:
        completed = subprocess.run(
            argv,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        stderr = exc.stderr.decode() if isinstance(exc.stderr, bytes) else exc.stderr
        raise GitError(
            argv, 124, f"timed out after {timeout}s: {stderr or ''}"
        ) from exc
    if completed.returncode != 0:
        raise GitError(argv, completed.returncode, completed.stderr)
    return completed


def is_work_tree(clone: Path) -> bool:
    """True when ``clone`` is inside a git work tree (a bare repo is not)."""
    try:
        completed = _run(clone, "rev-parse", "--is-inside-work-tree")
    except GitError:
        return False
    return completed.stdout.strip() == "true"


def current_branch(clone: Path) -> str:
    """The checked-out branch name; ``"HEAD"`` when detached."""
    return _run(clone, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip()


def head(clone: Path) -> str:
    """The full SHA of ``HEAD``."""
    return rev_parse(clone, "HEAD")


def rev_parse(clone: Path, ref: str) -> str:
    """Resolve ``ref`` to a full SHA (``GitError`` when it does not exist)."""
    return _run(
        clone, "rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}"
    ).stdout.strip()


def is_commit(clone: Path, ref: str) -> bool:
    """True when ``ref`` names a commit THIS clone has.

    The sync's ``applied_head`` comes from ``state.json``, which may outlive
    the clone it was written for (a re-clone, a hand reset after a rewritten
    origin, state copied from another host). ``git diff`` against a SHA the
    clone does not have fails on every tick forever, so the caller asks
    first and re-baselines instead.
    """
    try:
        rev_parse(clone, ref)
    except GitError:
        return False
    return True


def tracked_dirt(clone: Path) -> list[str]:
    """Porcelain status lines for TRACKED files only (untracked are ignored).

    Untracked files are tolerated on purpose: the preview clone carries
    ``logs/``, ``GITIGNORED/`` and operator scratch that a fast-forward
    never touches. A modified tracked file, on the other hand, is a
    half-finished edit that ``merge --ff-only`` would either refuse or
    silently fold into the preview — so it is a refusal, not a warning.
    """
    out = _run(clone, "status", "--porcelain", "--untracked-files=no").stdout
    return [line for line in out.splitlines() if line.strip()]


def fetch(clone: Path, remote: str, branch: str) -> None:
    """``git fetch --quiet <remote> <branch>`` (updates ``<remote>/<branch>``)."""
    _run(clone, "fetch", "--quiet", remote, branch, timeout=FETCH_TIMEOUT_SEC)


def merge_ff_only(clone: Path, ref: str) -> None:
    """``git merge --ff-only <ref>``; a diverged clone raises ``GitError``."""
    _run(clone, "merge", "--ff-only", "--quiet", ref, timeout=MERGE_TIMEOUT_SEC)


def changed_paths(clone: Path, old: str, new: str) -> list[str]:
    """Repo-relative paths that differ between ``old`` and ``new``, verbatim.

    ``-z`` (NUL-separated) rather than one path per line: with the default
    ``core.quotePath`` git prints a path containing a non-ASCII byte or a
    tab QUOTED and octal-escaped (``"static/ts/\\343\\202\\246...ts"``),
    and the classifier would then see a name ending in ``ts"`` instead of
    ``.ts`` and plan nothing. Measured with git 2.43.0 on 2026-09-05; ``-z``
    is the documented way to get the raw bytes back.
    """
    out = _run(clone, "diff", "--name-only", "-z", f"{old}..{new}").stdout
    return [entry for entry in out.split("\0") if entry.strip()]


def is_ancestor(clone: Path, ancestor: str, descendant: str) -> bool:
    """``git merge-base --is-ancestor``: exit 0 -> True, 1 -> False, else raise."""
    argv = [
        "git",
        "-C",
        str(clone),
        "merge-base",
        "--is-ancestor",
        ancestor,
        descendant,
    ]
    completed = subprocess.run(
        argv, capture_output=True, text=True, timeout=_LOCAL_TIMEOUT, check=False
    )
    if completed.returncode == 0:
        return True
    if completed.returncode == 1:
        return False
    raise GitError(argv, completed.returncode, completed.stderr)


# EOF
