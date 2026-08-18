#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Switching the active project must move BOTH stores, and one resolver must win.

"Which project am I in" was stored in two places — ``profile.last_active_repository``
(written by the header selector) and the session key ``current_project_slug`` —
and the switch endpoint wrote only the first. Readers that consulted the session
first therefore kept answering with the PREVIOUS project after a switch. Scholar's
search page was such a reader, with its own inverted copy of the resolution rules,
so BibTeX silently saved to the old project.

These tests pin the two properties that make that class of bug impossible:

  1. a switch writes both stores, so they cannot disagree;
  2. ``get_current_project`` prefers the explicit header choice over the session
     slug, so a stale session can never outrank a deliberate selection.
"""

import pytest
from django.contrib.auth import get_user_model

from apps.infra.project_app.models import Project
from apps.infra.project_app.services.project_utils import get_current_project

User = get_user_model()

SWITCH_URL = "/api/project/switch/"


@pytest.fixture
def owner(db):
    """A user who owns two projects."""
    # Arrange
    return User.objects.create_user(
        username="switcher", email="switcher@example.com", password="x"
    )


@pytest.fixture
def project_a(db, owner):
    """The project the user starts on."""
    # Arrange
    return Project.objects.create(name="Alpha", slug="alpha", owner=owner)


@pytest.fixture
def project_b(db, owner):
    """The project the user switches to."""
    # Arrange
    return Project.objects.create(name="Beta", slug="beta", owner=owner)


class TestSwitchWritesBothStores:
    """The endpoint must not leave the two stores disagreeing."""

    def test_switch_updates_the_profile(self, client, owner, project_a, project_b):
        # Arrange
        client.force_login(owner)
        # Act
        client.post(
            SWITCH_URL,
            data={"project_id": project_b.pk},
            content_type="application/json",
        )
        # Assert
        owner.profile.refresh_from_db()
        assert owner.profile.last_active_repository_id == project_b.pk

    def test_switch_updates_the_session_slug(
        self, client, owner, project_a, project_b
    ):
        """The half that was missing: a stale slug is what made readers disagree."""
        # Arrange
        client.force_login(owner)
        session = client.session
        session["current_project_slug"] = project_a.slug
        session.save()
        # Act
        client.post(
            SWITCH_URL,
            data={"project_id": project_b.pk},
            content_type="application/json",
        )
        # Assert
        assert client.session["current_project_slug"] == "beta"


class TestResolverPriority:
    """One resolver, and the explicit choice outranks the session."""

    def test_profile_choice_beats_a_stale_session_slug(
        self, rf, owner, project_a, project_b
    ):
        # Arrange
        request = rf.get("/")
        request.user = owner
        request.session = {"current_project_slug": project_a.slug}
        owner.profile.last_active_repository = project_b
        owner.profile.save()
        # Act
        resolved = get_current_project(request, user=owner)
        # Assert
        assert resolved.pk == project_b.pk

    def test_session_slug_is_used_when_the_profile_has_no_choice(
        self, rf, owner, project_a, project_b
    ):
        # Arrange
        request = rf.get("/")
        request.user = owner
        request.session = {"current_project_slug": project_a.slug}
        owner.profile.last_active_repository = None
        owner.profile.save()
        # Act
        resolved = get_current_project(request, user=owner)
        # Assert
        assert resolved.pk == project_a.pk


# EOF
