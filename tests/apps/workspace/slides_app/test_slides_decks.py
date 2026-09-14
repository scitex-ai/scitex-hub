#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: tests/apps/workspace/slides_app/test_slides_decks.py
"""Slides decks are Markdown files inside the project, written only by editors.

Real client, real ORM, real files on disk; no mocks.
"""

import json
import shutil
import tempfile
from pathlib import Path

from django.contrib.auth.models import User
from django.test import TestCase

from apps.infra.project_app.models import Project


class SlidesDeckApiTest(TestCase):
    def setUp(self):
        self.base = Path(tempfile.mkdtemp(prefix="slides-test-"))
        self.root = self.base / "proj"
        (self.root / "figures").mkdir(parents=True)
        self.owner = User.objects.create_user(
            username="slides-owner", password="TestPass123!"  # pragma: allowlist secret
        )
        self.project = Project.objects.create(
            owner=self.owner,
            name="Spike Sorting",
            slug="slides-study",
            visibility="public",
            local_path=str(self.root),
        )
        self.ref = "slides-owner/slides-study"

    def tearDown(self):
        shutil.rmtree(self.base, ignore_errors=True)

    def _post(self, url, payload):
        return self.client.post(
            url, data=json.dumps(payload), content_type="application/json"
        )

    def test_creating_a_deck_writes_the_markdown_inside_the_project_only(self):
        # Arrange
        self.client.force_login(self.owner)
        payload = {"project": self.ref, "name": "../../escape", "content": "# Hi"}
        # Act
        self._post("/apps/slides/api/deck/", payload)
        # Assert
        written = [p.relative_to(self.base) for p in self.base.rglob("escape.md")]
        assert written == [Path("proj/slides/escape.md")]

    def test_new_deck_from_project_has_one_slide_per_figure(self):
        # Arrange
        self.client.force_login(self.owner)
        (self.root / "figures" / "raster.png").write_bytes(b"\x89PNG\r\n")
        (self.root / "figures" / "spikes.svg").write_text("<svg/>")
        # Act
        response = self._post(
            "/apps/slides/api/deck/from-project/", {"project": self.ref}
        )
        # Assert
        assert response.json()["content"].count("](../figures/") == 2

    def test_non_owner_cannot_write_a_deck(self):
        # Arrange
        stranger = User.objects.create_user(
            username="slides-stranger", password="TestPass123!"  # pragma: allowlist secret
        )
        self.client.force_login(stranger)
        payload = {"project": self.ref, "name": "hijack", "content": "# Mine"}
        # Act
        response = self._post("/apps/slides/api/deck/", payload)
        # Assert
        assert response.status_code == 403


# EOF
