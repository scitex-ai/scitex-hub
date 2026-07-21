#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for launcher-tile availability states (coming_soon / desktop_only).

Operator directive (Telegram 1483, card
hub-launcher-tile-availability-states): communicate availability AT the
home icon. The state is a FIELD — manifest.json for registry modules,
the AppsModule catalog column for store-published apps — never hardcoded
in templates. Coming-soon tiles badge and never navigate; desktop-only
tiles badge on mobile (CSS breakpoint) and block launch there (TS).

All tests use the real Django test DB via django.test.TestCase — no
mocks (same conventions as test_launcher.py / test_launcher_store_tiles).
Expected strings are independent literals, never read back off the row
the tile was built from.
"""

import pytest
from django.contrib.auth.models import User
from django.test import TestCase

from apps.infra.workspace_app.registry import (
    AVAILABILITY_STATES,
    _manifest_to_module_config,
    get_module,
)
from apps.workspace.apps_app.models import AppsModule


class ManifestAvailabilityContractTest(TestCase):
    """The manifest is the SSoT: availability flows into ModuleConfig."""

    def test_writer_manifest_declares_desktop_only(self):
        # Arrange — writer is a LaTeX editing surface, desktop work
        expected = "desktop_only"
        # Act
        mod = get_module("writer")
        # Assert
        assert mod is not None and mod.availability == expected

    def test_figrecipe_manifest_declares_desktop_only(self):
        # Arrange
        expected = "desktop_only"
        # Act
        mod = get_module("figrecipe")
        # Assert
        assert mod is not None and mod.availability == expected

    def test_console_manifest_declares_desktop_only(self):
        # Arrange
        expected = "desktop_only"
        # Act
        mod = get_module("console")
        # Assert
        assert mod is not None and mod.availability == expected

    def test_scholar_manifest_declares_nothing(self):
        # Arrange — Scholar works on a phone; its manifest stays silent
        expected = ""
        # Act
        mod = get_module("scholar")
        # Assert
        assert mod is not None and mod.availability == expected

    def test_unknown_availability_fails_loudly(self):
        # Arrange — a typo'd state must never render as a launchable tile
        data = {
            "name": "typo-app",
            "label": "Typo App",
            "app_name": "apps_app",
            "availability": "comign_soon",
        }
        # Act
        # (the conversion itself is the act under assertion below)
        # Assert
        with pytest.raises(ValueError):
            _manifest_to_module_config(data)

    def test_availability_states_are_the_known_triple(self):
        # Arrange — the template/CSS/TS all key off these exact strings
        expected = ("available", "coming_soon", "desktop_only")
        # Act
        states = AVAILABILITY_STATES
        # Assert
        assert states == expected


class ModelAvailabilityDefaultTest(TestCase):
    """The catalog column defaults to fully available — no accidental gating."""

    def test_new_row_defaults_to_available(self):
        # Arrange
        expected = "available"
        # Act
        row = AppsModule.objects.create(module_name="availability-default-app")
        # Assert
        assert row.availability == expected


class SeedCopiesAvailabilityTest(TestCase):
    """ensure_builtin_modules mirrors the manifest state into the catalog."""

    def test_seed_stamps_writer_row_desktop_only(self):
        # Arrange
        from apps.workspace.apps_app.management.commands.seed_apps import (
            ensure_builtin_modules,
        )

        expected = "desktop_only"
        # Act
        ensure_builtin_modules()
        row = AppsModule.objects.get(module_name="writer")
        # Assert
        assert row.availability == expected

    def test_seed_stamps_scholar_row_available(self):
        # Arrange — a silent manifest means fully available, not blank
        from apps.workspace.apps_app.management.commands.seed_apps import (
            ensure_builtin_modules,
        )

        expected = "available"
        # Act
        ensure_builtin_modules()
        row = AppsModule.objects.get(module_name="scholar")
        # Assert
        assert row.availability == expected


class LauncherTileAvailabilityTest(TestCase):
    """_build_tiles surfaces availability + is_launchable per tile."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username="availability-user",
            password="TestPass123!",  # pragma: allowlist secret
        )
        # A store-published unfinished app (the Live Paper case): outside
        # the workspace registry, so it reaches the grid via the store
        # branch, carrying its availability on the catalog row.
        AppsModule.objects.create(
            module_name="scitex-live-paper-app",
            category="other",
            visibility="public",
            availability="coming_soon",
        )

    def setUp(self):
        self.client.login(
            username="availability-user",
            password="TestPass123!",  # pragma: allowlist secret
        )

    def _tile(self, name):
        resp = self.client.get("/")
        return next(t for t in resp.context["tiles"] if t["name"] == name)

    def test_writer_tile_is_desktop_only(self):
        # Arrange
        expected = "desktop_only"
        # Act
        tile = self._tile("writer")
        # Assert
        assert tile["availability"] == expected

    def test_desktop_only_tile_stays_launchable(self):
        # Arrange — desktop-only gates the PHONE, not the desktop; the
        # tile keeps its href and CSS/TS handle the mobile side.
        expected = True
        # Act
        tile = self._tile("writer")
        # Assert
        assert tile["is_launchable"] is expected

    def test_scholar_tile_is_available(self):
        # Arrange
        expected = "available"
        # Act
        tile = self._tile("scholar")
        # Assert
        assert tile["availability"] == expected

    def test_coming_soon_store_tile_carries_state(self):
        # Arrange
        expected = "coming_soon"
        # Act
        tile = self._tile("scitex-live-paper-app")
        # Assert
        assert tile["availability"] == expected

    def test_coming_soon_tile_is_not_launchable(self):
        # Arrange
        expected = False
        # Act
        tile = self._tile("scitex-live-paper-app")
        # Assert
        assert tile["is_launchable"] is expected


class LauncherTemplateAvailabilityTest(TestCase):
    """The template renders badges + drops the href from the field alone."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username="availability-tpl-user",
            password="TestPass123!",  # pragma: allowlist secret
        )
        AppsModule.objects.create(
            module_name="scitex-live-paper-app",
            category="other",
            visibility="public",
            availability="coming_soon",
        )

    def setUp(self):
        self.client.login(
            username="availability-tpl-user",
            password="TestPass123!",  # pragma: allowlist secret
        )

    def test_coming_soon_badge_class_rendered(self):
        # Arrange
        expected = b"launcher-badge-coming-soon"
        # Act
        resp = self.client.get("/")
        # Assert
        assert expected in resp.content

    def test_coming_soon_badge_text_rendered(self):
        # Arrange
        expected = b"Coming Soon"
        # Act
        resp = self.client.get("/")
        # Assert
        assert expected in resp.content

    def test_coming_soon_tile_has_no_href(self):
        # Arrange — the store tile's launch URL; data-detail-url may still
        # carry it, but no anchor may use it as an href.
        forbidden = b'href="/apps/store/scitex-live-paper-app/"'
        # Act
        resp = self.client.get("/")
        # Assert
        assert forbidden not in resp.content

    def test_coming_soon_tile_carries_data_availability(self):
        # Arrange — the data attribute drives CSS dimming + the TS gate
        expected = b'data-availability="coming_soon"'
        # Act
        resp = self.client.get("/")
        # Assert
        assert expected in resp.content

    def test_coming_soon_tile_is_aria_disabled(self):
        # Arrange
        expected = b'aria-disabled="true"'
        # Act
        resp = self.client.get("/")
        # Assert
        assert expected in resp.content

    def test_desktop_only_tile_carries_data_availability(self):
        # Arrange — writer declares desktop_only in its manifest
        expected = b'data-availability="desktop_only"'
        # Act
        resp = self.client.get("/")
        # Assert
        assert expected in resp.content

    def test_desktop_only_badge_rendered(self):
        # Arrange — the badge is always in the DOM; CSS shows it under the
        # mobile breakpoint only (media queries are not testable here).
        expected = b"launcher-badge-desktop-only"
        # Act
        resp = self.client.get("/")
        # Assert
        assert expected in resp.content

    def test_available_tile_keeps_its_href(self):
        # Arrange — scholar launches everywhere
        expected = b'href="/apps/scholar/"'
        # Act
        resp = self.client.get("/")
        # Assert
        assert expected in resp.content


# EOF
