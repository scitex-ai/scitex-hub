#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: tests/apps/infra/workspace_api/test_file_content_missing_project_dir.py
"""A project whose directory is missing answers 404 JSON, never a 500.

Site audit 2026-09-14 (D11): the only public project on dev,
test-user/Default Project, is a DB row with no working copy on disk. The
project path resolver returns None for it, and ``None / file_path`` in
api_get_file_content raised TypeError -> HTTP 500 for every file the viewer
asked for (e.g. README.md).

No mocks (project rule). One assertion per test.
"""

import json
import shutil
from pathlib import Path

from django.conf import settings
from django.contrib.auth.models import AnonymousUser, User
from django.test import RequestFactory, TestCase

from apps.infra.project_app.models import Project
from apps.infra.workspace_api.views.file_content import api_get_file_content

USERNAME = "fcm-owner"
SLUG = "fcm-no-directory"


def _project_dir() -> Path:
    return Path(settings.BASE_DIR) / "data" / "users" / USERNAME / "proj" / SLUG


class FileContentMissingProjectDirTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = User.objects.create_user(username=USERNAME)
        cls.project = Project.objects.create(
            owner=cls.owner, name="No directory", slug=SLUG, visibility="public"
        )

    def setUp(self):
        # The row exists; its directory must not (a signal may have made one).
        shutil.rmtree(_project_dir(), ignore_errors=True)
        self.rf = RequestFactory()

    def _read(self, file_path="README.md"):
        request = self.rf.get(
            f"/api/workspace/file-content/{file_path}",
            {"project_id": str(self.project.id)},
        )
        request.user = AnonymousUser()
        return api_get_file_content(request, file_path=file_path)

    def test_missing_project_directory_returns_404(self):
        # Arrange
        file_path = "README.md"
        # Act
        response = self._read(file_path)
        # Assert
        assert response.status_code == 404

    def test_missing_project_directory_returns_json_error(self):
        # Arrange
        file_path = "README.md"
        # Act
        response = self._read(file_path)
        # Assert
        assert json.loads(response.content)["error"] == "Project directory not found"


if __name__ == "__main__":
    import os

    import pytest

    pytest.main([os.path.abspath(__file__), "-v"])
