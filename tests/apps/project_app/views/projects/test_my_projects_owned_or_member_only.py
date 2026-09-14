#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: tests/apps/project_app/views/projects/test_my_projects_owned_or_member_only.py
"""My Projects lists projects the viewer owns or is a member of — nothing else.

Site audit 2026-09-14 (D11): opening someone else's public project put it into
the visitor's own "My Projects" tree (the open project was inserted into the
nav rows). Reading a public project does not make it yours: the worktree pane
reads "Public Projects" for it instead, and My Projects keeps its meaning.

One assertion per test; no mocks.
"""

from django.contrib.auth.models import User
from django.test import TestCase

from apps.infra.project_app.models import Project, ProjectMembership

PASSWORD = "TestPass123!"  # pragma: allowlist secret


class MyProjectsOwnedOrMemberOnlyTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.me = User.objects.create_user(username="mpo-me", password=PASSWORD)
        cls.other = User.objects.create_user(username="mpo-other", password=PASSWORD)
        cls.own = Project.objects.create(
            slug="mpo-own", owner=cls.me, name="mpo-own", visibility="private"
        )
        cls.others_public = Project.objects.create(
            slug="mpo-public", owner=cls.other, name="mpo-public", visibility="public"
        )
        cls.shared_with_me = Project.objects.create(
            slug="mpo-shared", owner=cls.other, name="mpo-shared", visibility="private"
        )
        ProjectMembership.objects.create(
            project=cls.shared_with_me, user=cls.me, permission_level="read"
        )

    def setUp(self):
        self.client.login(username="mpo-me", password=PASSWORD)

    def test_opening_others_public_project_keeps_it_out_of_my_projects(self):
        # Arrange
        url = "/mpo-other/mpo-public/"
        # Act
        response = self.client.get(url)
        # Assert
        assert self.others_public not in response.context["project_nav_projects"]

    def test_others_public_project_pane_reads_public_projects(self):
        # Arrange
        url = "/mpo-other/mpo-public/"
        # Act
        response = self.client.get(url)
        # Assert
        assert response.context["project_tree_public_read"] is True

    def test_my_projects_still_lists_a_project_i_am_a_member_of(self):
        # Arrange
        url = "/mpo-me/mpo-own/"
        # Act
        response = self.client.get(url)
        # Assert
        assert self.shared_with_me in response.context["project_nav_projects"]

    def test_own_project_pane_reads_my_projects(self):
        # Arrange
        url = "/mpo-me/mpo-own/"
        # Act
        response = self.client.get(url)
        # Assert
        assert response.context["project_tree_public_read"] is False


if __name__ == "__main__":
    import os

    import pytest

    pytest.main([os.path.abspath(__file__), "-v"])
