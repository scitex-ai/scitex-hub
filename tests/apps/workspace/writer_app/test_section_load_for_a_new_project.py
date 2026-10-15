#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Opening Writer in the registered-project journey must not answer with a 5xx.

Two ordinary states of a project that was just registered both used to be
answered as same-origin **500**s by the page's own section load
(`/apps/writer/api/project/<id>/section/<name>/`):

1. the project's directory is not on disk yet — Writer creates it lazily
   (`initialize-workspace`), so this fetch can arrive first. The view's
   `writer_service.writer_dir` raises RuntimeError, which the handler turned into
   a 500. **This is the reported blocker.**
2. the directory exists but the section has not been written — the view raised
   ValueError on a None read and its own handler turned that into a 500.

Both now answer 200 with empty content, which is the shape the client already
renders: SectionLoading treats !ok as a failure but renders `success: true` with
`content: ""` as normal empty content. No client change is made. A write into a
workspace that is not on disk is refused with 409 rather than 500, because there
is nowhere to write and the caller can act on that.

Anonymity is unchanged: the decorator still answers 401, and the per-project
identity gate in front of the missing-content branch is untouched.
"""

import json
import shutil

from django.contrib.auth.models import User
from django.test import Client, TestCase

from apps.infra.project_app.models import Project
from apps.infra.project_app.services.project_filesystem import (
    get_project_filesystem_manager,
)

PASSWORD = "TestPass123!"  # pragma: allowlist secret


class SectionLoadForANewProjectTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = User.objects.create_user(username="new-proj-owner", password=PASSWORD)
        # The journey in this test: a registered project whose directory IS
        # there (workspace created, section never written). The directory is made
        # by the product's own call — the same one initialize-workspace uses —
        # because `get_project_root_path` resolves `<base>/<slug>` and requires
        # it to exist; `local_path` plays no part in that resolution.
        cls.ready = Project.objects.create(
            slug="ready-study",
            owner=cls.owner,
            name="ready-study",
            visibility="private",
        )
        manager = get_project_filesystem_manager(cls.owner)
        created, cls.ready_root = manager.create_project_directory(
            cls.ready, use_template=False
        )
        cls.ready_base = manager.base_path
        # The filesystem is not rolled back between runs, so clear anything a
        # previous run wrote: "the section has not been written" has to be true
        # of the directory, not merely assumed of it.
        for leftover in cls.ready_root.rglob("*.tex"):
            leftover.unlink()
        # ... and the state the report describes: the project row exists with an
        # active owner and slug, but its directory was never created.
        cls.unborn = Project.objects.create(
            slug="unborn-study",
            owner=cls.owner,
            name="unborn-study",
            visibility="private",
        )
        cls.addClassCleanup(shutil.rmtree, str(cls.ready_base / cls.ready.slug), True)
        cls.addClassCleanup(shutil.rmtree, str(cls.ready_base / cls.unborn.slug), True)

    def _url(self, project_id, section="abstract"):
        return f"/apps/writer/api/project/{project_id}/section/{section}/?doc_type=manuscript"

    def _login(self):
        client = Client()
        client.login(username="new-proj-owner", password=PASSWORD)
        return client

    # --- the reported blocker: no directory on disk yet ---------------------

    def test_a_project_directory_that_is_not_on_disk_yet_is_not_a_server_error(self):
        # Arrange
        client = self._login()
        # Act
        response = client.get(self._url(self.unborn.pk))
        # Assert
        assert response.status_code < 500, response.content
        assert response.status_code == 200, response.content

    def test_a_project_directory_that_is_not_on_disk_yet_says_so(self):
        # Arrange
        client = self._login()
        # Act
        payload = json.loads(client.get(self._url(self.unborn.pk)).content)
        # Assert: empty editor, and the reason is stated rather than implied.
        assert payload["success"] is True, payload
        assert payload["content"] == "", payload
        assert payload["workspace_ready"] is False, payload

    def test_saving_into_a_workspace_that_is_not_on_disk_is_a_refusal_and_not_a_500(self):
        # Arrange
        client = self._login()
        body = json.dumps({"content": "too early", "doc_type": "manuscript"})
        # Act
        response = client.post(
            self._url(self.unborn.pk), data=body, content_type="application/json"
        )
        # Assert: something the caller can act on, not a server error.
        assert response.status_code < 500, response.content
        assert response.status_code == 409, response.content

    # --- the second ordinary state: directory there, section unwritten -------

    def test_an_unwritten_section_is_not_a_server_error(self):
        # Arrange
        client = self._login()
        # Act
        response = client.get(self._url(self.ready.pk))
        # Assert
        assert response.status_code < 500, response.content
        assert response.status_code == 200, response.content

    def test_an_unwritten_section_is_answered_with_content_the_client_can_render(self):
        # Arrange
        client = self._login()
        # Act
        response = client.get(self._url(self.ready.pk, section="discussion"))
        payload = json.loads(response.content)
        # Assert: a section whose file was not on disk comes back as renderable
        # content — NOT as a 5xx. `missing` is captured before the read because
        # scitex-writer materialises the file from its packaged template WHILE
        # reading it, which is also why `file_path` is populated afterwards: it is
        # the path the read created, not an error. Emptiness is deliberately not
        # asserted — the leaf's template text is a claim about the leaf, not
        # about this view's contract.
        assert response.status_code == 200, response.content
        assert payload["success"] is True, payload
        assert isinstance(payload["content"], str), payload
        assert payload["workspace_ready"] is True, payload
        # `missing` is deliberately NOT asserted here. Constructing the writer
        # scaffolds the workspace — template section files appear as a side effect
        # — so whether a given section was "missing" depends on whether any
        # earlier request in the same run already built one. That is real and
        # documented, not a thing to pin in an assertion; the branch it feeds is
        # covered by the workspace_ready case above.

    def test_a_written_section_still_round_trips(self):
        # Arrange: the ordinary path must be untouched by the fix. This test
        # writes a file, and TestCase rolls back the DATABASE but not the
        # filesystem — so it uses its own section, or it would leave content
        # behind for the "unwritten" tests to read.
        client = self._login()
        body = json.dumps({"content": "Hello from the round trip.", "doc_type": "manuscript"})
        url = self._url(self.ready.pk, section="title")
        # Act
        posted = client.post(url, data=body, content_type="application/json")
        fetched = client.get(url)
        # Assert
        assert posted.status_code < 500, posted.content
        assert fetched.status_code < 500, fetched.content
        payload = json.loads(fetched.content)
        assert payload["success"] is True, payload
        assert "Hello from the round trip." in payload["content"], payload

    # --- the fix must not turn real errors into 200s, or open the door -------

    def test_a_missing_project_is_still_a_404_and_not_a_500(self):
        # Arrange
        client = self._login()
        # Act
        response = client.get(self._url(999_999_999))
        # Assert
        assert response.status_code == 404, response.content

    def test_an_anonymous_caller_is_still_refused(self):
        # Arrange: the fix touches the two ordinary-state branches only, so the
        # identity gate in front of them must behave exactly as before.
        # Act
        response = Client().get(self._url(self.ready.pk))
        # Assert
        assert response.status_code == 401, response.content


# EOF
