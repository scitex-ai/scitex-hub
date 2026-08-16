#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Migration 0039: backfill the visitor default project's display name.

The 67 prod rows that carried ``slug == name == "default-project"`` are
renamed by ``apps/infra/project_app/migrations/
0039_default_project_display_name.py``. Three properties matter, and each
is asserted with a positive/negative sibling pair so none can pass
vacuously:

1. it renames ONLY ``name`` — the slug is load-bearing infrastructure
   (pool_manager / pool_cleanup / home_state / console consumer / the
   Gitea path ``visitor-NNN/default-project``) and must come out
   byte-identical;
2. it is IDEMPOTENT — a second run is a no-op, and a project the visitor
   renamed themselves is never touched;
3. it REVERSES — reverse puts the slug back in ``name`` for exactly the
   rows the forward pass renamed.

The migration carries a frozen snapshot of the two literals (a migration
must not import application code). ``TestMigrationLiterals`` pins that
snapshot to the live constants so it cannot silently drift.

Run (SQLite):

    SCITEX_HUB_USE_SQLITE_DEV=1 \
    /opt/venv-sac/bin/python -m pytest <abs path to this file>
"""

import importlib

import pytest
from django.apps import apps as global_apps
from django.contrib.auth.models import User

from apps.infra.project_app.models import Project
from apps.infra.project_app.services.visitor_pool.workspace_manager import (
    WorkspaceManager,
)

SLUG = WorkspaceManager.DEFAULT_PROJECT_SLUG
DISPLAY_NAME = WorkspaceManager.DEFAULT_PROJECT_DISPLAY_NAME

MIGRATION = importlib.import_module(
    "apps.infra.project_app.migrations.0039_default_project_display_name"
)


def _run_forward():
    """Run the real forward pass against the real app registry."""
    MIGRATION.name_default_projects_for_humans(global_apps, None)


def _run_reverse():
    """Run the real reverse pass against the real app registry."""
    MIGRATION.restore_slug_as_name(global_apps, None)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def owner(db):
    return User.objects.create(
        username="visitor-001", email="visitor-001@visitor.local"
    )


def _mk_project(owner, *, name, slug=SLUG):
    return Project.objects.create(
        name=name,
        slug=slug,
        owner=owner,
        visibility="private",
        data_location=f"{owner.username}/{slug}",
    )


@pytest.fixture
def prod_shaped_row(owner):
    """The exact prod shape: name is literally the slug."""
    return _mk_project(owner, name=SLUG)


@pytest.fixture
def backfilled_row(prod_shaped_row):
    """One forward pass applied."""
    _run_forward()
    prod_shaped_row.refresh_from_db()
    return prod_shaped_row


@pytest.fixture
def twice_backfilled_row(backfilled_row):
    """Two forward passes applied — the idempotency probe."""
    _run_forward()
    backfilled_row.refresh_from_db()
    return backfilled_row


@pytest.fixture
def reversed_row(backfilled_row):
    """Forward then reverse."""
    _run_reverse()
    backfilled_row.refresh_from_db()
    return backfilled_row


@pytest.fixture
def visitor_renamed_row(owner):
    """A default project the visitor titled themselves."""
    return _mk_project(owner, name="My Thesis")


@pytest.fixture
def unrelated_slug_row(owner):
    """A NON-default project that happens to be named after its slug."""
    return _mk_project(owner, name="my-paper", slug="my-paper")


# ---------------------------------------------------------------------------
# The frozen snapshot must track the live authority
# ---------------------------------------------------------------------------


class TestMigrationLiterals:
    """The migration duplicates two literals; they must not drift."""

    def test_slug_literal_matches_the_live_constant(self):
        """Positive: the migration targets the slug the code still uses."""
        # Arrange
        live = SLUG
        # Act
        actual = MIGRATION.DEFAULT_PROJECT_SLUG
        # Assert
        assert actual == live

    def test_display_name_literal_matches_the_live_constant(self):
        """Positive: the backfilled value is the one the code writes."""
        # Arrange
        live = DISPLAY_NAME
        # Act
        actual = MIGRATION.DEFAULT_PROJECT_DISPLAY_NAME
        # Assert
        assert actual == live

    def test_the_two_migration_literals_differ(self):
        """Negative sibling: a no-op migration would be silently useless."""
        # Arrange
        slug_literal = MIGRATION.DEFAULT_PROJECT_SLUG
        # Act
        actual = MIGRATION.DEFAULT_PROJECT_DISPLAY_NAME
        # Assert
        assert actual != slug_literal


# ---------------------------------------------------------------------------
# Forward: renames name, never slug
# ---------------------------------------------------------------------------


class TestForwardBackfill:
    """The 67 prod rows get a human-facing name."""

    def test_row_starts_out_named_after_its_slug(self, prod_shaped_row):
        """Anti-vacuity: confirm the defect shape before migrating."""
        # Arrange
        row = prod_shaped_row
        # Act
        actual = row.name
        # Assert
        assert actual == row.slug

    def test_forward_sets_the_display_name(self, backfilled_row):
        """Positive: the name a visitor now reads."""
        # Arrange
        row = backfilled_row
        # Act
        actual = row.name
        # Assert
        assert actual == DISPLAY_NAME

    def test_forward_leaves_the_name_unequal_to_the_slug(self, backfilled_row):
        """Negative sibling: the defect shape is gone."""
        # Arrange
        row = backfilled_row
        # Act
        actual = row.name
        # Assert
        assert actual != row.slug

    def test_forward_does_not_alter_the_slug(self, backfilled_row):
        """The load-bearing field comes out byte-identical."""
        # Arrange
        row = backfilled_row
        # Act
        actual = row.slug
        # Assert
        assert actual == SLUG

    def test_forward_does_not_alter_the_data_location(self, backfilled_row):
        """The slug-derived workspace path is untouched too."""
        # Arrange
        row = backfilled_row
        # Act
        actual = row.data_location
        # Assert
        assert actual == f"{row.owner.username}/{SLUG}"


# ---------------------------------------------------------------------------
# Idempotency
# ---------------------------------------------------------------------------


class TestForwardIsIdempotent:
    """A second run must be a no-op, not a re-rename."""

    def test_second_run_keeps_the_display_name(self, twice_backfilled_row):
        """Positive: still exactly one rename applied."""
        # Arrange
        row = twice_backfilled_row
        # Act
        actual = row.name
        # Assert
        assert actual == DISPLAY_NAME

    def test_second_run_keeps_the_slug(self, twice_backfilled_row):
        """The slug survives repeated application."""
        # Arrange
        row = twice_backfilled_row
        # Act
        actual = row.slug
        # Assert
        assert actual == SLUG

    def test_forward_leaves_a_visitor_chosen_name_alone(
        self, visitor_renamed_row
    ):
        """Only rows still named after their slug are touched."""
        # Arrange
        row = visitor_renamed_row
        # Act
        _run_forward()
        row.refresh_from_db()
        # Assert
        assert row.name == "My Thesis"

    def test_forward_leaves_another_slugs_name_alone(self, unrelated_slug_row):
        """A non-default project named after ITS slug is not our business."""
        # Arrange
        row = unrelated_slug_row
        # Act
        _run_forward()
        row.refresh_from_db()
        # Assert
        assert row.name == "my-paper"

    def test_forward_leaves_another_slug_unchanged(self, unrelated_slug_row):
        """Negative sibling: no other slug is rewritten either."""
        # Arrange
        row = unrelated_slug_row
        # Act
        _run_forward()
        row.refresh_from_db()
        # Assert
        assert row.slug == "my-paper"


# ---------------------------------------------------------------------------
# Reverse
# ---------------------------------------------------------------------------


class TestReverseBackfill:
    """Reverse undoes exactly what forward did."""

    def test_reverse_restores_the_slug_as_the_name(self, reversed_row):
        """Positive: back to the pre-migration shape."""
        # Arrange
        row = reversed_row
        # Act
        actual = row.name
        # Assert
        assert actual == SLUG

    def test_reverse_does_not_alter_the_slug(self, reversed_row):
        """Negative sibling: reversing the name never moves the slug."""
        # Arrange
        row = reversed_row
        # Act
        actual = row.slug
        # Assert
        assert actual == SLUG

    def test_reverse_leaves_a_visitor_chosen_name_alone(
        self, visitor_renamed_row
    ):
        """Reverse must not retitle a project the visitor named."""
        # Arrange
        row = visitor_renamed_row
        # Act
        _run_reverse()
        row.refresh_from_db()
        # Assert
        assert row.name == "My Thesis"


if __name__ == "__main__":
    import os

    pytest.main([os.path.abspath(__file__)])

# EOF
