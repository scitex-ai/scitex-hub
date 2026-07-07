#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for the app-launcher workspace home and pin-to-sidebar API.

All tests use the real Django test DB via django.test.TestCase — no mocks.
Each test exercises a real HTTP round-trip through the Django test client
against the real ORM (same conventions as test_views.py).
"""

from django.contrib.auth.models import User
from django.test import TestCase

from apps.workspace.apps_app.models import (
    CATEGORY_CHOICES,
    AppsModule,
    ModuleInstallation,
)
from apps.workspace.apps_app.views.launcher import MAX_PINNED_MODULES


class LauncherHomeTest(TestCase):
    """Tests for the launcher home page served at the workspace root."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username="launcher-user",
            password="TestPass123!",  # pragma: allowlist secret
        )

    def setUp(self):
        self.client.login(
            username="launcher-user",
            password="TestPass123!",  # pragma: allowlist secret
        )

    def test_launcher_view_returns_200(self):
        # Arrange
        url = "/"
        # Act
        resp = self.client.get(url)
        # Assert
        assert resp.status_code == 200

    def test_launcher_lists_registry_writer_module(self):
        # Arrange
        url = "/"
        # Act
        resp = self.client.get(url)
        # Assert
        assert b'data-module="writer"' in resp.content

    def test_launcher_tile_names_cover_all_registry_modules(self):
        # Arrange
        from apps.infra.workspace_app.registry import get_all_modules

        registry_names = {m.name for m in get_all_modules()}
        # Act
        resp = self.client.get("/")
        tile_names = {t["name"] for t in resp.context["tiles"]}
        # Assert
        assert registry_names <= tile_names

    def test_launcher_categories_match_store_categories(self):
        # Arrange
        url = "/"
        # Act
        resp = self.client.get(url)
        # Assert
        assert list(resp.context["categories"]) == list(CATEGORY_CHOICES)

    def test_launcher_anonymous_redirects_away(self):
        # Arrange
        self.client.logout()
        # Act
        resp = self.client.get("/")
        # Assert
        assert resp.status_code == 302

    def test_old_home_stays_reachable_at_apps_home(self):
        # Arrange
        url = "/apps/home/"
        # Act
        resp = self.client.get(url)
        # Assert
        assert resp.status_code == 200


class LauncherPinTest(TestCase):
    """Tests for the pin-to-sidebar API (persistence + cap)."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username="pin-user",
            password="TestPass123!",  # pragma: allowlist secret
        )
        cls.modules = [
            AppsModule.objects.create(
                module_name=f"t-pin-{index}",
                category="utility",
                visibility="public",
            )
            for index in range(MAX_PINNED_MODULES + 1)
        ]

    def setUp(self):
        self.client.login(
            username="pin-user",
            password="TestPass123!",  # pragma: allowlist secret
        )

    def test_pin_endpoint_returns_200(self):
        # Arrange
        url = "/apps/store/api/t-pin-0/pin/"
        # Act
        resp = self.client.post(url)
        # Assert
        assert resp.status_code == 200

    def test_pin_persists_pinned_flag_in_config(self):
        # Arrange
        url = "/apps/store/api/t-pin-0/pin/"
        # Act
        self.client.post(url)
        inst = ModuleInstallation.objects.get(user=self.user, module=self.modules[0])
        # Assert
        assert inst.config.get("pinned") is True

    def test_pin_toggle_twice_clears_pinned_flag(self):
        # Arrange
        url = "/apps/store/api/t-pin-0/pin/"
        self.client.post(url)
        # Act
        self.client.post(url)
        inst = ModuleInstallation.objects.get(user=self.user, module=self.modules[0])
        # Assert
        assert "pinned" not in (inst.config or {})

    def test_unpin_response_reports_pinned_false(self):
        # Arrange
        url = "/apps/store/api/t-pin-0/pin/"
        self.client.post(url)
        # Act
        resp = self.client.post(url)
        # Assert
        assert resp.json()["pinned"] is False

    def test_pins_capped_returns_400_beyond_limit(self):
        # Arrange
        for index in range(MAX_PINNED_MODULES):
            self.client.post(f"/apps/store/api/t-pin-{index}/pin/")
        # Act
        resp = self.client.post(f"/apps/store/api/t-pin-{MAX_PINNED_MODULES}/pin/")
        # Assert
        assert resp.status_code == 400

    def test_pin_cap_error_mentions_limit(self):
        # Arrange
        for index in range(MAX_PINNED_MODULES):
            self.client.post(f"/apps/store/api/t-pin-{index}/pin/")
        # Act
        resp = self.client.post(f"/apps/store/api/t-pin-{MAX_PINNED_MODULES}/pin/")
        # Assert
        assert str(MAX_PINNED_MODULES) in resp.json()["error"]

    def test_pin_requires_login_redirects_to_login(self):
        # Arrange
        self.client.logout()
        url = "/apps/store/api/t-pin-0/pin/"
        # Act
        resp = self.client.post(url)
        # Assert
        assert resp.status_code == 302

    def test_pinned_module_appears_in_sidebar_context(self):
        # Arrange
        self.client.post("/apps/store/api/t-pin-0/pin/")
        # Act — pinned names come from the launcher helper the sidebar uses
        from apps.workspace.apps_app.views.launcher import get_pinned_module_names

        pinned = get_pinned_module_names(self.user)
        # Assert
        assert "t-pin-0" in pinned


# EOF
