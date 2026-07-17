#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for store-published launcher tiles' label/icon resolution.

Store apps used to render as raw package slugs with a generic
puzzle-piece icon because AppsModule had no label/icon columns (card
hub-appsmodule-missing-label-icon). The catalog now carries
manifest-fed display columns; the launcher's store branch prefers them
and falls back to a prettified module name / the generic icon.

All tests use the real Django test DB via django.test.TestCase — no
mocks (same conventions as test_launcher.py). Expected strings are
written as independent literals, never read back off the row the tile
was built from.
"""

from django.contrib.auth.models import User
from django.test import TestCase

from apps.workspace.apps_app.models import AppsModule
from apps.workspace.apps_app.services.app_loader import load_single_app
from apps.workspace.apps_app.services.manifest_display import prettify_module_name
from apps.infra.workspace_app.registry import get_module


class RegistryLoaderLabelTest(TestCase):
    """load_single_app must never surface project.name as the tile label.

    The REGISTRY path (approved apps with a project) is how the two
    operator-reported tiles actually render — the prod screenshot after
    the store-branch fix still showed the raw slugs because the loader
    used project.name (the repo slug) as the label. The catalog columns
    win; blank columns get the prettified fallback.
    """

    def test_loader_prefers_catalog_label_over_project_name(self):
        # Arrange — blank label column, no project (keeps the test off the
        # registry's project/manifest file I/O); a distinct name so the
        # module-global registry cannot collide across tests.
        row = AppsModule.objects.create(
            module_name="scitex-registry-labeltest-app",
            category="other",
            visibility="public",
        )
        # Act
        load_single_app(row)
        registered = get_module("scitex-registry-labeltest-app")
        # Assert — the prettified fallback, never the raw slug.
        assert registered is not None and registered.label == "Registry Labeltest"


class PrettifyModuleNameHelperTest(TestCase):
    """prettify_module_name strips packaging noise and title-cases."""

    def test_agentic_journal_slug_prettifies(self):
        # Arrange — one of the exact slugs the operator saw on the grid
        raw = "scitex-agentic-journal-app"
        # Act
        label = prettify_module_name(raw)
        # Assert
        assert label == "Agentic Journal"

    def test_live_paper_slug_prettifies(self):
        # Arrange — the other slug from the operator's report
        raw = "scitex-live-paper-app"
        # Act
        label = prettify_module_name(raw)
        # Assert
        assert label == "Live Paper"

    def test_plain_name_just_title_cases(self):
        # Arrange — no scitex-/-app packaging noise to strip
        raw = "mytool"
        # Act
        label = prettify_module_name(raw)
        # Assert
        assert label == "Mytool"

    def test_underscore_variant_prettifies(self):
        # Arrange
        raw = "scitex_live_paper_app"
        # Act
        label = prettify_module_name(raw)
        # Assert
        assert label == "Live Paper"

    def test_all_noise_name_falls_back_to_raw(self):
        # Arrange — stripping would leave nothing; the raw name is more
        # honest than an empty tile
        raw = "scitex-"
        # Act
        label = prettify_module_name(raw)
        # Assert
        assert label == "scitex-"


class StoreTileLabelIconTest(TestCase):
    """The store branch of _build_tiles prefers the catalog columns.

    One published row carries manifest-fed label/icon; the other has
    blank columns and must render the prettified fallback + generic
    icon. Both rows are outside the workspace registry, so they can
    only reach the grid through the store branch.
    """

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username="store-tile-user",
            password="TestPass123!",  # pragma: allowlist secret
        )
        AppsModule.objects.create(
            module_name="scitex-agentic-journal-app",
            category="other",
            visibility="public",
            label="Journal Of Agents",
            icon="fas fa-newspaper",
        )
        AppsModule.objects.create(
            module_name="scitex-live-paper-app",
            category="other",
            visibility="public",
        )

    def setUp(self):
        self.client.login(
            username="store-tile-user",
            password="TestPass123!",  # pragma: allowlist secret
        )

    def _tile(self, name):
        resp = self.client.get("/")
        return next(t for t in resp.context["tiles"] if t["name"] == name)

    def test_store_tile_uses_catalog_label_when_set(self):
        # Arrange — expected literal written independently of the row
        expected = "Journal Of Agents"
        # Act
        tile = self._tile("scitex-agentic-journal-app")
        # Assert
        assert tile["label"] == expected

    def test_store_tile_uses_catalog_icon_when_set(self):
        # Arrange
        expected = "fas fa-newspaper"
        # Act
        tile = self._tile("scitex-agentic-journal-app")
        # Assert
        assert tile["icon_fa"] == expected

    def test_blank_label_falls_back_to_prettified_name(self):
        # Arrange — expected literal written independently, not derived
        # from the row or from the helper under test
        expected = "Live Paper"
        # Act
        tile = self._tile("scitex-live-paper-app")
        # Assert
        assert tile["label"] == expected

    def test_blank_icon_falls_back_to_puzzle_piece(self):
        # Arrange
        expected = "fas fa-puzzle-piece"
        # Act
        tile = self._tile("scitex-live-paper-app")
        # Assert
        assert tile["icon_fa"] == expected

    def test_raw_slug_no_longer_shown_as_label(self):
        # Arrange — the regression the operator reported three times
        raw_slug = "scitex-live-paper-app"
        # Act
        tile = self._tile(raw_slug)
        # Assert
        assert tile["label"] != raw_slug


# EOF
