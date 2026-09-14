#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""New projects start private; /new/ offers an explicit Private/Public choice."""

import re
import tempfile

from django.contrib.auth.models import User
from django.test import TestCase, override_settings

from apps.infra.project_app.models import Project


class ProjectModelDefaultVisibilityTest(TestCase):
    def test_project_created_without_visibility_is_private(self):
        # Arrange
        owner = User.objects.create_user("vis-model-owner", password="pw-12345678")

        # Act
        project = Project.objects.create(
            name="unset-visibility", slug="unset-visibility", owner=owner
        )

        # Assert
        assert project.visibility == "private"


class NewProjectFormVisibilityTest(TestCase):
    def setUp(self):
        self.data_root = tempfile.TemporaryDirectory()
        self.addCleanup(self.data_root.cleanup)
        override = override_settings(BASE_DIR=self.data_root.name)
        override.enable()
        self.addCleanup(override.disable)
        self.user = User.objects.create_user("vis-form-owner", password="pw-12345678")
        self.client.force_login(self.user)

    def _post(self, **extra):
        data = {"name": "vis-project", "init_type": "empty", "project_type": "local"}
        data.update(extra)
        self.client.post("/new/", data)
        return Project.objects.get(owner=self.user, name="vis-project")

    def test_form_renders_private_option_checked(self):
        # Arrange
        pattern = re.compile(r'name="visibility"\s+value="private"\s+checked')

        # Act
        html = self.client.get("/new/").content.decode()

        # Assert
        assert pattern.search(html) is not None

    def test_form_renders_public_option(self):
        # Arrange
        pattern = re.compile(r'name="visibility"\s+value="public"\s+/>')

        # Act
        html = self.client.get("/new/").content.decode()

        # Assert
        assert pattern.search(html) is not None

    def test_post_without_visibility_creates_private_project(self):
        # Arrange
        fields = {}

        # Act
        project = self._post(**fields)

        # Assert
        assert project.visibility == "private"

    def test_post_with_public_creates_public_project(self):
        # Arrange
        fields = {"visibility": "public"}

        # Act
        project = self._post(**fields)

        # Assert
        assert project.visibility == "public"

    def test_post_with_unknown_visibility_falls_back_to_private(self):
        # Arrange
        fields = {"visibility": "internal"}

        # Act
        project = self._post(**fields)

        # Assert
        assert project.visibility == "private"
