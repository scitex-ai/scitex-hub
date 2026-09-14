#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: tests/apps/project_app/views/projects/test_tree_link_to_a_file_opens_it.py
"""/tree/<branch>/<file> opens that file, like GitHub does.

Site audit 2026-09-14 (D12): /tree/main/AGENTS.md rendered the tree with
data-focus-path="AGENTS.md" (a folder focus on a file), so the viewer said
"No file selected". A /tree/ path that is a file in the project now opens it.

One assertion per test; no mocks. The file is written to the project's real
directory and removed afterwards.
"""

import shutil
from pathlib import Path

from django.conf import settings
from django.contrib.auth.models import User
from django.test import TestCase

from apps.infra.project_app.models import Project

PASSWORD = "TestPass123!"  # pragma: allowlist secret
USERNAME = "tlf-me"
SLUG = "tlf-study"


class TreeLinkToAFileOpensItTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.me = User.objects.create_user(username=USERNAME, password=PASSWORD)
        cls.project = Project.objects.create(
            slug=SLUG, owner=cls.me, name=SLUG, visibility="private"
        )

    def setUp(self):
        root = Path(settings.BASE_DIR) / "data" / "users" / USERNAME / "proj" / SLUG
        (root / "docs").mkdir(parents=True, exist_ok=True)
        (root / "AGENTS.md").write_text("# agents\n")
        self.addCleanup(shutil.rmtree, root, ignore_errors=True)
        self.client.login(username=USERNAME, password=PASSWORD)

    def test_tree_link_to_a_file_opens_the_file(self):
        # Arrange
        url = f"/{USERNAME}/{SLUG}/tree/main/AGENTS.md"
        # Act
        response = self.client.get(url)
        # Assert
        assert b'data-open-file="AGENTS.md"' in response.content

    def test_tree_link_to_a_folder_still_focuses_the_folder(self):
        # Arrange
        url = f"/{USERNAME}/{SLUG}/tree/main/docs"
        # Act
        response = self.client.get(url)
        # Assert
        assert b'data-focus-path="docs"' in response.content


if __name__ == "__main__":
    import os

    import pytest

    pytest.main([os.path.abspath(__file__), "-v"])
