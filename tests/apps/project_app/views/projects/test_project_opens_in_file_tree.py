#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: tests/apps/project_app/views/projects/test_project_opens_in_file_tree.py
"""Opening a project lands on the Explorer/Finder-style file tree.

Operator, 2026-09-14 (UX TODO 186/188-192): researchers know a file tree, not
a GitHub-style repository screen. My Projects and Public Projects open the SAME
Project UI, the file tree is its centre, and the repository screen is retired
gradually — so it must stay reachable, just not be the default.

The page served at /<owner>/<slug>/ already carries the workspace editor pane
(file tree + viewer) bound to the project. What decides the default is which
pane is server-rendered active, so that is what these tests read.
"""

from django.contrib.auth.models import User
from django.test import TestCase

from apps.infra.project_app.models import Project

EDITOR_PANE_ACTIVE = b'class="workspace-pane active" id="pane-editor"'


class ProjectOpensInFileTreeTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.me = User.objects.create_user(
            username="tree-me",
            password="TestPass123!",  # pragma: allowlist secret
        )
        cls.other = User.objects.create_user(
            username="tree-other",
            password="TestPass123!",  # pragma: allowlist secret
        )
        cls.own_project = Project.objects.create(
            slug="tree-own-study", owner=cls.me, name="tree-own-study", visibility="private"
        )
        cls.public_project = Project.objects.create(
            slug="tree-public-study", owner=cls.other, name="tree-public-study", visibility="public"
        )

    def setUp(self):
        self.client.login(
            username="tree-me",
            password="TestPass123!",  # pragma: allowlist secret
        )

    def test_my_project_opens_on_the_file_tree_pane(self):
        # Arrange
        url = "/tree-me/tree-own-study/"
        # Act
        response = self.client.get(url)
        # Assert
        assert EDITOR_PANE_ACTIVE in response.content

    def test_public_project_opens_on_the_same_file_tree_pane(self):
        # Arrange
        url = "/tree-other/tree-public-study/"
        # Act
        response = self.client.get(url)
        # Assert
        assert EDITOR_PANE_ACTIVE in response.content

    def test_file_tree_links_to_the_repository_view(self):
        # Arrange
        url = "/tree-me/tree-own-study/"
        link = b'href="/tree-me/tree-own-study/?view=repository"'
        # Act
        response = self.client.get(url)
        # Assert
        assert link in response.content

    def test_public_projects_listing_links_straight_to_the_project(self):
        """The hub's Public Projects list used href="#" — a dead link."""
        # Arrange
        url = "/apps/my-projects/api/explore/?tab=repositories"
        link = 'href="/tree-other/tree-public-study/"'
        # Act
        response = self.client.get(url)
        # Assert
        assert link in response.json().get("html", "")


# EOF
