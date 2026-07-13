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
    AppsModule,
    ModuleInstallation,
)
from apps.workspace.apps_app.views.launcher import (
    DEFAULT_LAUNCHER_ORDER,
    MAX_PINNED_MODULES,
    _MI_DEFAULT_TAB_ORDER,
    get_pinned_module_names,
)


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

    def test_launcher_tiles_cover_launcher_visible_registry_modules(self):
        # Arrange — every registry module that opts INTO the launcher
        # (show_in_launcher, the default) must render a tile.
        from apps.infra.workspace_app.registry import get_all_modules

        visible_names = {m.name for m in get_all_modules() if m.show_in_launcher}
        # Act
        resp = self.client.get("/")
        tile_names = {t["name"] for t in resp.context["tiles"]}
        # Assert
        assert visible_names <= tile_names

    def test_clew_is_not_a_launcher_tile(self):
        # Arrange — Clew opens within a manuscript, not as a standalone
        # launcher app; it opts out via manifest show_in_launcher=false
        # (launcher pass 2).
        # Act
        resp = self.client.get("/")
        tile_names = {t["name"] for t in resp.context["tiles"]}
        # Assert
        assert "clew" not in tile_names

    def test_chat_comms_is_not_a_launcher_tile(self):
        # Arrange — Chat lives in the left sidebar (/chat/), so the grid
        # tile is redundant; comms opts out via manifest
        # show_in_launcher=false (launcher pass 2).
        # Act
        resp = self.client.get("/")
        tile_names = {t["name"] for t in resp.context["tiles"]}
        # Assert
        assert "comms" not in tile_names

    def test_store_tile_label_is_app_store(self):
        # Arrange — the Store tile is relabelled "App Store" (launcher pass 2).
        # Act
        resp = self.client.get("/")
        store_tile = next(t for t in resp.context["tiles"] if t["name"] == "store")
        # Assert
        assert store_tile["label"] == "App Store"

    def _writer_tile(self):
        resp = self.client.get("/")
        return next(t for t in resp.context["tiles"] if t["name"] == "writer")

    def test_writer_tile_version_matches_manifest_ssot(self):
        # Arrange — tile version is sourced from the manifest (SSOT), not
        # hardcoded; compare against the registry value (also the manifest).
        from apps.infra.workspace_app.registry import get_module

        manifest_version = get_module("writer").version
        # Act
        writer_tile = self._writer_tile()
        # Assert
        assert writer_tile["version"] == manifest_version

    def test_writer_tile_version_label_is_v_prefixed(self):
        # Arrange
        from apps.infra.workspace_app.registry import get_module

        manifest_version = get_module("writer").version
        # Act
        writer_tile = self._writer_tile()
        # Assert
        assert writer_tile["version_label"] == f"v{manifest_version}"

    def test_launcher_renders_version_label_span(self):
        # Arrange
        url = "/"
        # Act
        resp = self.client.get(url)
        # Assert
        assert b"launcher-tile-version" in resp.content

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


class VersionLabelHelperTest(TestCase):
    """_version_label formats manifest versions and degrades gracefully."""

    def test_semver_gets_v_prefix(self):
        # Arrange
        from apps.workspace.apps_app.views.launcher import _version_label

        # Act
        label = _version_label("0.14.0")
        # Assert
        assert label == "v0.14.0"

    def test_empty_string_degrades_to_blank(self):
        # Arrange
        from apps.workspace.apps_app.views.launcher import _version_label

        # Act
        label = _version_label("")
        # Assert
        assert label == ""

    def test_none_degrades_to_blank(self):
        # Arrange
        from apps.workspace.apps_app.views.launcher import _version_label

        # Act
        label = _version_label(None)
        # Assert
        assert label == ""

    def test_dev_marker_passes_through_without_v(self):
        # Arrange
        from apps.workspace.apps_app.views.launcher import _version_label

        # Act
        label = _version_label("dev")
        # Assert
        assert label == "dev"

    def test_already_v_prefixed_not_doubled(self):
        # Arrange
        from apps.workspace.apps_app.views.launcher import _version_label

        # Act
        label = _version_label("v1.2")
        # Assert
        assert label == "v1.2"


class DefaultPinSeedTest(TestCase):
    """A user who has never pinned anything still gets a populated sidebar.

    Regression (commit 458412b1, 2026-07-07): the sidebar switched from listing
    every module to listing only PINNED ones, but nothing ever set a pin — so
    every user's sidebar collapsed to Home + All apps, and Scholar (which owns
    the Search tab), Writer, FigRecipe, Console and the rest vanished at once.
    """

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username="unpinned-user",
            password="TestPass123!",  # pragma: allowlist secret
        )

    def setUp(self):
        self.client.login(
            username="unpinned-user",
            password="TestPass123!",  # pragma: allowlist secret
        )

    def test_fresh_user_gets_a_non_empty_pin_set(self):
        # Arrange
        user = self.user
        # Act
        pinned = get_pinned_module_names(user)
        # Assert
        assert pinned != []

    def test_default_pins_include_scholar(self):
        # Arrange — Scholar owns the Search tab the operator lost
        user = self.user
        # Act
        pinned = get_pinned_module_names(user)
        # Assert
        assert "scholar" in pinned

    def test_default_pins_respect_the_cap(self):
        # Arrange
        user = self.user
        # Act
        pinned = get_pinned_module_names(user)
        # Assert
        assert len(pinned) <= MAX_PINNED_MODULES

    def test_default_pins_exclude_home_module(self):
        # Arrange — the sidebar renders its own Home entry
        user = self.user
        # Act
        pinned = get_pinned_module_names(user)
        # Assert
        assert "home" not in pinned

    def test_default_pins_follow_the_curated_launcher_order(self):
        # Arrange — sidebar and launcher grid must agree on which apps lead
        expected = [
            name
            for name in DEFAULT_LAUNCHER_ORDER
            if name != "home"
        ][:MAX_PINNED_MODULES]
        # Act
        pinned = get_pinned_module_names(self.user)
        # Assert
        assert pinned == expected

    def test_seeding_twice_returns_the_same_pins(self):
        # Arrange
        first = get_pinned_module_names(self.user)
        # Act
        second = get_pinned_module_names(self.user)
        # Assert
        assert second == first

    def test_seeding_twice_creates_no_duplicate_rows(self):
        # Arrange
        pinned = get_pinned_module_names(self.user)
        # Act
        get_pinned_module_names(self.user)
        # Assert
        assert (
            ModuleInstallation.objects.filter(
                user=self.user, config__pinned=True
            ).count()
            == len(pinned)
        )

    def test_seeded_rows_keep_the_default_tab_order(self):
        # Arrange — a seeded row is incidental, not an explicit drag-reorder
        get_pinned_module_names(self.user)
        # Act
        orders = set(
            ModuleInstallation.objects.filter(user=self.user).values_list(
                "tab_order", flat=True
            )
        )
        # Assert
        assert orders == {_MI_DEFAULT_TAB_ORDER}

    def test_unpinning_everything_is_not_resurrected(self):
        # Arrange — seed, then let the user deliberately unpin every module
        get_pinned_module_names(self.user)
        for inst in ModuleInstallation.objects.filter(user=self.user):
            inst.config = {}
            inst.save(update_fields=["config"])
        # Act
        pinned = get_pinned_module_names(self.user)
        # Assert — an empty sidebar the user chose must stay empty
        assert pinned == []

    def test_sidebar_context_exposes_scholar_for_fresh_user(self):
        # Arrange
        url = "/"
        # Act
        resp = self.client.get(url)
        # Assert
        assert "scholar" in [
            mod.name for mod in resp.context["workspace_pinned_modules"]
        ]


# EOF
