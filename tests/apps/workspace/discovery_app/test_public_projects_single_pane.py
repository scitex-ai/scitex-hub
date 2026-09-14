#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: tests/apps/workspace/discovery_app/test_public_projects_single_pane.py
"""Public Projects (/apps/discovery/) is one pane in the My Projects tree look.

Live audit 2026-09-14: the page mounted the legacy three-pane shell — a left
chat pane ("Ask anything about Scientific Research"), an unrelated project file
pane, then the listing — and its first tab read "Repositories". Operator: one
pane, the same list/tree look as My Projects, tab "Projects".
"""

from django.contrib.auth.models import User
from django.test import TestCase

from apps.infra.project_app.models import Project

PASSWORD = "TestPass123!"  # pragma: allowlist secret


class PublicProjectsSinglePaneTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.me = User.objects.create_user(username="disc-me", password=PASSWORD)
        cls.other = User.objects.create_user(username="disc-other", password=PASSWORD)
        Project.objects.create(
            slug="disc-public-study",
            owner=cls.other,
            name="disc-public-study",
            visibility="public",
        )

    def setUp(self):
        self.client.login(username="disc-me", password=PASSWORD)

    def test_public_projects_has_no_side_chat_pane(self):
        """The visible chat + file panes came from the legacy three-pane shell.

        (Every workspace page also carries a HIDDEN chat pane, #pane-chat, for
        the sidebar's Chat button; that one is not what the audit saw.)
        """
        # Arrange
        url = "/apps/discovery/"
        # Act
        response = self.client.get(url)
        # Assert
        assert b'id="workspace-shell"' not in response.content

    def test_public_projects_first_tab_reads_projects(self):
        # Arrange
        url = "/apps/discovery/"
        tab = b'<i class="fas fa-folder"></i> Projects'
        # Act
        response = self.client.get(url)
        # Assert
        assert tab in response.content

    def test_users_tab_counts_projects_not_repos(self):
        """Operator 2026-09-14: researchers say Project, not Repository."""
        # Arrange
        url = "/apps/discovery/api/explore/?tab=users"
        # Act
        response = self.client.get(url)
        # Assert
        assert " repos</span>" not in response.json()["html"]

    def test_public_projects_are_listed_as_tree_rows(self):
        # Arrange
        url = "/apps/discovery/"
        row = b'data-project-row="disc-other/disc-public-study"'
        # Act
        response = self.client.get(url)
        # Assert
        assert row in response.content


class PublicProjectsSignedOutTest(TestCase):
    """Site audit 2026-09-14 (D11): signed-out "Public Projects" went to /landing/."""

    @classmethod
    def setUpTestData(cls):
        cls.other = User.objects.create_user(username="disc-anon-owner", password=PASSWORD)
        Project.objects.create(
            slug="disc-anon-study",
            owner=cls.other,
            name="disc-anon-study",
            visibility="public",
        )

    def test_signed_out_public_projects_is_not_redirected(self):
        # Arrange
        url = "/apps/discovery/"
        # Act
        response = self.client.get(url)
        # Assert
        assert response.status_code == 200

    def test_signed_out_public_projects_lists_public_projects(self):
        # Arrange
        url = "/apps/discovery/"
        row = b'data-project-row="disc-anon-owner/disc-anon-study"'
        # Act
        response = self.client.get(url)
        # Assert
        assert row in response.content

    def test_signed_out_public_projects_offers_no_sign_in_only_tabs(self):
        # Arrange
        url = "/apps/discovery/"
        # Act
        response = self.client.get(url)
        # Assert
        assert b'data-discovery-tab="users"' not in response.content


# EOF
