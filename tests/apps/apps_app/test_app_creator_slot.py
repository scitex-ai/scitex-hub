#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: tests/apps/apps_app/test_app_creator_slot.py
"""App Creator is an empty "+" slot, always last in Work (operator, 2026-09-14).

Real client, real ORM, real templates; no mocks.
"""

import json
import re

from django.contrib.auth.models import User
from django.test import TestCase


def _work_band(html: str) -> str:
    start = html.index('data-group="work" aria-label')
    end = re.compile(r'class="launcher-group" role="group" data-group="(?!work")')
    return html[start : end.search(html, start).start()]


def _cells(html: str) -> list[tuple[str, str]]:
    """(class, data-module) of every grid cell in the Work band, in order."""
    return re.findall(
        r'<a\b[^>]*?class="([^"]*)"[^>]*?data-module="([^"]+)"', _work_band(html)
    )


class AppCreatorSlotTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username="app-creator-slot-user",
            password="TestPass123!",  # pragma: allowlist secret
        )

    def setUp(self):
        self.client.force_login(self.user)

    def _home(self) -> str:
        return self.client.get("/apps/").content.decode("utf-8")

    def test_last_work_cell_is_the_dashed_app_creator_slot(self):
        # Arrange
        url = "/apps/"
        # Act
        last = _cells(self.client.get(url).content.decode("utf-8"))[-1]
        # Assert
        assert last == ("launcher-slot launcher-slot--add", "create-app")

    def test_app_creator_slot_has_no_version_label(self):
        # Arrange
        html = self._home()
        # Act
        start = html.index('data-module="create-app"')
        slot = html[start : html.index("</a>", start)]
        # Assert
        assert "launcher-tile-version" not in slot

    def test_app_creator_slot_is_labelled_app_creator(self):
        # Arrange
        html = self._home()
        # Act
        start = html.index('data-module="create-app"')
        slot = html[start : html.index(">", start)]
        # Assert
        assert 'aria-label="App Creator"' in slot

    def test_slot_stays_last_after_the_user_reorders_it_to_the_front(self):
        # Operator iPhone 2026-09-14: 1000+ reorder values put it FIRST in Work.
        # Arrange
        self.client.post(
            "/apps/store/api/reorder/",
            data=json.dumps({"order": ["create-app", "tools", "writer", "scholar"]}),
            content_type="application/json",
        )
        # Act
        cells = self.client.get("/apps/").context["groups"][1]["cells"]
        # Assert
        assert cells[-1]["name"] == "create-app"

    def test_slot_cannot_be_saved_into_the_dock(self):
        # Arrange
        body = json.dumps({"dock": ["launcher", "create-app"]})
        # Act
        response = self.client.post(
            "/apps/store/api/dock/", data=body, content_type="application/json"
        )
        # Assert
        assert response.status_code == 400


# EOF
