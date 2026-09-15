#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: tests/apps/workspace/my_projects_app/test_my_projects_opens_file_tree.py
"""The My Projects tile (/apps/my-projects/) lands on the file-tree Project UI.

Live audit 2026-09-14: /apps/my-projects/ still server-rendered the GitHub-style
repository page — 227 KB, the full branch list (213 branches for one project),
Watch/Star/Fork, a clone panel. Operator: My Projects must be the same
Explorer/Finder tree as everywhere else. The GitHub-style screen stays at
?view=repository.
"""

from django.contrib.auth.models import User
from django.test import TestCase

from apps.infra.project_app.models import Project

PASSWORD = "TestPass123!"  # pragma: allowlist secret
EDITOR_PANE_ACTIVE = b'class="workspace-pane active" id="pane-editor"'


class MyProjectsOpensFileTreeTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.me = User.objects.create_user(username="home-me", password=PASSWORD)
        cls.project = Project.objects.create(
            slug="home-study", owner=cls.me, name="home-study", visibility="private"
        )
        cls.me.profile.last_active_repository = cls.project
        cls.me.profile.save(update_fields=["last_active_repository"])

    def setUp(self):
        self.client.login(username="home-me", password=PASSWORD)

    def test_my_projects_opens_on_the_file_tree_pane(self):
        # Arrange
        url = "/apps/my-projects/"
        # Act
        response = self.client.get(url)
        # Assert
        assert EDITOR_PANE_ACTIVE in response.content

    def test_my_projects_lists_the_users_projects_as_tree_rows(self):
        # Arrange
        url = "/apps/my-projects/"
        row = b'data-project-row="home-me/home-study"'
        # Act
        response = self.client.get(url)
        # Assert
        assert row in response.content

    def test_my_projects_does_not_render_watch_star_fork(self):
        # Arrange
        url = "/apps/my-projects/"
        # Act
        response = self.client.get(url)
        # Assert
        assert b'id="watch-btn"' not in response.content

    def test_my_projects_has_no_my_settings_tab_row(self):
        """Operator 2026-09-14: drop "My | Settings | <project>" entirely."""
        # Arrange
        url = "/apps/my-projects/"
        # Act
        response = self.client.get(url)
        # Assert
        assert b'id="hub-mode-switcher"' not in response.content

    def test_repository_view_of_my_projects_has_no_tab_row_either(self):
        # Arrange
        url = "/apps/my-projects/?view=repository"
        # Act
        response = self.client.get(url)
        # Assert
        assert b'id="hub-mode-switcher"' not in response.content

    def test_account_settings_link_the_profile_the_my_tab_showed(self):
        # Arrange
        url = "/accounts/settings/profile/"
        # Act
        response = self.client.get(url)
        # Assert
        assert b'data-settings-nav="public-profile"' in response.content

    def test_in_page_my_projects_lists_projects_in_the_tree_look(self):
        """The sidebar loads My Projects in-page; it injected the repo screen."""
        # Arrange
        url = "/apps/workspace/content/home/"
        row = b'data-project-row="home-me/home-study"'
        # Act
        response = self.client.get(url, HTTP_X_WORKSPACE_SHELL="1")
        # Assert
        assert row in response.content

    def test_my_projects_does_not_build_the_branch_list(self):
        # Arrange
        url = "/apps/my-projects/"
        # Act
        response = self.client.get(url)
        # Assert
        assert "branches" not in response.context


# EOF
