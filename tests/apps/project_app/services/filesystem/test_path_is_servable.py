#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""`.git` and `.env` must not be servable, whatever route asks for them.

WHY THIS EXISTS. On 2026-08-18 an anonymous reader of a PUBLIC project could
fetch `.git/HEAD` and `.git/config` with their real contents. Two edge blocks
were deployed the same day and both key on URL SHAPES:

    /<owner>/<repo>/(blob|raw)/...      the repo browser
    /api/workspace/file-content/...     the workspace API

The second block exists only because the first one missed that route entirely
-- the same files, a different prefix. BLOCKING A PATH SHAPE ONLY BLOCKS THE
ROUTES THAT USE IT, and the route enumeration is known to be incomplete: the
audit that found the second route explicitly declined to claim it had found
them all.

`path_is_servable` is the same rule at the filesystem chokepoint, so it covers
routes nobody has enumerated. These tests pin the behaviour the edge blocks
currently provide, so the blocks can eventually be retired against evidence
rather than against hope.

WHAT THIS IS NOT. It is not "refuse every dotfile". `.gitignore` and
`.github/` are ordinary repository content a repo browser is meant to show,
and refusing them would be a UX regression dressed as hardening. Whether the
refused set should grow is a product decision and is deliberately left open.
"""

import pytest

from apps.infra.project_app.services.filesystem.permissions import (
    path_is_servable,
)


@pytest.mark.parametrize(
    "path",
    [
        ".git/HEAD",
        ".git/config",
        ".git/objects/fe/2cc605aa",
        "sub/dir/.git/HEAD",
        ".env",
        "sub/dir/.env",
    ],
    ids=[
        "git-head",
        "git-config",
        "git-loose-object",
        "nested-git",
        "env-at-root",
        "nested-env",
    ],
)
def test_vcs_metadata_and_credentials_are_refused(path):
    """The exact shapes measured serving real content on live prod."""
    # Arrange
    candidate = path

    # Act
    servable = path_is_servable(candidate)

    # Assert
    assert servable is False, f"{candidate!r} must not be servable"


@pytest.mark.parametrize(
    "path",
    [
        "README.md",
        ".gitignore",
        ".github/workflows/ci.yml",
        "src/pkg/module.py",
        "vendor/foo.git/README.md",
        "config/env",
        "environment.yml",
    ],
    ids=[
        "ordinary-file",
        "gitignore-is-content",
        "github-dir-is-content",
        "nested-source",
        "foo.git-is-not-a-git-component",
        "env-as-a-directory-name",
        "filename-merely-starting-with-env",
    ],
)
def test_ordinary_repository_content_is_still_servable(path):
    """The refusal must be component-wise, not a substring match.

    `vendor/foo.git/README.md` and `environment.yml` are the cases a naive
    `".git" in path` or `path.endswith("env")` check would wrongly refuse, and
    `.gitignore` is the one a blanket dotfile rule would take out.
    """
    # Arrange
    candidate = path

    # Act
    servable = path_is_servable(candidate)

    # Assert
    assert servable is True, f"{candidate!r} must remain servable"


def test_backslash_separators_do_not_evade_the_rule():
    """A Windows-style separator must not smuggle a .git component through."""
    # Arrange
    candidate = r"sub\.git\HEAD"

    # Act
    servable = path_is_servable(candidate)

    # Assert
    assert servable is False, "backslash-separated .git must still be refused"


def test_the_refused_set_is_not_empty():
    """Anti-vacuity: an empty rule set would make every refusal test pass.

    Both parametrised suites above assert on a fixed list, so an accidentally
    empty `_REFUSED_PATH_COMPONENTS` would turn the first suite red rather
    than green -- but the helper could still be reduced to `return True` by a
    refactor that keeps the constants and stops consulting them. This asserts
    the rule has teeth independently of the lists above.
    """
    # Arrange
    known_bad = ".git/HEAD"

    # Act
    refuses_something = not path_is_servable(known_bad)

    # Assert
    assert refuses_something, "path_is_servable refuses nothing at all"
