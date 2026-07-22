#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Sibling-prefix path escape in the project directory-browsing views.

FINDING (2026-07-22)
    Four modules guarded the project root with a STRING PREFIX::

        full = (project_path / user_supplied).resolve()
        if not str(full).startswith(str(project_path.resolve())):
            reject()

    ``str.startswith`` is not path containment. A SIBLING directory whose
    name merely EXTENDS the project root satisfies it: for the root
    ``/…/proj`` the resolved path ``/…/proj-other/secret.md`` does start
    with ``/…/proj``, so the URL segment ``../proj-other/secret.md``
    sails straight through the guard and the view proceeds to read,
    list, or concatenate another project's files.

    Sites (each fed by an attacker-controlled URL segment):
      - views/directory_views/browse.py:73    project_directory_dynamic
      - views/directory_views/browse.py:225   project_directory
      - views/directory_views/file_view_utils.py:50  get_file_context
      - views/directory_views/helpers.py:105  _validate_path_security
      - views/api/directory_concatenation.py:65  api_concatenate_directory

    ``api_concatenate_directory`` is the sharpest: it rglob()s the escaped
    directory and returns every whitelisted file's CONTENT in the JSON body.

FIX
    ``validate_path_in_project()`` — component-wise containment via
    ``Path.resolve().relative_to()`` — at all five sites.

TEST STRATEGY (and its honest limits)
    ``_validate_path_security`` is the one guard in this batch that takes
    its collaborators as PARAMETERS, so the escape is reproduced against
    the real production function on a real tmp filesystem — no database,
    no patching.

    The other four guards are inline in views whose first statement is
    ``get_object_or_404(...)``. Driving them needs either a migrated test
    database (not available to this suite) or rewriting production
    internals from the test (forbidden ecosystem-wide: STX-NM002). They
    are therefore pinned two ways that both flip when the fix is
    reverted: the vulnerable prefix expression must be absent from the
    source, and each module must actually bind the real
    ``validate_path_in_project`` callable.
"""

import re
from pathlib import Path

import pytest

from apps.infra.project_app.services.filesystem.permissions import (
    validate_path_in_project,
)
from apps.infra.project_app.views.api import directory_concatenation as concat_mod
from apps.infra.project_app.views.directory_views import browse as browse_mod
from apps.infra.project_app.views.directory_views import file_view_utils as fvu_mod
from apps.infra.project_app.views.directory_views import helpers as helpers_mod

pytestmark = pytest.mark.security

OWNER = "alice"
SLUG = "proj"
# The sibling's name EXTENDS the project root's — the whole point of the finding.
SIBLING_SLUG = "proj-other"
SECRET = "sibling-project-secret-must-not-leak\n"
OWN_CONTENT = "my own project file\n"

ESCAPE_FILE = f"../{SIBLING_SLUG}/secret.md"
LEGIT_FILE = "scripts/mine.md"

REPO_ROOT = Path(__file__).resolve().parents[2]

# Every module in this batch that decides "is this path inside the project?".
GUARDED_MODULES = {
    "apps/infra/project_app/views/directory_views/browse.py": browse_mod,
    "apps/infra/project_app/views/directory_views/helpers.py": helpers_mod,
    "apps/infra/project_app/views/directory_views/file_view_utils.py": fvu_mod,
    "apps/infra/project_app/views/api/directory_concatenation.py": concat_mod,
}

# The vulnerable shape: containment decided by a string prefix on the root.
PREFIX_GUARD = re.compile(r"startswith\(\s*str\([A-Za-z_.]*project_path\.resolve\(\)")


@pytest.fixture
def tree(tmp_path):
    """A project root with a same-prefix sibling holding the secret."""
    projects = tmp_path / "projects"
    root = projects / SLUG
    (root / "scripts").mkdir(parents=True)
    (root / LEGIT_FILE).write_text(OWN_CONTENT)

    sibling = projects / SIBLING_SLUG
    sibling.mkdir(parents=True)
    (sibling / "secret.md").write_text(SECRET)

    return {"root": root, "sibling": sibling}


# ---------------------------------------------------------------------------
# helpers._validate_path_security — the real guard, driven end to end
# ---------------------------------------------------------------------------


def _validate(full_path, root):
    """Return whatever the helper yields, or the exception it raised.

    The helper's reject branch calls ``messages.error(None, ...)``, which
    raises before the redirect is built. That is a separate pre-existing
    wart; what matters here is that a rejected path is never handed back.
    """
    try:
        return helpers_mod._validate_path_security(full_path, root, OWNER, SLUG)
    except Exception as exc:
        return exc


@pytest.fixture
def escape_result(tree):
    return _validate(tree["root"] / ESCAPE_FILE, tree["root"])


def test_helper_never_returns_a_same_prefix_sibling_path(escape_result):
    # Arrange
    result = escape_result
    # Act
    leaked = isinstance(result, Path)
    # Assert
    assert leaked is False, f"guard handed back {result}"


def test_helper_never_returns_a_path_that_reads_the_sibling_secret(escape_result, tree):
    # Arrange
    result = escape_result
    # Act
    text = result.read_text() if isinstance(result, Path) and result.is_file() else ""
    # Assert
    assert SECRET.strip() not in text


@pytest.fixture
def legit_result(tree):
    return _validate(tree["root"] / LEGIT_FILE, tree["root"])


def test_helper_still_returns_an_in_root_path(legit_result, tree):
    # Arrange
    expected = (tree["root"] / LEGIT_FILE).resolve()
    # Act
    result = legit_result
    # Assert
    assert result == expected


def test_helper_still_reads_the_projects_own_file(legit_result):
    # Arrange
    result = legit_result
    # Act
    text = result.read_text() if isinstance(result, Path) else ""
    # Assert
    assert text == OWN_CONTENT


# ---------------------------------------------------------------------------
# validate_path_in_project — the containment the other four sites now use
# ---------------------------------------------------------------------------


def test_containment_rejects_the_same_prefix_sibling(tree):
    # Arrange
    escaped = (tree["root"] / ESCAPE_FILE).resolve()
    # Act
    contained = validate_path_in_project(tree["root"], escaped)
    # Assert
    assert contained is False, f"{escaped} accepted as inside {tree['root']}"


def test_containment_accepts_an_in_root_path(tree):
    # Arrange
    legit = (tree["root"] / LEGIT_FILE).resolve()
    # Act
    contained = validate_path_in_project(tree["root"], legit)
    # Assert
    assert contained is True


def test_the_escape_defeats_a_string_prefix_check(tree):
    """Pin the premise: the old expression really did admit the sibling."""
    # Arrange
    escaped = (tree["root"] / ESCAPE_FILE).resolve()
    # Act
    old_check_passed = str(escaped).startswith(str(tree["root"].resolve()))
    # Assert
    assert old_check_passed is True


# ---------------------------------------------------------------------------
# The four inline guards
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("relpath", sorted(GUARDED_MODULES))
def test_no_project_root_is_guarded_by_a_string_prefix(relpath):
    # Arrange
    source = (REPO_ROOT / relpath).read_text()
    # Act
    offenders = PREFIX_GUARD.findall(source)
    # Assert
    assert offenders == [], f"{relpath} still decides containment by prefix"


@pytest.mark.parametrize("relpath", sorted(GUARDED_MODULES))
def test_every_guarded_module_binds_the_real_containment_helper(relpath):
    # Arrange
    module = GUARDED_MODULES[relpath]
    # Act
    bound = getattr(module, "validate_path_in_project", None)
    # Assert
    assert bound is validate_path_in_project, f"{relpath} does not use the helper"

# EOF
