#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""A section read against a half-created workspace must not 500.

Measured live in the visible Private Beta run, AFTER the section endpoint had
been fixed for a missing project directory — same class, one level deeper:

    GET /apps/writer/api/project/245/section/abstract/?doc_type=manuscript  ->  500
    {"success": false, "error": "Failed to read section: Failed to initialize
     Writer: Project structure invalid: missing 01_manuscript directory"}

WHY IT HAPPENS, from the leaf's own control flow (`scitex_writer/writer.py`,
`_attach_or_create_project`): when `project_dir` EXISTS it attaches and calls
`_verify_project_structure()`, which raises RuntimeError if a required directory
is missing; it only scaffolds when the directory does NOT exist. So a workspace
that exists in part — a clone that failed, a template without the manuscript
directory, a directory a user emptied — takes the attach path and throws, and the
view's broad handler turned that into a 500. Note the earlier state (no directory
at all) is the easy one: it scaffolds, and the first attempt at this test missed
the defect because it built only the project ROOT, not the writer directory.

Both states now answer the same controlled response: 200, empty content,
`workspace_ready: false` — what the client renders as an empty editor. The
ordinary path (a structurally complete workspace) is pinned unchanged.
"""

import json

from django.contrib.auth.models import User
from django.test import Client, TestCase

from apps.infra.project_app.models import Project
from apps.infra.project_app.services.project_filesystem import (
    get_project_filesystem_manager,
)
from apps.infra.project_app.services.writer_workspace_layout import (
    get_writer_workspace_path,
)

PASSWORD = "TestPass123!"  # pragma: allowlist secret
REQUIRED_DIRS = ("01_manuscript", "02_supplementary", "03_revision")


class SectionReadWhenWorkspaceIsHalfCreatedTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = User.objects.create_user(username="halfw-owner", password=PASSWORD)
        manager = get_project_filesystem_manager(cls.owner)

        # 1. The reported state: the writer workspace EXISTS but its manuscript
        #    directory does not. The leaf attaches instead of scaffolding, then
        #    fails its structure check.
        cls.halfway = Project.objects.create(
            slug="halfway-study", owner=cls.owner, name="halfway-study", visibility="private"
        )
        _, root = manager.create_project_directory(cls.halfway, use_template=False)
        get_writer_workspace_path(root).mkdir(parents=True, exist_ok=True)

        # 2. The ordinary path: a structurally complete workspace.
        cls.complete = Project.objects.create(
            slug="complete-study", owner=cls.owner, name="complete-study", visibility="private"
        )
        _, complete_root = manager.create_project_directory(cls.complete, use_template=False)
        for name in REQUIRED_DIRS:
            (get_writer_workspace_path(complete_root) / name).mkdir(parents=True, exist_ok=True)

    def _url(self, project_id, section="abstract"):
        return f"/apps/writer/api/project/{project_id}/section/{section}/?doc_type=manuscript"

    def _client(self):
        client = Client()
        client.login(username="halfw-owner", password=PASSWORD)
        return client

    def test_a_half_created_workspace_is_not_a_server_error(self):
        # Arrange
        client = self._client()
        # Act
        response = client.get(self._url(self.halfway.pk))
        # Assert
        assert response.status_code < 500, response.content
        assert response.status_code == 200, response.content

    def test_the_response_says_the_workspace_is_not_ready(self):
        # Arrange
        client = self._client()
        # Act
        payload = json.loads(client.get(self._url(self.halfway.pk)).content)
        # Assert
        assert payload["success"] is True, payload
        assert payload["content"] == "", payload
        assert payload["workspace_ready"] is False, payload

    def test_a_complete_workspace_still_serves_content(self):
        # Arrange: the ordinary path, which the fix must not have changed.
        client = self._client()
        # Act
        response = client.get(self._url(self.complete.pk))
        # Assert
        assert response.status_code == 200, response.content
        payload = json.loads(response.content)
        assert payload["success"] is True, payload
        assert payload["workspace_ready"] is True, payload
        assert isinstance(payload["content"], str), payload


# EOF
