#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The Dataset leaf through the hub's GENERIC mounts, per role, end to end.

The leaf (scitex-dataset >= 0.16.0) owns its pages (``scitex.apps`` →
/apps/dataset/) and its REST operations (``scitex.apis`` →
/api/v1/dataset/); the hub mounts both generically and answers the SDK host
contract over its real project model and API keys:

- a project MEMBER (read permission) opens the page and lists the project's
  public datasets; a NON-MEMBER gets 404, the same as a missing project;
- a MAINTAINER records a public dataset in the project; a read-only member
  gets 403 and nothing is written;
- a personal API key scoped ``dataset:*:read`` searches from a script, and
  cannot write;
- anonymous: the page sends to log in; the API answers 401 problem+json.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from django.conf import settings as django_settings
from django.contrib.auth.models import User
from django.test import Client, TestCase, override_settings
from django.urls import resolve

from apps.infra.accounts_app.models.api_key import APIKey
from apps.infra.project_app.models import Project, ProjectMembership

PASSWORD = "TestPass123!"  # pragma: allowlist secret
BASE = "/apps/dataset/"
API = "/api/v1/dataset/"
PROJECT = "ds-owner/eeg"


def test_the_dataset_page_resolves_to_the_leaf_namespace():
    # Arrange
    path = BASE
    # Act
    match = resolve(path)
    # Assert
    assert match.view_name == "scitex_dataset:index"


class DatasetMountRoleTest(TestCase):
    """The role matrix over real users, a real project and real folders."""

    @classmethod
    def setUpTestData(cls):
        cls.owner = User.objects.create_user(username="ds-owner", password=PASSWORD)
        cls.maintainer = User.objects.create_user(
            username="ds-maint", password=PASSWORD
        )
        cls.member = User.objects.create_user(username="ds-member", password=PASSWORD)
        cls.stranger = User.objects.create_user(
            username="ds-stranger", password=PASSWORD
        )
        cls.project = Project.objects.create(
            slug="eeg", owner=cls.owner, name="eeg", visibility="private"
        )
        ProjectMembership.objects.create(
            project=cls.project, user=cls.maintainer, permission_level="write"
        )
        ProjectMembership.objects.create(
            project=cls.project, user=cls.member, permission_level="read"
        )

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.base = Path(tmp.name)
        overrides = override_settings(BASE_DIR=self.base)
        overrides.enable()
        self.addCleanup(overrides.disable)
        assert str(django_settings.BASE_DIR) == str(self.base)
        self.root = self.base / "data" / "users" / "ds-owner" / "proj" / "eeg"
        (self.root / "data" / "results").mkdir(parents=True)
        (self.root / "data" / "results" / "metrics.json").write_text("{}")

    def _client(self, user=None):
        client = Client()
        if user is not None:
            client.force_login(user)
        return client

    def _page(self, user):
        return self._client(user).get(BASE + f"?project={PROJECT}")

    def _api_get(self, user, path, **params):
        return self._client(user).get(API + path, params)

    def _record(self, user, key="rec-1"):
        return self._client(user).post(
            API + "project-datasets",
            json.dumps({"project": PROJECT, "dataset": "reference:mnist-idx"}),
            content_type="application/json",
            HTTP_IDEMPOTENCY_KEY=key,
        )

    def _token(self, scopes):
        _key, raw = APIKey.create_key(self.stranger, "script", scopes=scopes)
        return raw

    # -- members read ------------------------------------------------------

    def test_a_member_can_open_the_page(self):
        # Arrange
        user = self.member
        # Act
        response = self._page(user)
        # Assert
        assert response.status_code == 200

    def test_project_outputs_are_not_shown_as_datasets(self):
        # Arrange
        user = self.member
        # Act
        html = self._page(user).content.decode()
        # Only the leaf's own content: the hub's workspace sidebar preloads
        # the project file tree, where project outputs legitimately appear.
        # A missing <main> raises here instead of passing vacuously.
        leaf = html.split('<main id="main-content"', 1)[1].split("</main>", 1)[0]
        # Assert
        assert "metrics.json" not in leaf

    def test_a_member_lists_the_projects_public_datasets(self):
        # Arrange
        user = self.member
        # Act
        response = self._api_get(user, "project-datasets", project=PROJECT)
        # Assert
        assert (response.status_code, response.json()["data"]) == (200, [])

    # -- writes ----------------------------------------------------------------

    def test_a_maintainer_records_a_public_dataset(self):
        # Arrange
        user = self.maintainer
        # Act
        response = self._record(user)
        # Assert
        assert (
            response.status_code,
            (self.root / ".scitex/dataset/sources.json").exists(),
        ) == (
            201,
            True,
        )

    def test_a_read_only_member_cannot_record(self):
        # Arrange
        user = self.member
        # Act
        response = self._record(user)
        # Assert
        assert (response.status_code, (self.root / ".scitex").exists()) == (403, False)

    # -- non-members and anonymous ---------------------------------------------

    def test_a_non_member_gets_404_on_the_page(self):
        # Arrange
        user = self.stranger
        # Act
        response = self._page(user)
        # Assert
        assert response.status_code == 404

    def test_a_non_member_gets_404_on_the_api(self):
        # Arrange
        user = self.stranger
        # Act
        response = self._api_get(user, "project-datasets", project=PROJECT)
        # Assert
        assert response.status_code == 404

    def test_a_missing_project_answers_like_a_foreign_one(self):
        # Arrange
        user = self.member
        # Act
        response = self._api_get(user, "project-datasets", project="ds-owner/nope")
        # Assert
        assert response.status_code == 404

    def test_an_anonymous_visitor_is_sent_to_log_in(self):
        # Arrange
        client = self._client()
        # Act
        response = client.get(BASE + f"?project={PROJECT}")
        # Assert
        assert (response.status_code, "login" in response["Location"]) == (302, True)

    def test_an_anonymous_api_call_is_a_401_problem(self):
        # Arrange
        client = self._client()
        # Act
        response = client.get(API + "datasets", {"q": "mnist"})
        # Assert
        assert (response.status_code, response["Content-Type"]) == (
            401,
            "application/problem+json",
        )

    # -- personal API keys ------------------------------------------------------

    def test_a_read_key_searches_public_datasets_from_a_script(self):
        # Arrange
        raw = self._token(["dataset:*:read"])
        # Act
        response = Client().get(
            API + "datasets",
            {"q": "mnist", "repository": "reference"},
            HTTP_AUTHORIZATION=f"Bearer {raw}",
        )
        # Assert
        assert "reference:mnist-idx" in [d["id"] for d in response.json()["data"]]

    def test_a_read_key_cannot_write(self):
        # Arrange
        raw = self._token(["dataset:*:read"])
        # Act
        response = Client().post(
            API + "project-datasets",
            json.dumps({"project": PROJECT, "dataset": "reference:mnist-idx"}),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {raw}",
            HTTP_IDEMPOTENCY_KEY="k",
        )
        # Assert
        assert response.json()["code"] == "api.insufficient_scope"

    def test_a_bad_key_is_401_not_anonymous(self):
        # Arrange
        header = "Bearer scitex_not_a_key"
        # Act
        response = Client().get(API + "datasets", {"q": "x"}, HTTP_AUTHORIZATION=header)
        # Assert
        assert response.status_code == 401
