#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Presence heartbeat endpoints for the leaf editor collab pane.

Slice 1 (2026-10-24): POST heartbeat records (user, project) presence;
GET active lists users seen within the model window. Fail-closed: unknown
OR invisible projects both 404, so the endpoint is not an existence oracle
for private projects.
"""

import json

from django.contrib.auth.models import User
from django.test import Client, TestCase

from apps.infra.project_app.models import Project
from apps.infra.project_app.services.project_filesystem import (
    get_project_filesystem_manager,
)
from tests.apps.workspace.writer_app._old_direct_gate import (
    writer_old_direct_urls,
)

PASSWORD = "TestPass123!"  # pragma: allowlist secret


def _heartbeat(client, body):
    with writer_old_direct_urls():
        return client.post(
            "/apps/writer/old-direct/collaboration/presence/heartbeat/",
            data=json.dumps(body),
            content_type="application/json",
        )


def _active(client, project):
    with writer_old_direct_urls():
        return client.get(
            "/apps/writer/old-direct/collaboration/presence/active/",
            {"project": project},
        )


class PresenceHeartbeatTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = User.objects.create_user(
            username="presence-owner", password=PASSWORD
        )
        cls.other = User.objects.create_user(
            username="presence-other", password=PASSWORD
        )
        cls.project = Project.objects.create(
            slug="presence-study",
            owner=cls.owner,
            name="presence-study",
            visibility="private",
        )
        get_project_filesystem_manager(cls.owner).create_project_directory(
            cls.project, use_template=False
        )

    def _authed(self, username):
        client = Client()
        client.login(username=username, password=PASSWORD)
        return client

    def test_unauthenticated_heartbeat_redirects_to_login(self):
        response = _heartbeat(Client(), {"project": "x/y"})
        assert response.status_code == 302, response.status_code

    def test_unknown_project_is_404(self):
        response = _heartbeat(
            self._authed("presence-owner"), {"project": "nobody/nothing"}
        )
        assert response.status_code == 404, response.content[:200]

    def test_other_owners_private_project_is_404_not_403(self):
        ref = f"{self.owner.username}/{self.project.slug}"
        response = _heartbeat(self._authed("presence-other"), {"project": ref})
        assert response.status_code == 404, response.content[:200]
        response = _active(self._authed("presence-other"), ref)
        assert response.status_code == 404, response.content[:200]

    def test_heartbeat_then_active_lists_the_user(self):
        client = self._authed("presence-owner")
        ref = f"{self.owner.username}/{self.project.slug}"
        response = _heartbeat(client, {"project": ref, "section": "abstract"})
        assert response.status_code == 200, response.content[:200]
        assert response.json() == {"success": True}
        response = _active(client, ref)
        assert response.status_code == 200, response.content[:200]
        users = response.json()["users"]
        assert [u["username"] for u in users] == ["presence-owner"]
        assert users[0]["section"] == "abstract"

    def test_heartbeat_accepts_numeric_project_id(self):
        client = self._authed("presence-owner")
        response = _heartbeat(client, {"project": self.project.id})
        assert response.status_code == 200, response.content[:200]

    def test_malformed_json_is_400(self):
        with writer_old_direct_urls():
            client = self._authed("presence-owner")
            response = client.post(
                "/apps/writer/old-direct/collaboration/presence/heartbeat/",
                data="{broken",
                content_type="application/json",
            )
        assert response.status_code == 400, response.status_code
