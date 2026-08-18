#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Copy-on-edit backups of tracked files are prohibited — git is the archive.

WHY THIS TEST EXISTS. The constitution is explicit: "Copy-on-edit snapshots —
``.old/<timestamp>/`` directories, ``spec.yaml.bak-*`` files — are hand-rolled
version control outside git: no author, no diff, no ``log``. They are prohibited
for anything git tracks." Nothing enforced that, so the rule was kept by memory,
and memory is exactly what fails at the moment it matters.

WHAT IT COST, measured on this checkout 2026-08-15. A single stale backup was
failing a PUBLIC-FACING gate, and had been for four months:

    tests/config/test_public_repo_urls_are_canonical.py FAILED x2
      'github.com/ywatanabe1989/SciTeX-Code'   appears in [...landing_demos.html.bak]
      'github.com/ywatanabe1989/SciTeX-Writer' appears in [...landing_demos.html.bak]

    the .bak            untracked, gitignored, mtime 2026-04-09
    the tracked original beside it   already CLEAN — fixed long ago

So the real template was correct and a forgotten copy of it kept a public-URL gate
red. Archiving the copy turned that suite from 2 failed to 14 passed, with no
change to any tracked file.

WHY CI NEVER SAW IT, which is the part worth keeping. That URL gate walks the
FILESYSTEM. CI walks a fresh clone, so CI only ever sees TRACKED files and the
backup was invisible to it by construction — the gate is correct and was pointed
at a different subject than the one that ships on a long-lived host. This test has
the same property and therefore the same limitation: it is worth real money only
when run where the files actually live. See
``hub-filesystem-walking-gates-are-blind-in-ci-20260815``.

WHAT COUNTS AS A BACKUP, and why the rule keys on the TRACKED ORIGINAL. Stripping
a backup suffix must land on a file git tracks. That is what separates
``landing_demos.html.bak`` (a shadow copy of a tracked template — prohibited) from
a file that merely ends in ``.orig`` on its own terms. Keying on the original also
means this test says nothing about scratch files with no tracked counterpart; the
constitution's objection is specifically to hand-rolled version control of
something git is already versioning.

WHAT THIS TEST DOES NOT DO, deliberately. It does not delete anything. A failure
names the file and the tracked original it shadows, and the fix is a one-line move
into ``.old/<timestamp>/`` — which the constitution prescribes for UNTRACKED
artifacts, and which is reversible. Encoding an automatic deletion would turn a
tidiness rule into a destructive one.

This test does not hit the network and shells out to git only to ask which paths
are tracked.
"""

import re
import subprocess
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]

# Suffixes that mean "a copy of the file next to me, kept by hand". Each is
# anchored at the END of the name. The trailing-anything forms (`.bak-p0-2026...`,
# `.bak-20260812-portbind`) are real spellings observed in this checkout, which is
# why a bare `.bak` match would have been too narrow.
_BACKUP_SUFFIX = re.compile(
    r"""
    (
        \. (?: bak | backup | orig | save | old | copy )  # .bak  .orig  .save ...
        (?: [-.~] .* )?                                   # ...and .bak-20260812-x
      | ~                                                 # emacs-style trailing ~
      | \. rej                                            # a conflict leftover
    )
    $
    """,
    re.VERBOSE | re.IGNORECASE,
)

# Directories whose contents are not ours to police: dependency trees, build
# output, and the archive location the constitution itself prescribes as the
# CORRECT destination for these files.
_EXEMPT_PARTS = frozenset(
    {
        ".git",
        ".old",  # where a superseded untracked artifact is SUPPOSED to go
        ".worktrees",
        "node_modules",
        ".venv",
        "__pycache__",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        "externals",  # vendored upstream source; their housekeeping, not ours
    }
)


def _tracked_paths() -> frozenset:
    """Every path git tracks, repo-relative. Empty set is a hard failure, not 'clean'."""
    completed = subprocess.run(
        ["git", "-C", str(_REPO_ROOT), "ls-files", "-z"],
        capture_output=True,
        text=True,
        check=True,
    )
    return frozenset(p for p in completed.stdout.split("\0") if p)


def _strip_backup_suffix(name: str) -> "str | None":
    """Return the name this file is a backup OF, or None if it is not backup-shaped."""
    match = _BACKUP_SUFFIX.search(name)
    if match is None:
        return None
    stripped = name[: match.start()]
    return stripped or None


def _candidate_files():
    """Every file under the repo, skipping trees we do not police."""
    for path in _REPO_ROOT.rglob("*"):
        if not path.is_file():
            continue
        if _EXEMPT_PARTS.intersection(path.relative_to(_REPO_ROOT).parts):
            continue
        yield path


def _shadow_copies_of_tracked_files():
    """(backup, the tracked original it shadows) for every prohibited copy on disk."""
    tracked = _tracked_paths()
    found = []
    for path in _candidate_files():
        relative = path.relative_to(_REPO_ROOT)
        original_name = _strip_backup_suffix(relative.name)
        if original_name is None:
            continue
        original = relative.with_name(original_name)
        if original.as_posix() in tracked:
            found.append((relative.as_posix(), original.as_posix()))
    return sorted(found)


def test_git_is_readable_so_this_test_can_actually_fail():
    """Anti-vacuity: if `ls-files` returns nothing, every assertion below passes for
    the wrong reason. A uniqueness/absence check over an empty corpus measures
    nothing while reporting success, which is the exact defect class this repo keeps
    shipping (hub-guards-must-demonstrate-their-own-red-20260815)."""
    tracked = _tracked_paths()
    assert len(tracked) > 1000, (
        f"git ls-files returned {len(tracked)} paths, which is far too few for this "
        f"repo — the scan is not seeing the tree, so the backup check below would "
        f"pass without checking anything. Verify {_REPO_ROOT} is a git checkout."
    )


def test_no_copy_on_edit_backups_of_tracked_files():
    """A tracked file must not have a hand-made shadow copy beside it."""
    shadows = _shadow_copies_of_tracked_files()
    assert shadows == [], (
        "Copy-on-edit backups of TRACKED files were found. git already holds the "
        "history of each original — with an author, a diff and a log, none of which "
        "a .bak has. A stale copy is not inert: one of these kept a public-URL gate "
        "red for four months while the real template was already fixed.\n\n"
        + "\n".join(f"    {backup}\n        shadows {original}" for backup, original in shadows)
        + "\n\nFIX: move it to .old/<YYYYMMDD>/ (gitignored, reversible, and what the "
        "constitution prescribes for untracked artifacts) — or delete it, since the "
        "original is in git:\n"
        "    mkdir -p .old/$(date +%Y%m%d) && mv <path> .old/$(date +%Y%m%d)/\n"
        "Do NOT simply add it to .gitignore: that hides it from git while leaving it "
        "in the working tree, where filesystem-walking gates still read it."
    )


@pytest.mark.parametrize(
    "name,expected",
    [
        ("landing_demos.html.bak", "landing_demos.html"),
        ("nginx_prod.conf.bak-p0-20260724", "nginx_prod.conf"),
        ("docker-compose.staging.yml.bak-20260812-portbind", "docker-compose.staging.yml"),
        ("settings.py.orig", "settings.py"),
        ("urls.py~", "urls.py"),
        ("models.py.rej", "models.py"),
        ("spec.yaml.save", "spec.yaml"),
    ],
)
def test_backup_shapes_this_repo_has_actually_produced_are_recognised(name, expected):
    """The suffix list is derived from spellings seen in this checkout, not invented."""
    assert _strip_backup_suffix(name) == expected


@pytest.mark.parametrize(
    "name",
    [
        "settings.py",
        "README.md",
        "docker-compose.staging.yml",
        "backup_service.py",  # 'backup' as a WORD, not a suffix
        "oldest_first.py",  # 'old' inside a word
        ".gitignore",
    ],
)
def test_ordinary_names_are_not_mistaken_for_backups(name):
    """False positives here would fail honest work, so the pattern must stay anchored."""
    assert _strip_backup_suffix(name) is None
