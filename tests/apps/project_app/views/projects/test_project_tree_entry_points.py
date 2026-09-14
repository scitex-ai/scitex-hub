#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: tests/apps/project_app/views/projects/test_project_tree_entry_points.py
"""Every project entry point opens the SAME file-tree Project UI.

Operator, 2026-09-14: My Projects and Public Projects open one Explorer/Finder-
style tree, 「いろんなページで同じ見た目のもの」. PR #810 made /<owner>/<slug>/
open the tree; these cover the entry points it left on the GitHub-style screen
(/tree/ and /blob/ deep links, anonymous visitors) and what the tree offers
(write actions only for writers, an empty state, a hint that names the tree).

The tree is rendered client-side, so the tests read the server-rendered mount
attributes that drive it (templates/global_base_partials/workspace_worktree_tree.html).
"""

from django.contrib.auth.models import User
from django.test import TestCase

from apps.infra.project_app.models import Project

PASSWORD = "TestPass123!"  # pragma: allowlist secret


class ProjectTreeEntryPointsTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.me = User.objects.create_user(username="entry-me", password=PASSWORD)
        cls.other = User.objects.create_user(username="entry-other", password=PASSWORD)
        cls.own_project = Project.objects.create(
            slug="entry-own-study", owner=cls.me, name="entry-own-study", visibility="private"
        )
        cls.public_project = Project.objects.create(
            slug="entry-public-study",
            owner=cls.other,
            name="entry-public-study",
            visibility="public",
        )

    def _login(self):
        self.client.login(username="entry-me", password=PASSWORD)

    def test_tree_deep_link_lands_on_the_tree_with_that_folder_focused(self):
        # Arrange
        self._login()
        url = "/entry-me/entry-own-study/tree/develop/scripts/analysis/"
        # Act
        response = self.client.get(url)
        # Assert
        assert b'data-focus-path="scripts/analysis"' in response.content

    def test_blob_deep_link_lands_on_the_tree_with_that_file_open(self):
        # Arrange
        self._login()
        url = "/entry-me/entry-own-study/blob/scripts/run.py"
        # Act
        response = self.client.get(url)
        # Assert
        assert b'data-open-file="scripts/run.py"' in response.content

    def test_non_owner_gets_a_read_only_tree_on_a_public_project(self):
        # Arrange
        self._login()
        url = "/entry-other/entry-public-study/"
        # Act
        response = self.client.get(url)
        # Assert
        assert b'data-read-only="true"' in response.content

    def test_owner_gets_a_writable_tree_on_their_own_project(self):
        # Arrange
        self._login()
        url = "/entry-me/entry-own-study/"
        # Act
        response = self.client.get(url)
        # Assert
        assert b'data-read-only="false"' in response.content

    def test_empty_project_shows_the_no_files_yet_empty_state(self):
        # Arrange
        self._login()
        url = "/entry-me/entry-own-study/"
        # Act
        response = self.client.get(url)
        # Assert
        assert b"No files yet" in response.content

    def test_empty_state_offers_upload_to_a_viewer_who_can_write(self):
        # Arrange
        self._login()
        url = "/entry-me/entry-own-study/"
        # Act
        response = self.client.get(url)
        # Assert
        assert b'data-tree-empty-action="upload"' in response.content

    def test_viewer_hint_names_the_tree_not_a_files_tab(self):
        # Arrange
        self._login()
        url = "/entry-me/entry-own-study/"
        # Act
        response = self.client.get(url)
        # Assert
        assert b"Select a file in the tree" in response.content

    def test_anonymous_visitor_gets_the_tree_on_a_public_project(self):
        # Arrange
        url = "/entry-other/entry-public-study/"
        # Act
        response = self.client.get(url)
        # Assert
        assert b"data-project-tree-public" in response.content

    def test_anonymous_visitors_tree_is_read_only(self):
        # Arrange
        url = "/entry-other/entry-public-study/"
        # Act
        response = self.client.get(url)
        # Assert
        assert b'data-read-only="true"' in response.content


# EOF
