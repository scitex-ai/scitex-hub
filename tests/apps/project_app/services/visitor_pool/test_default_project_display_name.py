#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The visitor default project's NAME is human-facing; its SLUG is not.

WHAT WENT WRONG (prod, measured 2026-07-30)
-------------------------------------------
67 Project rows carried ``slug == name == "default-project"``. The name
was not empty — it was literally set to the slug, by BOTH visitor-pool
creation sites: ``workspace_manager.reset_visitor_workspace`` did
``name=project_slug``, and ``pool_initialization._create_default_project``
hardcoded the same literal in its ``get_or_create`` defaults. So a
first-time visitor's FIRST NOUN was the string ``default-project``, in
the project switcher (operator complaint: 「まずわかりにくい」).

THE TWO-SIDED INVARIANT THIS MODULE LOCKS
-----------------------------------------
The fix is NOT "rename the thing". The slug is load-bearing
infrastructure — ``pool_manager`` allocates on it, ``pool_cleanup`` gates
deletion on it, ``home_state.EXPECTED_PROJ_ENTRIES`` gates the
recycled-home final check on it, the console terminal consumer filters on
it, and Gitea repos live at ``visitor-NNN/default-project``. So both
halves are asserted here, and every negative assertion has a positive
sibling so neither half can pass vacuously:

* the display name is NOT the slug   (the defect)
* the slug is STILL exactly ``default-project``  (the invariant a future
  "let's tidy these two back together" refactor would break — this file
  is where that refactor is supposed to go red)

The backfill migration for the 67 existing rows is covered in
``test_default_project_name_backfill_migration.py``.

Run (SQLite, no network/Gitea — the Gitea client and template clone are
injected as tiny real fakes through the production seams):

    SCITEX_HUB_USE_SQLITE_DEV=1 \
    /opt/venv-sac/bin/python -m pytest <abs path to this file>
"""

from pathlib import Path

import pytest
from django.contrib.auth.models import User

from apps.infra.project_app.models import Project
from apps.infra.project_app.services.visitor_pool.home_state import (
    EXPECTED_PROJ_ENTRIES,
)
from apps.infra.project_app.services.visitor_pool.pool_initialization import (
    PoolInitializer,
)
from apps.infra.project_app.services.visitor_pool.workspace_manager import (
    TEMPLATE_MARKER_RELPATH,
    WorkspaceManager,
)

SLUG = WorkspaceManager.DEFAULT_PROJECT_SLUG
DISPLAY_NAME = WorkspaceManager.DEFAULT_PROJECT_DISPLAY_NAME

REPO_ROOT = Path(__file__).resolve().parents[5]
HEADER_TEMPLATE = (
    REPO_ROOT / "templates" / "global_base_partials" / "global_header.html"
)


# ---------------------------------------------------------------------------
# Tiny real fakes (no unittest.mock) injected through the existing seams
# ---------------------------------------------------------------------------


class FakeGiteaClient:
    """In-memory Gitea: the visitor owns no repos; deletion is a no-op."""

    def list_repositories(self, username):
        return []

    def delete_repository(self, owner, repo):
        return True


def fake_clone(template_id, dest, git_strategy=None):
    """Tiny real clone mirroring the REAL dot-prefixed template layout.

    Builds the marker from ``TEMPLATE_MARKER_RELPATH`` (which
    test_template_marker_reality.py locks against the real packages) so
    this fake cannot drift from what production verifies. Includes
    ``01_manuscript`` so ``ensure_manuscript_record`` actually runs — that
    is the other code path whose text derives from ``project.name``.
    """
    manuscript = Path(dest) / TEMPLATE_MARKER_RELPATH / "01_manuscript"
    manuscript.mkdir(parents=True, exist_ok=True)
    (manuscript / "main.tex").write_text("% fresh template\n")
    return True


def no_container_toolchain(argv, timeout=None):
    """``run_cmd`` seam: a host with no SLURM/apptainer binaries."""
    raise FileNotFoundError(argv[0])


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def visitor(db):
    """A pool visitor whose workspace lives under this test's tmp root.

    The directory-level ``isolated_visitor_data_root`` autouse fixture
    repoints ``settings.BASE_DIR`` at a per-test ``tmp_path``, so the
    hardcoded identity below cannot collide across xdist workers.
    """
    username = "visitor-001"
    return User.objects.create(username=username, email=f"{username}@visitor.local")


@pytest.fixture
def reset_project(visitor):
    """Drive the REAL reset pipeline; return the row it created."""
    WorkspaceManager.reset_visitor_workspace(
        visitor,
        gitea_client=FakeGiteaClient(),
        clone_fn=fake_clone,
        run_cmd=no_container_toolchain,
    )
    return Project.objects.get(owner=visitor, slug=SLUG)


@pytest.fixture
def initialized_project(visitor):
    """Drive the REAL pool-initialization creation site."""
    project, created = PoolInitializer._create_default_project(visitor, SLUG)
    return project, created


@pytest.fixture
def preexisting_named_project(visitor):
    """A visitor who already renamed their default project."""
    Project.objects.create(
        name="My Thesis",
        slug=SLUG,
        owner=visitor,
        visibility="private",
        data_location=f"{visitor.username}/{SLUG}",
    )
    return PoolInitializer._create_default_project(visitor, SLUG)


@pytest.fixture
def header_markup():
    """The raw header template text (the fallback lives in markup)."""
    return HEADER_TEMPLATE.read_text()


# ---------------------------------------------------------------------------
# The constants themselves
# ---------------------------------------------------------------------------


class TestDefaultProjectConstants:
    """One value is human-facing text, the other is infrastructure."""

    def test_display_name_is_the_human_label(self):
        """Positive: the name a first-time visitor should read.

        WAS "My Project", which was honest while the workspace was an
        empty skeleton and said nothing once ``demo_seed`` started
        filling it with a worked example. The name now says WHAT the
        project is and that it is an EXAMPLE — the same complaint the
        operator made about "dotfiles" meaning nothing to a general
        audience.
        """
        # Arrange
        expected = "Handwritten Digits (Example)"
        # Act
        actual = DISPLAY_NAME
        # Assert
        assert actual == expected

    def test_display_name_is_not_the_slug(self):
        """The defect: the human-facing name must not BE the slug."""
        # Arrange
        slug = SLUG
        # Act
        actual = DISPLAY_NAME
        # Assert
        assert actual != slug

    def test_slug_is_still_the_load_bearing_literal(self):
        """The invariant: renaming the slug must fail HERE, loudly."""
        # Arrange
        load_bearing = "default-project"
        # Act
        actual = SLUG
        # Assert
        assert actual == load_bearing

    def test_recycled_home_gate_expects_the_slug_directory(self):
        """Positive cross-check: the on-disk directory is the SLUG."""
        # Arrange
        gate_entries = EXPECTED_PROJ_ENTRIES
        # Act
        actual = SLUG in gate_entries
        # Assert
        assert actual

    def test_recycled_home_gate_does_not_expect_the_display_name(self):
        """Negative sibling: the display name is never a path component."""
        # Arrange
        gate_entries = EXPECTED_PROJ_ENTRIES
        # Act
        actual = DISPLAY_NAME in gate_entries
        # Assert
        assert not actual


# ---------------------------------------------------------------------------
# Creation site 1: the reset pipeline (driven for real)
# ---------------------------------------------------------------------------


class TestResetPipelineNamesProjectForHumans:
    """``WorkspaceManager.reset_visitor_workspace`` — the real code path."""

    def test_name_is_the_display_name(self, reset_project):
        """The row a recycled slot hands to the next visitor."""
        # Arrange
        project = reset_project
        # Act
        actual = project.name
        # Assert
        assert actual == DISPLAY_NAME

    def test_name_is_not_the_slug(self, reset_project):
        """Negative sibling: ``name=project_slug`` must not come back."""
        # Arrange
        project = reset_project
        # Act
        actual = project.name
        # Assert
        assert actual != project.slug

    def test_slug_is_the_load_bearing_literal(self, reset_project):
        """Renaming the name must not have moved the slug."""
        # Arrange
        project = reset_project
        # Act
        actual = project.slug
        # Assert
        assert actual == SLUG

    def test_data_location_still_uses_the_slug(self, reset_project, visitor):
        """The workspace path is built from the slug, not the name."""
        # Arrange
        project = reset_project
        # Act
        actual = project.data_location
        # Assert
        assert actual == f"{visitor.username}/{SLUG}"

    def test_manuscript_title_uses_the_display_name(self, reset_project):
        """``ensure_manuscript_record`` derives its title from the name.

        Side effect of this change, deliberately kept: the title was
        "default-project Manuscript", it is now "My Project Manuscript".
        """
        # Arrange
        from apps.workspace.writer_app.models import Manuscript

        project = reset_project
        # Act
        actual = Manuscript.objects.get(project=project).title
        # Assert
        assert actual == f"{DISPLAY_NAME} Manuscript"

    def test_manuscript_title_does_not_contain_the_slug(self, reset_project):
        """Negative sibling: no slug leaks into the manuscript title."""
        # Arrange
        from apps.workspace.writer_app.models import Manuscript

        project = reset_project
        # Act
        actual = Manuscript.objects.get(project=project).title
        # Assert
        assert SLUG not in actual


# ---------------------------------------------------------------------------
# Creation site 2: pool initialization (driven for real)
# ---------------------------------------------------------------------------


class TestPoolInitializerNamesProjectForHumans:
    """``PoolInitializer._create_default_project`` — the real code path."""

    def test_a_fresh_slot_creates_the_row(self, initialized_project):
        """Guard against a vacuous pass: the row really was created."""
        # Arrange
        _project, created = initialized_project
        # Act
        actual = created
        # Assert
        assert actual

    def test_name_is_the_display_name(self, initialized_project):
        """A freshly initialized pool slot is named for a human."""
        # Arrange
        project, _created = initialized_project
        # Act
        actual = project.name
        # Assert
        assert actual == DISPLAY_NAME

    def test_name_is_not_the_slug(self, initialized_project):
        """Negative sibling: the hardcoded slug literal must not return."""
        # Arrange
        project, _created = initialized_project
        # Act
        actual = project.name
        # Assert
        assert actual != project.slug

    def test_slug_is_the_load_bearing_literal(self, initialized_project):
        """The slug the allocator looks the row up by is unchanged."""
        # Arrange
        project, _created = initialized_project
        # Act
        actual = project.slug
        # Assert
        assert actual == SLUG

    def test_persisted_row_carries_the_display_name(self, initialized_project, visitor):
        """Read it back the way the allocator does — by slug."""
        # Arrange
        _project, _created = initialized_project
        # Act
        actual = Project.objects.get(owner=visitor, slug=SLUG).name
        # Assert
        assert actual == DISPLAY_NAME

    def test_existing_project_is_not_recreated(self, preexisting_named_project):
        """``get_or_create`` found the row rather than making a second."""
        # Arrange
        _project, created = preexisting_named_project
        # Act
        actual = created
        # Assert
        assert not actual

    def test_existing_project_keeps_a_visitor_chosen_name(
        self, preexisting_named_project
    ):
        """The defaults must not clobber a name the visitor picked."""
        # Arrange
        project, _created = preexisting_named_project
        # Act
        actual = project.name
        # Assert
        assert actual == "My Thesis"


# ---------------------------------------------------------------------------
# The template fallback (a nameless project must never render a slug)
# ---------------------------------------------------------------------------


class TestHeaderTemplateFallback:
    """global_header.html renders ``project.name`` with a hardcoded default."""

    def test_both_fallbacks_are_the_display_name(self, header_markup):
        """Positive: both live sites render human text, not the slug.

        WAS THREE, NOW TWO — and this test caught the change, which is
        exactly what it is for. #513 added the fallback at three sites; the
        third lived inside the second, CSS-hidden copy of the project
        selector (``.header-project-selector``, hidden by
        ``header/02-layout.css:19-21``). This PR deletes that dead block, so
        only the two LIVE sites remain.

        Kept as ``== 2`` rather than ``>= 2``: an exact count fails at 1 and
        at 3, so it is the presence assertion and the no-duplicate assertion
        in one expression. ``>=`` would go quiet if a future edit
        reintroduced the hidden copy.
        """
        # Arrange
        human_fallback = f'|default:"{DISPLAY_NAME}"'
        # Act
        actual = header_markup.count(human_fallback)
        # Assert
        assert actual == 2

    def test_no_fallback_renders_the_slug(self, header_markup):
        """Negative sibling, with the marker DERIVED from the live slug.

        ``test_slug_is_still_the_load_bearing_literal`` pins that
        constant, so this cannot pass vacuously by someone renaming it.
        """
        # Arrange
        slug_fallback = f'|default:"{SLUG}"'
        # Act
        actual = header_markup.count(slug_fallback)
        # Assert
        assert actual == 0

    def test_template_still_renders_the_project_name(self, header_markup):
        """Anti-vacuity: the block being asserted on still exists."""
        # Arrange
        rendered_field = "{{ project.name"
        # Act
        actual = header_markup.count(rendered_field)
        # Assert
        assert actual >= 3


if __name__ == "__main__":
    import os

    pytest.main([os.path.abspath(__file__)])

# EOF
