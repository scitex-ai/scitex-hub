#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Behavioural tests for the writer access guard `user_can_access_project`.

WHY THIS FILE EXISTS, and why it is not redundant with
tests/security/test_comms_writer_idor.py:

That suite asserts on SOURCE TEXT --
    assert "user_can_access_project" in code
-- so it passes whenever the guard's NAME appears in the view. It cannot
tell whether the guard works. It stayed green for days while the guard
called ``project.team_members``, an attribute that has never existed on
Project, so every authenticated non-owner raised AttributeError, got
swallowed by a blanket ``except Exception``, and was answered
``200 {"success": true}`` with the static section hierarchy.

Grep-for-the-guard-name is a real technique (it catches a guard deleted
from a view) but it is a STRUCTURAL check, and it reads as coverage while
proving nothing about behaviour. These tests CALL the guard.

Real Django test DB, real ProjectMembership rows. No mocks: a mocked
Project would have had whatever attribute the mock was told to have,
which is precisely the bug this file exists to catch.
"""

import pytest
from django.contrib.auth.models import AnonymousUser, User
from django.test import RequestFactory, TestCase

from apps.infra.project_app.models import Project, ProjectMembership
from apps.workspace.writer_app.views.editor.auth_utils import (
    user_can_access_project,
)


def _request(rf, user):
    request = rf.get("/apps/writer/editor-v2/")
    request.user = user
    request.session = {}
    return request


class WriterProjectAccessGuardTest(TestCase):
    """owner / collaborator / outsider, evaluated by calling the guard."""

    @classmethod
    def setUpTestData(cls):
        cls.owner = User.objects.create_user(username="owner-u")
        cls.collaborator = User.objects.create_user(username="collab-u")
        cls.outsider = User.objects.create_user(username="outsider-u")
        cls.project = Project.objects.create(
            owner=cls.owner, name="Paper", slug="paper"
        )
        # The real relation: Project.collaborators is an M2M THROUGH this.
        ProjectMembership.objects.create(
            project=cls.project,
            user=cls.collaborator,
            role="collaborator",
            permission_level="write",
        )

    def setUp(self):
        self.rf = RequestFactory()

    def test_owner_is_allowed(self):
        # Arrange
        request = _request(self.rf, self.owner)
        # Act
        got = user_can_access_project(request, self.project)
        # Assert
        assert got is True

    def test_collaborator_is_allowed(self):
        # Arrange — THE regression. On the broken code this raised
        # AttributeError('Project' object has no attribute 'team_members')
        # rather than returning False, so it did not merely deny the
        # collaborator: it made the guard unable to answer at all.
        request = _request(self.rf, self.collaborator)
        # Act
        got = user_can_access_project(request, self.project)
        # Assert
        assert got is True

    def test_outsider_is_denied(self):
        # Arrange
        request = _request(self.rf, self.outsider)
        # Act
        got = user_can_access_project(request, self.project)
        # Assert
        assert got is False

    def test_guard_returns_a_bool_and_never_raises_for_a_non_owner(self):
        # Arrange — the guard's docstring promises "a plain bool so the
        # caller can emit its own JSON error (fail closed, never mask)".
        # A raise breaks that contract, and whether it then fails open or
        # closed depends entirely on the CALLER's except handling — which
        # is how this became a 200 instead of a 403.
        request = _request(self.rf, self.outsider)
        # Act
        got = user_can_access_project(request, self.project)
        # Assert
        assert isinstance(got, bool)

    def test_anonymous_without_visitor_session_is_denied(self):
        # Arrange
        request = _request(self.rf, AnonymousUser())
        # Act
        got = user_can_access_project(request, self.project)
        # Assert
        assert got is False


class WriterAccessGuardUsesRealRelationTest(TestCase):
    """The model must actually expose what the guard reaches for."""

    def test_project_has_no_team_members_attribute(self):
        # Arrange — pins the root cause so a future edit cannot quietly
        # reintroduce `project.team_members` believing it exists.
        project = Project.objects.create(
            owner=User.objects.create_user(username="pin-u"),
            name="Pin",
            slug="pin",
        )
        # Act
        has_team_members = hasattr(project, "team_members")
        # Assert
        assert has_team_members is False

    def test_project_exposes_collaborators(self):
        # Arrange
        project = Project.objects.create(
            owner=User.objects.create_user(username="pin2-u"),
            name="Pin2",
            slug="pin2",
        )
        # Act
        has_collaborators = hasattr(project, "collaborators")
        # Assert
        assert has_collaborators is True


if __name__ == "__main__":
    import os

    pytest.main([os.path.abspath(__file__)])

# EOF
