#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The project "Add file" menu: new-file/ and upload/ pages.

Regression: both links fell through to the directory catch-all, which answered
"Directory 'upload' not found".
"""

from __future__ import annotations

import shutil
import uuid
from pathlib import Path

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import RequestFactory
from django.urls import resolve

from apps.infra.project_app.views.repository.add_file import (
    project_new_file,
    project_upload_files,
)


class TestAddFileRoutes:
    def test_upload_path_is_not_read_as_a_directory(self):
        # Arrange
        url = "/alice/my-project/upload/"
        # Act
        match = resolve(url)
        # Assert
        assert match.func is project_upload_files

    def test_new_file_path_is_not_read_as_a_directory(self):
        # Arrange
        url = "/alice/my-project/new-file/"
        # Act
        match = resolve(url)
        # Assert
        assert match.func is project_new_file


@pytest.fixture
def owned_project(db):
    from django.conf import settings
    from django.contrib.auth.models import User

    from apps.infra.project_app.models import Project

    suffix = uuid.uuid4().hex[:8]
    user = User.objects.create_user(username=f"addfile_{suffix}", password="x")
    project = Project.objects.create(slug=f"p-{suffix}", owner=user, name="P")
    user_root = Path(settings.BASE_DIR) / "data" / "users" / user.username
    project_dir = user_root / "proj" / project.slug
    project_dir.mkdir(parents=True, exist_ok=True)
    try:
        yield user, project, project_dir
    finally:
        shutil.rmtree(user_root, ignore_errors=True)


def _post(view, user, project, data):
    request = RequestFactory().post(f"/{user.username}/{project.slug}/x/", data=data)
    request.user = user
    return view(request, user.username, project.slug)


@pytest.mark.django_db
class TestAddFileViews:
    def test_new_file_writes_the_file_into_the_project(self, owned_project):
        # Arrange
        user, project, project_dir = owned_project
        data = {"directory": "notes", "file_name": "idea.md", "content": "# Idea"}
        # Act
        _post(project_new_file, user, project, data)
        # Assert
        assert (project_dir / "notes" / "idea.md").read_text() == "# Idea"

    def test_upload_writes_every_file_into_the_project(self, owned_project):
        # Arrange
        user, project, project_dir = owned_project
        files = [
            SimpleUploadedFile("a.csv", b"x,y\n1,2\n"),
            SimpleUploadedFile("b.csv", b"x,y\n3,4\n"),
        ]
        data = {"directory": "data", "files": files}
        # Act
        _post(project_upload_files, user, project, data)
        # Assert
        assert sorted(p.name for p in (project_dir / "data").iterdir()) == [
            "a.csv",
            "b.csv",
        ]

    def test_upload_refuses_a_path_outside_the_project(self, owned_project):
        # Arrange
        user, project, project_dir = owned_project
        data = {"directory": "../../escape", "files": [SimpleUploadedFile("a", b"1")]}
        # Act
        response = _post(project_upload_files, user, project, data)
        # Assert
        assert response.status_code == 400


if __name__ == "__main__":
    import os

    pytest.main([os.path.abspath(__file__), "-v"])
