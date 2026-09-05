#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: tests/apps/project_app/services/visitor_pool/test_visitors_open_on_the_demo.py
"""A provisioned visitor slot opens on the demo, never on the shell config.

WHAT WENT WRONG (develop preview, measured 2026-09-05)
------------------------------------------------------
Four fresh slots were provisioned with ``create_visitor_pool``. Minutes later,
loading the site as a new visitor gave a page whose TITLE was
``dotfiles — SciTeX (dev)`` and whose header's first word was ``dotfiles`` —
the shell-config project (bashrc, gitconfig, screenrc), not the seeded demo
sitting beside it. Operator the same day:
「入ってきたユーザが今だと意味不明なので戻っちゃう」 — an arriving user finds it
meaningless and leaves.

WHY IT CAME BACK AFTER BEING "FIXED"
------------------------------------
Migration ``accounts_app.0014_visitors_land_on_the_demo_project`` repaired the
sixteen rows that existed on 2026-08-16. A data migration cannot repair rows
written after it runs, and provisioning keeps writing them: the USER is created
first, so ``accounts_app.signals`` points the profile at ``dotfiles`` while it
is the only project that exists, and ``_adopt_landing_project`` then refuses to
overwrite an existing pointer — correctly, because for a signed-in human that
pointer is a choice.

So the repair belongs at the two provisioning sites, which is what
``visitor_pool.landing.land_visitor_on`` is, and these tests pin BOTH of them.
The sibling contract (never rewrite a human's choice) is pinned by
``tests/apps/accounts_app/test_signals_landing_project.py`` and must keep
passing — this file does not touch that path.

WHAT EACH TEST IS FOR
  pool_initialisation_opens_the_slot_on_the_demo
      the site that provisioned the slots the operator saw.
  the_landing_project_is_not_the_home_project
      the defect in its own words, on the same provisioned user.
  land_visitor_on_moves_a_profile_parked_on_dotfiles
      the unit, against the exact state provisioning leaves behind.
  land_visitor_on_reports_when_nothing_moved
      it is idempotent, so a second provisioning pass is not a write.
  a_profileless_user_does_not_break_provisioning
      best-effort by design: a slot must stay servable.
"""

import pytest
from django.contrib.auth import get_user_model

from apps.infra.project_app.models import Project
from apps.infra.project_app.services.visitor_pool.landing import land_visitor_on
from apps.infra.project_app.services.visitor_pool.pool_initialization import (
    PoolInitializer,
)
from apps.infra.project_app.services.visitor_pool.workspace_manager import (
    WorkspaceManager,
)

pytestmark = pytest.mark.django_db

SLUG = WorkspaceManager.DEFAULT_PROJECT_SLUG
DISPLAY_NAME = WorkspaceManager.DEFAULT_PROJECT_DISPLAY_NAME


@pytest.fixture(name="visitor")
def _visitor():
    """A visitor exactly as provisioning leaves it: parked on dotfiles.

    The User post_save signal creates the profile AND the home project, then
    points the profile at it — this fixture asserts nothing, it reproduces
    that state so the tests below act on the real thing.
    """
    User = get_user_model()
    return User.objects.create_user(username="visitor-901", password="x")


@pytest.fixture(name="visitor_with_demo")
def _visitor_with_demo(visitor):
    """The same visitor, plus the demo project provisioning creates second."""
    Project.objects.create(
        name=DISPLAY_NAME,
        slug=SLUG,
        owner=visitor,
        visibility="private",
        data_location=f"{visitor.username}/{SLUG}",
    )
    return visitor


def test_pool_initialisation_opens_the_slot_on_the_demo(visitor):
    # Arrange — the provisioning site the operator's four slots came from.
    project, _ = PoolInitializer._create_default_project(visitor, SLUG)
    land_visitor_on(visitor, project)
    visitor.profile.refresh_from_db()
    # Act
    landing = visitor.profile.last_active_repository
    # Assert
    assert landing.slug == SLUG, (
        "a freshly provisioned visitor opens on "
        f"{landing.slug!r}; the operator saw 'dotfiles' as the first word "
        "on the page and said an arriving user leaves"
    )


def test_the_landing_project_is_not_the_home_project(visitor):
    # Arrange
    project, _ = PoolInitializer._create_default_project(visitor, SLUG)
    land_visitor_on(visitor, project)
    visitor.profile.refresh_from_db()
    # Act
    landing = visitor.profile.last_active_repository
    # Assert
    assert landing.is_home is False


def test_land_visitor_on_moves_a_profile_parked_on_dotfiles(visitor_with_demo):
    # Arrange — the state provisioning leaves: pointer on the home project.
    home = Project.objects.get(owner=visitor_with_demo, is_home=True)
    visitor_with_demo.profile.last_active_repository = home
    visitor_with_demo.profile.save()
    demo = Project.objects.get(owner=visitor_with_demo, slug=SLUG)
    # Act
    moved = land_visitor_on(visitor_with_demo, demo)
    # Assert
    assert moved is True


def test_land_visitor_on_reports_when_nothing_moved(visitor_with_demo):
    # Arrange — already on the demo (a second provisioning pass).
    demo = Project.objects.get(owner=visitor_with_demo, slug=SLUG)
    land_visitor_on(visitor_with_demo, demo)
    # Act
    moved_again = land_visitor_on(visitor_with_demo, demo)
    # Assert
    assert moved_again is False


def test_a_profileless_user_does_not_break_provisioning(visitor_with_demo):
    """Best effort: a missing profile must not abort a slot's provisioning."""
    # Arrange — a stand-in with no profile attribute at all.
    demo = Project.objects.get(owner=visitor_with_demo, slug=SLUG)

    class _NoProfile:
        username = "visitor-902"

    # Act
    moved = land_visitor_on(_NoProfile(), demo)
    # Assert
    assert moved is False


# EOF


# ---------------------------------------------------------------------------
# The SHARED read-only account — the one the first screen actually uses
# ---------------------------------------------------------------------------
# The fix above moved the four pooled visitor-NNN slots and left this account
# behind, which meant it fixed nothing a first-time arrival could see. Measured
# on the PUBLIC dev preview 2026-09-05, AFTER the pooled slots were repaired:
#
#     https://compute-03-net.scitex.ai/  ->  "dotfiles — SciTeX (dev)"
#     body: "Read-Only Mode / 2 of 4 visitor slots available"
#     the bound user was readonly-visitor, not visitor-NNN
#
# Two free slots, and the visitor still got this account: the middleware binds
# readonly-visitor for any request classified as needing no workspace, the
# public landing page included. So this account serves the FIRST SCREEN, and it
# is the one that has to open on the demo.
@pytest.fixture(name="readonly_visitor_with_demo")
def _readonly_visitor_with_demo():
    """The shared account as provisioning leaves it: parked on dotfiles.

    The User post_save signal creates the profile AND the dotfiles home project
    and points the profile at it — so this fixture must NOT create dotfiles
    itself. Doing that is what my first attempt got wrong, and Postgres said so:
    UniqueViolation on (name, owner_id)=(dotfiles, 1).
    """
    User = get_user_model()
    user = User.objects.create_user(username="readonly-visitor", password="x")
    Project.objects.create(
        name=DISPLAY_NAME,
        slug=SLUG,
        owner=user,
        visibility="private",
        data_location=f"{user.username}/{SLUG}",
    )
    return user


@pytest.mark.django_db
def test_the_shared_readonly_account_starts_parked_on_dotfiles(
    readonly_visitor_with_demo,
):
    """Control: the defect must be present before the fix is asserted."""
    # Arrange
    user = readonly_visitor_with_demo
    # Act
    parked = user.profile.last_active_repository
    # Assert
    assert getattr(parked, "slug", None) == "dotfiles"


@pytest.mark.django_db
def test_the_shared_readonly_account_opens_on_the_demo(readonly_visitor_with_demo):
    # Arrange
    user = readonly_visitor_with_demo
    demo = Project.objects.get(owner=user, slug=SLUG)
    # Act
    land_visitor_on(user, demo)
    # Assert
    user.refresh_from_db()
    assert user.profile.last_active_repository_id == demo.pk


@pytest.mark.django_db
def test_moving_the_readonly_account_is_idempotent(readonly_visitor_with_demo):
    """The account long predates the fix, so the move cannot be gated on
    project_created — that is exactly how it was missed the first time."""
    # Arrange
    user = readonly_visitor_with_demo
    demo = Project.objects.get(owner=user, slug=SLUG)
    # Act
    moved_first = land_visitor_on(user, demo)
    moved_again = land_visitor_on(user, demo)
    # Assert
    assert (moved_first, moved_again) == (True, False)
