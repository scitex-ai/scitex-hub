#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: tests/apps/apps_app/test_home_planned_app_tiles.py
"""Coming-soon tiles for planned apps on Home (operator, 2026-09-14).

Real client, real ORM, real templates; no mocks.
"""

import re

from django.contrib.auth.models import User
from django.test import TestCase

from apps.workspace.apps_app.models import AppsModule, PlannedAppInterest
from apps.workspace.apps_app.views.planned import record_planned_app_interest


def _planned_tile(content: str, app_id: str) -> str:
    match = re.search(
        rf'<button[^>]*data-planned="{re.escape(app_id)}".*?</button>', content, re.S
    )
    return match.group(0) if match else ""


class PlannedAppTileTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username="planned-tiles-user",
            password="TestPass123!",  # pragma: allowlist secret
        )

    def setUp(self):
        self.client.force_login(self.user)

    def test_planned_app_renders_with_its_coming_soon_badge(self):
        # Arrange
        url = "/apps/"
        # Act
        tile = _planned_tile(self.client.get(url).content.decode("utf-8"), "grant-writer")
        # Assert
        assert "launcher-badge-coming-soon" in tile

    def test_placeholder_is_hidden_once_a_real_app_has_its_id(self):
        # Arrange
        AppsModule.objects.create(
            module_name="scitex-grant-writer-app", label="Grant Writer", visibility="public"
        )
        # Act
        content = self.client.get("/apps/").content.decode("utf-8")
        # Assert
        assert _planned_tile(content, "grant-writer") == ""

    def test_create_app_stays_the_last_work_tile_after_the_placeholders(self):
        # Arrange
        groups = self.client.get("/apps/").context["groups"]
        # Act
        work = next(group["cells"] for group in groups if group["key"] == "work")
        # Assert
        assert any(c.get("is_planned") for c in work) and work[-1]["name"] == "create-app"

    def test_build_link_prefills_the_create_app_form(self):
        # Arrange
        url = "/apps/"
        # Act
        tile = _planned_tile(self.client.get(url).content.decode("utf-8"), "grant-writer")
        # Assert
        assert 'data-create-url="/apps/create/?name=Grant+Writer&amp;brief=grant-writer&amp;' in tile


class PlannedAppInterestTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username="planned-interest-user",
            password="TestPass123!",  # pragma: allowlist secret
        )

    def test_notify_me_is_recorded_once_per_user(self):
        # Arrange
        record_planned_app_interest(self.user, "grant-writer", "notify")
        # Act
        record_planned_app_interest(self.user, "grant-writer", "notify")
        # Assert
        assert PlannedAppInterest.objects.filter(user=self.user, app_id="grant-writer").count() == 1

    def test_notify_and_build_are_separate_interests(self):
        # Arrange
        record_planned_app_interest(self.user, "files", "notify")
        # Act
        record_planned_app_interest(self.user, "files", "build")
        # Assert
        assert PlannedAppInterest.objects.filter(user=self.user, app_id="files").count() == 2

    def test_interest_endpoint_refuses_an_unknown_app(self):
        # Arrange
        self.client.force_login(self.user)
        # Act
        response = self.client.post(
            "/apps/store/api/planned/not-planned/interest/", {"kind": "notify"}
        )
        # Assert
        assert response.status_code == 404


# EOF
