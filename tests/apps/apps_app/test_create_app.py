#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""+ Create app: private project scaffold, safe "Apply to file", owner-only private run."""

import json
import tempfile
from pathlib import Path

from django.contrib.auth.models import User
from django.test import TestCase, override_settings

from apps.infra.project_app.models import Project
from apps.workspace.apps_app.models import DevInstallation
from apps.workspace.apps_app.services.app_create import (
    app_module_name,
    create_app_project,
)
from apps.workspace.apps_app.services.app_workspace import (
    EditRefused,
    apply_file_edit,
    project_dir_for,
    run_privately,
)


class _DataRootTestCase(TestCase):
    def setUp(self):
        self.data_root = tempfile.TemporaryDirectory()
        self.addCleanup(self.data_root.cleanup)
        override = override_settings(BASE_DIR=self.data_root.name)
        override.enable()
        self.addCleanup(override.disable)
        self.owner = User.objects.create_user("appmaker-owner", password="pw-12345678")
        self.other = User.objects.create_user("appmaker-other", password="pw-12345678")


class CreateAppPageTest(_DataRootTestCase):
    def _create(self):
        self.client.force_login(self.owner)
        self.client.post(
            "/apps/create/",
            {
                "name": "Trial logger",
                "description": "Log trials",
                "starter": "data_entry",
            },
        )
        return Project.objects.get(owner=self.owner, is_app=True)

    def _manifest(self, project):
        path = (
            project_dir_for(project) / app_module_name(project.slug) / "manifest.json"
        )
        return json.loads(path.read_text(encoding="utf-8"))

    def test_create_page_renders_for_signed_in_user(self):
        # Arrange
        self.client.force_login(self.owner)

        # Act
        response = self.client.get("/apps/create/")

        # Assert
        assert response.status_code == 200

    def test_create_makes_a_private_project(self):
        # Arrange
        expected = "private"

        # Act
        project = self._create()

        # Assert
        assert project.visibility == expected

    def test_create_writes_manifest_with_project_scope(self):
        # Arrange
        project = self._create()

        # Act
        manifest = self._manifest(project)

        # Assert
        assert manifest["scope"] == "project"

    def test_create_puts_the_app_in_the_work_group(self):
        # Arrange
        project = self._create()

        # Act
        manifest = self._manifest(project)

        # Assert
        assert manifest["group"] == "work"

    def test_create_redirects_to_the_app_workspace(self):
        # Arrange
        self.client.force_login(self.owner)

        # Act
        response = self.client.post(
            "/apps/create/",
            {"name": "Viewer", "description": "", "starter": "log_viewer"},
        )

        # Assert
        assert response["Location"] == "/apps/create/viewer/"

    def test_workspace_is_not_found_for_another_user(self):
        # Arrange
        project = self._create()
        self.client.force_login(self.other)

        # Act
        response = self.client.get(f"/apps/create/{project.slug}/")

        # Assert
        assert response.status_code == 404


class ApplyToFileTest(_DataRootTestCase):
    def setUp(self):
        super().setUp()
        self.project = create_app_project(self.owner, "Dashboard", "", "dashboard")

    def test_apply_writes_inside_the_project(self):
        # Arrange
        rel = "notes/plan.md"

        # Act
        apply_file_edit(self.owner, self.project, rel, "hello")

        # Assert
        assert (project_dir_for(self.project) / rel).read_text() == "hello"

    def _refusal(self, user, rel):
        try:
            apply_file_edit(user, self.project, rel, "x")
        except EditRefused as exc:
            return exc
        return None

    def test_apply_refuses_a_path_outside_the_project(self):
        # Arrange
        rel = "../../escape.txt"

        # Act
        refusal = self._refusal(self.owner, rel)

        # Assert
        assert isinstance(refusal, EditRefused)

    def test_apply_leaves_no_file_outside_the_project(self):
        # Arrange
        outside = Path(self.data_root.name) / "data" / "users" / "outside.txt"

        # Act
        self._refusal(self.owner, "../../outside.txt")

        # Assert
        assert not outside.exists()

    def test_apply_refuses_the_git_directory(self):
        # Arrange
        rel = ".git/config"

        # Act
        refusal = self._refusal(self.owner, rel)

        # Assert
        assert isinstance(refusal, EditRefused)

    def test_apply_refuses_a_non_owner(self):
        # Arrange
        rel = "notes/plan.md"

        # Act
        refusal = self._refusal(self.other, rel)

        # Assert
        assert isinstance(refusal, EditRefused)

    def test_apply_api_is_not_found_for_a_non_owner(self):
        # Arrange
        self.client.force_login(self.other)

        # Act
        response = self.client.post(
            f"/apps/create/{self.project.slug}/api/apply/",
            data=json.dumps({"path": "a.txt", "content": "x"}),
            content_type="application/json",
        )

        # Assert
        assert response.status_code == 404


class RunPrivatelyTest(_DataRootTestCase):
    def setUp(self):
        super().setUp()
        self.project = create_app_project(self.owner, "Form", "", "data_entry")

    def test_run_creates_a_dev_installation_for_the_owner(self):
        # Arrange
        self.client.force_login(self.owner)

        # Act
        self.client.post(f"/apps/create/{self.project.slug}/api/run/")

        # Assert
        assert DevInstallation.objects.filter(
            user=self.owner, source_repo=self.project.slug
        ).exists()

    def test_run_installs_for_nobody_else(self):
        # Arrange
        self.client.force_login(self.owner)

        # Act
        self.client.post(f"/apps/create/{self.project.slug}/api/run/")

        # Assert
        assert not DevInstallation.objects.exclude(user=self.owner).exists()

    def test_run_by_a_non_owner_is_refused(self):
        # Arrange
        refusal = None

        # Act
        try:
            run_privately(self.other, self.project)
        except PermissionError as exc:
            refusal = exc

        # Assert
        assert isinstance(refusal, PermissionError)

    def test_run_api_for_a_non_owner_creates_nothing(self):
        # Arrange
        self.client.force_login(self.other)

        # Act
        self.client.post(f"/apps/create/{self.project.slug}/api/run/")

        # Assert
        assert not DevInstallation.objects.exists()
