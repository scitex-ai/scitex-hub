#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The save action is labelled for the researcher, not for git.

Product compass L412: the control a researcher uses to persist their work is
labelled "Commit" — git vocabulary in the path of the primary writing action.
The label becomes "Save checkpoint"; the endpoint, the ids and the CSS classes
are NOT renamed, because those are the machine-facing names and nothing about
the wording change should move under a client's feet.

The assertions are deliberately narrow. "Commit History" (a timeline heading) and
the message placeholder are left alone by this change, so a blanket "no 'Commit'
anywhere" check would be wrong — what must not survive is the ACTION label.
"""

from django.contrib.auth.models import User
from django.test import Client, TestCase

from apps.infra.project_app.models import Project
from apps.infra.project_app.services.project_filesystem import (
    get_project_filesystem_manager,
)

PASSWORD = "TestPass123!"  # pragma: allowlist secret
ACTION_LABEL = "Save checkpoint"
RETIRED_ACTION_LABELS = (">Commit<", "Commit Changes")


class SaveCheckpointLabelTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = User.objects.create_user(username="label-owner", password=PASSWORD)
        cls.project = Project.objects.create(
            slug="label-study", owner=cls.owner, name="label-study", visibility="private"
        )
        get_project_filesystem_manager(cls.owner).create_project_directory(
            cls.project, use_template=False
        )

    def _page(self):
        client = Client()
        client.login(username="label-owner", password=PASSWORD)
        return client.get(
            f"/apps/writer/?project={self.owner.username}/{self.project.slug}"
        )

    def test_the_save_action_is_labelled_save_checkpoint(self):
        # Arrange / Act
        response = self._page()
        html = response.content.decode()
        # Assert
        assert response.status_code == 200, response.content[:400]
        assert ACTION_LABEL in html, "the save action is not labelled 'Save checkpoint'"

    def test_the_git_word_is_gone_from_the_action_label(self):
        # Arrange / Act
        html = self._page().content.decode()
        # Assert: the action label, not every occurrence of the word — the
        # timeline heading and the message field are separate decisions.
        still_present = [label for label in RETIRED_ACTION_LABELS if label in html]
        assert not still_present, f"git vocabulary still on the action: {still_present}"

    def test_the_machine_facing_names_are_untouched(self):
        # Arrange / Act
        html = self._page().content.decode()
        # Assert: a wording change must not move the ids or classes clients use.
        assert 'id="gitCommitBtn"' in html, "the button id was renamed"
        assert "git-commit-btn" in html, "the css class was renamed"


# EOF
