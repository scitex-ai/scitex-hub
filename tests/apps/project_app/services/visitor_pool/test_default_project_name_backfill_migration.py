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
snapshot so it cannot silently drift.

WHICH MIGRATION HOLDS THE LIVE NAME — read this before "fixing" a failure
here. 0039's ``DEFAULT_PROJECT_DISPLAY_NAME`` used to be pinned to
``WorkspaceManager.DEFAULT_PROJECT_DISPLAY_NAME``, which was right only
while 0039 was the LAST backfill. It no longer is: 0040
(``0040_default_project_names_the_demo``) renames those same rows again,
onto the demo project's name, now that ``demo_seed`` gives the workspace
content worth naming. An APPLIED migration must never be edited, so 0039's
literal is now asserted as the FROZEN historical value it is, and the pin
to the live constant moved to 0040 — the newest link in the chain, which
is the only one whose output the code still has to agree with. When a
future rename lands, add 0041 and move the pin again; do not touch 0039 or
0040.

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
MIGRATION_0040 = importlib.import_module(
    "apps.infra.project_app.migrations.0040_default_project_names_the_demo"
)

# 0039's output, frozen. Everything in this module that asserts what 0039
# DOES reads it from the migration itself rather than from the live
# constant, because the live constant has moved on to 0040's value.
NAME_AFTER_0039 = MIGRATION.DEFAULT_PROJECT_DISPLAY_NAME


def _run_forward():
    """Run the real forward pass against the real app registry."""
    MIGRATION.name_default_projects_for_humans(global_apps, None)


def _run_reverse():
    """Run the real reverse pass against the real app registry."""
    MIGRATION.restore_slug_as_name(global_apps, None)


def _run_forward_0040():
    """Run 0040's real forward pass against the real app registry."""
    MIGRATION_0040.name_default_projects_for_the_demo(global_apps, None)


def _run_reverse_0040():
    """Run 0040's real reverse pass against the real app registry."""
    MIGRATION_0040.restore_previous_display_name(global_apps, None)


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
def demo_named_row(backfilled_row):
    """The full chain a prod row actually travels: 0039 then 0040."""
    _run_forward_0040()
    backfilled_row.refresh_from_db()
    return backfilled_row


@pytest.fixture
def twice_demo_named_row(demo_named_row):
    """0040 applied twice — the idempotency probe for the new link."""
    _run_forward_0040()
    demo_named_row.refresh_from_db()
    return demo_named_row


@pytest.fixture
def demo_reversed_row(demo_named_row):
    """0039 forward, 0040 forward, 0040 reverse."""
    _run_reverse_0040()
    demo_named_row.refresh_from_db()
    return demo_named_row


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

    def test_0039_display_name_literal_is_the_frozen_historical_value(self):
        """0039 is APPLIED and must never be edited, so its literal is
        asserted as history — not against the live constant, which has
        since moved to 0040's value."""
        # Arrange
        historical = "My Project"
        # Act
        actual = MIGRATION.DEFAULT_PROJECT_DISPLAY_NAME
        # Assert
        assert actual == historical

    def test_newest_migration_display_name_matches_the_live_constant(self):
        """Positive: the LAST link in the backfill chain writes the name the
        code writes. This is the pin that keeps snapshot and code in step."""
        # Arrange
        live = DISPLAY_NAME
        # Act
        actual = MIGRATION_0040.DEFAULT_PROJECT_DISPLAY_NAME
        # Assert
        assert actual == live

    def test_0040_hands_off_from_0039(self):
        """The chain must not have a gap: 0040 renames exactly the rows
        0039 produced. A typo here would leave every row un-renamed and
        the migration silently useless."""
        # Arrange
        produced_by_0039 = MIGRATION.DEFAULT_PROJECT_DISPLAY_NAME
        # Act
        actual = MIGRATION_0040.PREVIOUS_DISPLAY_NAME
        # Assert
        assert actual == produced_by_0039

    def test_0040_actually_changes_the_name(self):
        """Negative sibling: a rename to the same string is a no-op."""
        # Arrange
        before = MIGRATION_0040.PREVIOUS_DISPLAY_NAME
        # Act
        actual = MIGRATION_0040.DEFAULT_PROJECT_DISPLAY_NAME
        # Assert
        assert actual != before

    def test_0040_targets_the_same_slug(self):
        """Both links address the same rows."""
        # Arrange
        live = SLUG
        # Act
        actual = MIGRATION_0040.DEFAULT_PROJECT_SLUG
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
        """Positive: the name 0039 writes.

        Asserted against 0039's OWN frozen literal, not the live constant:
        this class tests what 0039 does, and 0040 renames these rows again
        afterwards. ``TestDemoRenameChain`` covers the end state.
        """
        # Arrange
        row = backfilled_row
        # Act
        actual = row.name
        # Assert
        assert actual == NAME_AFTER_0039

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
        assert actual == NAME_AFTER_0039

    def test_second_run_keeps_the_slug(self, twice_backfilled_row):
        """The slug survives repeated application."""
        # Arrange
        row = twice_backfilled_row
        # Act
        actual = row.slug
        # Assert
        assert actual == SLUG

    def test_forward_leaves_a_visitor_chosen_name_alone(self, visitor_renamed_row):
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

    def test_reverse_leaves_a_visitor_chosen_name_alone(self, visitor_renamed_row):
        """Reverse must not retitle a project the visitor named."""
        # Arrange
        row = visitor_renamed_row
        # Act
        _run_reverse()
        row.refresh_from_db()
        # Assert
        assert row.name == "My Thesis"


# ---------------------------------------------------------------------------
# 0040: the same rows again, now that the workspace HAS content
# ---------------------------------------------------------------------------


class TestDemoRenameChain:
    """The end state of the whole chain — what a visitor's switcher reads.

    Without 0040 the new name would reach only slots that get RECYCLED after
    deploy, so an already-provisioned row would keep reading "My Project"
    while the manuscript inside it is the digits example.
    """

    def test_chain_ends_at_the_live_display_name(self, demo_named_row):
        """Positive: 0039 then 0040 lands on the name the code writes."""
        # Arrange
        row = demo_named_row
        # Act
        actual = row.name
        # Assert
        assert actual == DISPLAY_NAME

    def test_chain_leaves_0039s_name_behind(self, demo_named_row):
        """Negative sibling: the intermediate value is really gone."""
        # Arrange
        row = demo_named_row
        # Act
        actual = row.name
        # Assert
        assert actual != NAME_AFTER_0039

    def test_chain_does_not_alter_the_slug(self, demo_named_row):
        """The load-bearing field survives BOTH links byte-identical."""
        # Arrange
        row = demo_named_row
        # Act
        actual = row.slug
        # Assert
        assert actual == SLUG

    def test_chain_does_not_alter_the_data_location(self, demo_named_row):
        """The slug-derived workspace path is untouched by 0040 too."""
        # Arrange
        row = demo_named_row
        # Act
        actual = row.data_location
        # Assert
        assert actual == f"{row.owner.username}/{SLUG}"

    def test_0040_is_idempotent(self, twice_demo_named_row):
        """A second run is a no-op, not a re-rename."""
        # Arrange
        row = twice_demo_named_row
        # Act
        actual = row.name
        # Assert
        assert actual == DISPLAY_NAME

    def test_0040_leaves_a_visitor_chosen_name_alone(self, visitor_renamed_row):
        """A visitor who named their own project keeps that name."""
        # Arrange
        row = visitor_renamed_row
        # Act
        _run_forward_0040()
        row.refresh_from_db()
        # Assert
        assert row.name == "My Thesis"

    def test_0040_reverse_restores_0039s_name(self, demo_reversed_row):
        """Positive: reverse hands the row back to 0039's output, so the
        pair 0039/0040 remains reversible as a chain."""
        # Arrange
        row = demo_reversed_row
        # Act
        actual = row.name
        # Assert
        assert actual == NAME_AFTER_0039

    def test_0040_reverse_does_not_alter_the_slug(self, demo_reversed_row):
        """Negative sibling: reversing the name never moves the slug."""
        # Arrange
        row = demo_reversed_row
        # Act
        actual = row.slug
        # Assert
        assert actual == SLUG

    def test_0040_does_not_touch_a_non_default_project(self, unrelated_slug_row):
        """A project with a different slug is out of scope entirely."""
        # Arrange
        row = unrelated_slug_row
        # Act
        _run_forward_0040()
        row.refresh_from_db()
        # Assert
        assert row.name == "my-paper"


if __name__ == "__main__":
    import os

    pytest.main([os.path.abspath(__file__)])

# EOF
