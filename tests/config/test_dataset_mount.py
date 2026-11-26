#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The Dataset app (/apps/dataset/) through the generic plugin mount, per role.

The leaf (scitex-dataset >= 0.15.0) owns the views and the dataset logic; the
hub only mounts it (``plugin_urlpatterns``) and answers the SDK host contract
(``SCITEX_PROJECT_PROVIDER`` / ``SCITEX_PROJECT_STORAGE``). These tests pin the
contract END TO END over the hub's real project model, not the leaf in
isolation:

- a project MEMBER (read permission) can open the page and list datasets;
- a MAINTAINER (owner, or member with write permission) can upload/register;
- a read-only member gets 403 on every write and nothing is written;
- a NON-MEMBER gets 404 — the same answer as a project that does not exist;
- an anonymous visitor is sent to log in (the mount's login boundary).

Project roots live under ``settings.BASE_DIR``, so each test points BASE_DIR
at a fresh temporary directory and creates the owner's real project folder.

scitex-dataset[server] is a declared dependency of both ``[all]`` and ``[dev]``,
so it is imported unguarded here: a skip when it is absent would read as a
passing role matrix over an unmounted app.
"""

from __future__ import annotations

import hashlib
import tempfile
from pathlib import Path

from django.conf import settings as django_settings
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import resolve

from apps.infra.project_app.models import Project, ProjectMembership


PASSWORD = "TestPass123!"  # pragma: allowlist secret
BASE = "/apps/dataset/"
CSV = b"x,y\n1,2\n"


def test_the_dataset_route_resolves_to_the_leaf_namespace():
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
        (self.root / "data").mkdir(parents=True)
        (self.root / "data" / "a.csv").write_bytes(CSV)
        self.query = "?project=ds-owner/eeg"

    def _client(self, user=None):
        client = Client()
        if user is not None:
            client.force_login(user)
        return client

    def _get(self, user, path=""):
        return self._client(user).get(BASE + path + self.query)

    def _upload(self, user):
        return self._client(user).post(
            BASE + "api/upload" + self.query,
            {"file": SimpleUploadedFile("b.csv", b"1,2\n")},
        )

    def _register(self, user):
        return self._client(user).post(
            BASE + "api/register" + self.query, {"path": "data/a.csv", "name": "A"}
        )

    # -- members read ------------------------------------------------------

    def test_a_member_can_open_the_page(self):
        # Arrange
        user = self.member
        # Act
        response = self._get(user)
        # Assert
        assert response.status_code == 200

    def test_the_page_shows_the_file_checksum(self):
        # Arrange
        expected = hashlib.sha256(CSV).hexdigest()
        # Act
        html = self._get(self.member).content.decode()
        # Assert
        assert expected in html

    def test_a_member_lists_datasets_with_size_and_checksum(self):
        # Arrange
        expected = [("data/a.csv", len(CSV), hashlib.sha256(CSV).hexdigest())]
        # Act
        body = self._get(self.member, "api/datasets").json()
        # Assert
        assert [(f["path"], f["size"], f["sha256"]) for f in body["files"]] == expected

    def test_a_member_is_told_it_cannot_write(self):
        # Arrange
        user = self.member
        # Act
        body = self._get(user, "api/datasets").json()
        # Assert
        assert body["project"]["can_write"] is False

    def test_a_maintainer_is_told_it_can_write(self):
        # Arrange
        user = self.maintainer
        # Act
        body = self._get(user, "api/datasets").json()
        # Assert
        assert body["project"]["can_write"] is True

    # -- members cannot write ----------------------------------------------

    def test_a_member_cannot_upload(self):
        # Arrange
        user = self.member
        # Act
        response = self._upload(user)
        # Assert
        assert (response.status_code, (self.root / "data" / "b.csv").exists()) == (
            403,
            False,
        )

    def test_a_member_cannot_register(self):
        # Arrange
        user = self.member
        # Act
        response = self._register(user)
        # Assert
        assert (response.status_code, (self.root / ".scitex").exists()) == (403, False)

    # -- maintainers write ---------------------------------------------------

    def test_a_maintainer_can_upload(self):
        # Arrange
        user = self.maintainer
        # Act
        response = self._upload(user)
        # Assert
        assert (response.status_code, (self.root / "data" / "b.csv").read_bytes()) == (
            201,
            b"1,2\n",
        )

    def test_the_owner_can_register(self):
        # Arrange
        user = self.owner
        # Act
        response = self._register(user)
        # Assert
        assert (response.status_code, response.json()["dataset"]["registered_by"]) == (
            201,
            "ds-owner",
        )

    def test_a_registration_is_visible_to_members(self):
        # Arrange
        self._register(self.maintainer)
        # Act
        body = self._get(self.member, "api/datasets").json()
        # Assert
        assert [(d["name"], d["state"]) for d in body["registered"]] == [
            ("A", "unchanged")
        ]

    # -- non-members: 404 -----------------------------------------------------

    def test_a_non_member_gets_404_on_the_page(self):
        # Arrange
        user = self.stranger
        # Act
        response = self._get(user)
        # Assert
        assert response.status_code == 404

    def test_a_non_member_gets_404_on_the_listing(self):
        # Arrange
        user = self.stranger
        # Act
        response = self._get(user, "api/datasets")
        # Assert
        assert response.status_code == 404

    def test_a_non_member_gets_404_on_upload(self):
        # Arrange
        user = self.stranger
        # Act
        response = self._upload(user)
        # Assert
        assert (response.status_code, (self.root / "data" / "b.csv").exists()) == (
            404,
            False,
        )

    def test_a_non_member_gets_404_on_register(self):
        # Arrange
        user = self.stranger
        # Act
        response = self._register(user)
        # Assert
        assert response.status_code == 404

    def test_a_missing_project_answers_like_a_foreign_one(self):
        # Arrange
        client = self._client(self.member)
        # Act
        response = client.get(BASE + "api/datasets?project=ds-owner/nope")
        # Assert
        assert response.status_code == 404

    # -- anonymous --------------------------------------------------------------

    def test_an_anonymous_visitor_is_sent_to_log_in(self):
        # Arrange
        client = self._client()
        # Act
        response = client.get(BASE + self.query)
        # Assert
        assert (response.status_code, "login" in response["Location"]) == (302, True)
