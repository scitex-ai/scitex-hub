#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""A project whose workspace is not on disk yet must not 500 the PDF route.

Measured in the visible Private Beta run: with a project whose directory had not
been created on disk (registered, not yet initialized), the page's own PDF fetch

    GET /apps/writer/api/project/245/pdf/?doc_type=manuscript   ->  500
    {"success": false, "error": "Project directory not found for project 245
     (slug: writer-beta-study). Please ensure the project directory exists."}

The 500 came from the same raise the section endpoint used to hit —
`WriterService.writer_dir` raising RuntimeError — falling through the view's
broad `except Exception`. This route already has the right answer for "there is
no PDF to serve": **404**. A workspace that is not on disk yet means exactly
that, so it answers 404 too, and the ordinary paths (real workspace, no PDF;
project that does not exist; anonymous caller) are unchanged and pinned below.
"""

from django.contrib.auth.models import User
from django.test import Client, TestCase

from apps.infra.project_app.models import Project
from apps.infra.project_app.services.project_filesystem import (
    get_project_filesystem_manager,
)

PASSWORD = "TestPass123!"  # pragma: allowlist secret


class PdfRouteWhenWorkspaceIsAbsentTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = User.objects.create_user(username="pdf-owner", password=PASSWORD)
        # Registered, with owner and slug, and NO directory on disk: the state
        # the page's PDF fetch can race.
        cls.unborn = Project.objects.create(
            slug="pdf-unborn", owner=cls.owner, name="pdf-unborn", visibility="private"
        )
        # A project whose workspace DOES exist but has no compiled PDF: the
        # ordinary "nothing compiled yet" case, which must keep answering 404.
        cls.ready = Project.objects.create(
            slug="pdf-ready", owner=cls.owner, name="pdf-ready", visibility="private"
        )
        get_project_filesystem_manager(cls.owner).create_project_directory(
            cls.ready, use_template=False
        )

    def _client(self):
        client = Client()
        client.login(username="pdf-owner", password=PASSWORD)
        return client

    def test_a_project_whose_directory_is_not_on_disk_yet_is_not_a_server_error(self):
        # Arrange
        client = self._client()
        # Act
        response = client.get(f"/apps/writer/api/project/{self.unborn.pk}/pdf/?doc_type=manuscript")
        # Assert
        assert response.status_code < 500, response.content
        assert response.status_code == 404, response.content

    def test_the_named_file_form_answers_404_too(self):
        # Arrange: the preview form the editor also requests.
        client = self._client()
        # Act
        response = client.get(
            f"/apps/writer/api/project/{self.unborn.pk}/pdf/preview-abstract-light.pdf"
        )
        # Assert
        assert response.status_code < 500, response.content
        assert response.status_code == 404, response.content

    def test_a_real_workspace_with_no_pdf_still_answers_404(self):
        # Arrange: the ordinary path, which the fix must not have changed.
        client = self._client()
        # Act
        response = client.get(f"/apps/writer/api/project/{self.ready.pk}/pdf/?doc_type=manuscript")
        # Assert
        assert response.status_code == 404, response.content

    def test_a_project_that_does_not_exist_is_still_404(self):
        # Arrange
        client = self._client()
        # Act
        response = client.get("/apps/writer/api/project/999999999/pdf/?doc_type=manuscript")
        # Assert
        assert response.status_code == 404, response.content

    def test_an_anonymous_caller_is_still_refused(self):
        # Arrange: the fix is confined to the workspace branch.
        # Act
        response = Client().get(f"/apps/writer/api/project/{self.unborn.pk}/pdf/?doc_type=manuscript")
        # Assert
        assert response.status_code == 401, response.content


# EOF
