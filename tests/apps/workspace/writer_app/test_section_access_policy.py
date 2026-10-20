#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The section endpoints must apply the Hub's canonical project access policy.

Policy, taken from the Hub's own model methods rather than invented here:

- read  : ``Project.can_view``  — owner, or a collaborator on a private project
          (the gate these views already have, via ``api_login_optional``);
- write : ``Project.can_edit``  — owner, or a membership whose
          ``permission_level`` is ``write``/``admin``. A collaborator with
          ``read`` permission may NOT write;
- denial: the app's canonical denial for an authenticated caller without access
          (403, "You don't have access to this project"), and 404 for a project
          id that does not exist;
- anonymous: 401, unchanged.

The distinction between the two halves is the point of this file: the views'
existing gate is *read*-shaped, so a read-only collaborator currently passes it,
while ``Project.can_edit`` is the Hub's answer to what a write requires.
"""

import json
import shutil

from django.contrib.auth.models import User
from django.test import Client, TestCase

from apps.infra.project_app.models import Project, ProjectMembership
from apps.infra.project_app.services.project_filesystem import (
    get_project_filesystem_manager,
)

PASSWORD = "TestPass123!"  # pragma: allowlist secret
STRANGERS_CONTENT = "WRITTEN BY AN UNAUTHORIZED CALLER"


class SectionAccessPolicyTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = User.objects.create_user(username="policy-owner", password=PASSWORD)
        cls.stranger = User.objects.create_user(username="policy-stranger", password=PASSWORD)
        cls.reader = User.objects.create_user(username="policy-reader", password=PASSWORD)
        cls.writer = User.objects.create_user(username="policy-writer", password=PASSWORD)

        cls.project = Project.objects.create(
            slug="policy-study",
            owner=cls.owner,
            name="policy-study",
            visibility="private",
        )
        manager = get_project_filesystem_manager(cls.owner)
        created, cls.root = manager.create_project_directory(cls.project, use_template=False)
        cls.base = manager.base_path
        for leftover in cls.root.rglob("*.tex"):
            leftover.unlink()

        # A second, unrelated private project — the cross-project target.
        cls.other_project = Project.objects.create(
            slug="policy-other",
            owner=cls.stranger,
            name="policy-other",
            visibility="private",
        )
        manager2 = get_project_filesystem_manager(cls.stranger)
        manager2.create_project_directory(cls.other_project, use_template=False)
        cls.other_base = manager2.base_path

        # Collaborators: one may only read, one may write.
        ProjectMembership.objects.create(
            project=cls.project, user=cls.reader, role="collaborator",
            permission_level="read",
        )
        ProjectMembership.objects.create(
            project=cls.project, user=cls.writer, role="collaborator",
            permission_level="write",
        )

        cls.addClassCleanup(shutil.rmtree, str(cls.base / cls.project.slug), True)
        cls.addClassCleanup(shutil.rmtree, str(cls.other_base / cls.other_project.slug), True)

    def _url(self, project_id, section="abstract"):
        return f"/apps/writer/api/project/{project_id}/section/{section}/?doc_type=manuscript"

    def _login(self, username):
        client = Client()
        client.login(username=username, password=PASSWORD)
        return client

    def _post(self, client, project_id, content, section="abstract"):
        return client.post(
            self._url(project_id, section),
            data=json.dumps({"content": content, "doc_type": "manuscript"}),
            content_type="application/json",
        )

    # --- a stranger must not get in at all ---------------------------------

    def test_a_stranger_cannot_read_a_private_projects_section(self):
        # Arrange
        client = self._login("policy-stranger")
        # Act
        response = client.get(self._url(self.project.pk))
        # Assert
        assert response.status_code < 500, response.content
        assert response.status_code in (403, 404), response.content

    def test_a_stranger_cannot_write_to_a_private_projects_section(self):
        # Arrange
        client = self._login("policy-stranger")
        # Act
        response = self._post(client, self.project.pk, STRANGERS_CONTENT)
        # Assert
        assert response.status_code < 500, response.content
        assert response.status_code in (403, 404), response.content

    def test_a_stranger_cannot_reach_another_projects_content(self):
        # Arrange: the stranger owns a project of their own, so a mistake in
        # resolving "the caller's project" would show up as the wrong file.
        client = self._login("policy-stranger")
        # Act
        response = client.get(self._url(self.project.pk, section="discussion"))
        # Assert
        assert response.status_code in (403, 404), response.content
        assert STRANGERS_CONTENT not in response.content.decode()

    # --- collaborators: read is not write ----------------------------------

    def test_a_read_only_collaborator_may_read(self):
        # Arrange
        client = self._login("policy-reader")
        # Act
        response = client.get(self._url(self.project.pk, section="methods"))
        # Assert
        assert response.status_code == 200, response.content

    def test_a_read_only_collaborator_may_not_write(self):
        # Arrange: membership permission_level == "read". Project.can_edit says
        # no; the views' read-shaped gate says yes, which is the gap this pins.
        client = self._login("policy-reader")
        # Act
        response = self._post(client, self.project.pk, STRANGERS_CONTENT)
        # Assert
        assert response.status_code < 500, response.content
        assert response.status_code in (403, 404), response.content

    def test_a_read_only_collaborators_refused_write_leaves_no_content_behind(self):
        # Arrange
        client = self._login("policy-reader")
        # Act
        self._post(client, self.project.pk, STRANGERS_CONTENT)
        # Assert: the file is untouched, not merely that the response was denied.
        on_disk = [p for p in self.root.rglob("*.tex") if p.is_file()]
        assert all(
            STRANGERS_CONTENT not in path.read_text(encoding="utf-8", errors="ignore")
            for path in on_disk
        ), [str(path) for path in on_disk]

    def test_a_write_collaborator_may_write(self):
        # Arrange
        client = self._login("policy-writer")
        # Act
        response = self._post(
            client, self.project.pk, "Written by a write collaborator.", section="results"
        )
        # Assert
        assert response.status_code < 500, response.content
        assert response.status_code == 200, response.content

    def test_a_read_only_collaborator_cannot_reach_the_other_project(self):
        # Arrange
        client = self._login("policy-reader")
        # Act
        response = client.get(self._url(self.other_project.pk))
        # Assert
        assert response.status_code in (403, 404), response.content

    # --- ids that point nowhere, and anonymity ------------------------------

    def test_a_stale_project_id_is_a_404_and_not_a_500(self):
        # Arrange
        client = self._login("policy-owner")
        # Act
        response = client.get(self._url(999_999_999))
        # Assert
        assert response.status_code == 404, response.content

    def test_an_anonymous_caller_is_still_refused(self):
        # Arrange / Act
        response = Client().get(self._url(self.project.pk))
        # Assert
        assert response.status_code == 401, response.content


# EOF
