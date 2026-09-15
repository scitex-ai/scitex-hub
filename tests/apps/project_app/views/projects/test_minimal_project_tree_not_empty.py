#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""A project created from /new/ with SciTeX Minimal has a visible file tree.

The Minimal clone writes only ``.scitex/writer`` and ``.scitex/scholar``, and
the tree hid every dot-entry, so without Gitea's auto-init README the tree API
answered ``[]`` while the form promised writer + scholar folders.
"""

import tempfile

from django.contrib.auth.models import User
from django.test import TestCase, override_settings

from apps.infra.project_app.models import Project
from apps.infra.project_app.views.projects.create_helpers import (
    _dotted_workspace_tree,
)


class MinimalProjectTreeTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.data_root = tempfile.TemporaryDirectory()
        cls.override = override_settings(BASE_DIR=cls.data_root.name)
        cls.override.enable()

    @classmethod
    def tearDownClass(cls):
        cls.override.disable()
        cls.data_root.cleanup()
        super().tearDownClass()

    def setUp(self):
        self.user = User.objects.create_user("tree-owner", password="pw-12345678")
        self.client.force_login(self.user)
        self.client.post(
            "/new/",
            {
                "name": "minimal-tree",
                "init_type": "template",
                "project_type": "local",
                "template_type": "minimal",
                "init_scitex": "true",
            },
        )
        self.project = Project.objects.get(owner=self.user, name="minimal-tree")

    def _tree_names(self):
        url = f"/{self.user.username}/{self.project.slug}/api/file-tree/"
        return [item["name"] for item in self.client.get(url).json()["tree"]]

    def test_tree_is_not_empty_after_creation(self):
        # Arrange
        minimum = 1

        # Act
        names = self._tree_names()

        # Assert
        assert len(names) >= minimum

    def test_tree_shows_scitex_workspace_root(self):
        # Arrange
        expected = ".scitex"

        # Act
        names = self._tree_names()

        # Assert
        assert expected in names

    def test_tree_shows_readme(self):
        # Arrange
        expected = "README.md"

        # Act
        names = self._tree_names()

        # Assert
        assert expected in names


def test_preview_tree_names_the_dotted_workspace_root():
    # Arrange
    tree = ".\n└── scitex\n    ├── scholar\n    └── writer"

    # Act
    result = _dotted_workspace_tree(tree)

    # Assert
    assert result == ".\n└── .scitex\n    ├── scholar\n    └── writer"
