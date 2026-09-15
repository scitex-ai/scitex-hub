#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: tests/apps/apps_app/test_launcher_rows_and_my_projects.py
"""Launcher groups and the "My Projects" / "Public Projects" names.

Operator, 2026-09-14:
  * "Projects" is "My Projects" (JA 「マイプロジェクト」); the existing Explore
    app is relabelled "Public Projects" (JA 「パブリックプロジェクト」) — same
    URL, same module name.
  * Infrastructure: My Projects, Public Projects, Agents, Cards.
  * Applications: Scholar, FigRecipe, [Stats — its own app later], Writer.
  * Then: Chat, Settings, Tools (Console, Clew if ever shown).
  * Last: Docs, App Store, Storage.

WHY LABELS ARE READ FROM THE MANIFEST FILES, NOT THE REGISTRY
Agents and Cards are optional plugin tiles: the registry only knows them where
their package is installed, and in CI the registry has been measured reading
order=50 for every manifest (see test_app_order_is_the_operators_order.py). The
curated list is what the grid sorts by, and the manifest files are the SSoT for
labels (workspace manifests plus the launcher LINK manifests for Chat and
Settings), so joining those is the deterministic statement of what a user sees.

The header "Apps" dropdown these tests used to read was removed on 2026-09-14;
the same statements are now made against the grid itself.
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest
from django.contrib.auth.models import User
from django.test import RequestFactory, TestCase
from django.utils import translation
from django.utils.translation import pgettext

from apps.workspace.apps_app.views.launcher import launcher_context
from apps.workspace.apps_app.views.launcher_order import (
    DEFAULT_LAUNCHER_ORDER,
    default_order_value,
)

_REPO_ROOT = Path(__file__).resolve().parents[3]

EXPECTED_TILE_ORDER = [
    # FOUNDATION (operator groups, 2026-09-14 16:3xZ)
    "My Projects",
    "Agents",
    "Cards",
    "Storage",
    "Files",
    # WORK (Stats keeps its slot until its app lands)
    "Scholar",
    "FigRecipe",
    "stats",
    "Writer",
    "Chat",
    "Image Tools",
    "PDF Tools",
    "Text Tools",
    "Developer Tools",
    "Media Tools",
    "Tools",
    "Console",
    "Clew",
    "App Creator",
    # PUBLISH (proposed 2026-09-14, Telegram 6040)
    "Slides",
    "Public Projects",
    # SYSTEM
    "Settings",
    "Docs",
    "App Store",
]


def _manifest_labels():
    labels = {}
    manifests = sorted((_REPO_ROOT / "apps" / "workspace").glob("*/manifest.json"))
    manifests += sorted(
        (_REPO_ROOT / "apps" / "workspace" / "tools_app" / "manifests").glob("*.json")
    )
    links = sorted(
        (_REPO_ROOT / "apps" / "workspace" / "apps_app" / "launcher_links").glob(
            "*.json"
        )
    )
    for path in manifests + links:
        data = json.loads(path.read_text(encoding="utf-8"))
        labels[data["name"]] = data["label"]
    return labels


def test_curated_launcher_reads_infra_then_apps_then_chat_settings_tools_then_last():
    # Arrange
    labels = _manifest_labels()
    # Act
    tile_names = [labels.get(name, name) for name in DEFAULT_LAUNCHER_ORDER]
    # Assert
    assert tile_names == EXPECTED_TILE_ORDER


class GridLauncherTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.staff = User.objects.create_user(
            username="launcher-rows-staff",
            password="TestPass123!",  # pragma: allowlist secret
            is_staff=True,
        )

    def _tiles(self):
        request = RequestFactory().get("/apps/")
        request.user = self.staff
        request.session = {}
        return launcher_context(request)["tiles"]

    def test_grid_follows_the_curated_order(self):
        # Arrange
        names = [tile["name"] for tile in self._tiles()]
        # Act
        curated = sorted(names, key=default_order_value)
        # Assert
        assert names == curated

    def test_grid_names_the_projects_app_my_projects(self):
        # Arrange
        tiles = self._tiles()
        # Act
        labels = {tile["name"]: tile["label"] for tile in tiles}
        # Assert
        assert labels.get("home") == "My Projects"

    def test_mobile_menu_offers_my_projects(self):
        # Arrange
        self.client.force_login(self.staff)
        # Act
        response = self.client.get("/apps/home/")
        # Assert
        assert b"<span>My Projects</span>" in response.content


@pytest.fixture(name="compiled_catalogs")
def _compiled_catalogs():
    """Compile locale/**/*.po -> .mo (gitignored), as test_i18n_landing does."""
    script = _REPO_ROOT / "scripts" / "i18n" / "compile_catalogs.py"
    subprocess.run([sys.executable, str(script)], cwd=_REPO_ROOT, check=True)
    translation.trans_real._translations.clear()
    yield
    translation.trans_real._translations.clear()


def _tile_label(username, name):
    user = User.objects.create_user(username=username, is_staff=True)
    request = RequestFactory().get("/apps/")
    request.user = user
    request.session = {}
    tiles = launcher_context(request)["tiles"]
    return next(tile["label"] for tile in tiles if tile["name"] == name)


@pytest.mark.django_db
def test_grid_names_my_projects_in_japanese(compiled_catalogs):
    # Arrange — the grid renders {% trans tile.label context "app name" %}
    label = _tile_label("launcher-rows-ja", "home")
    # Act
    with translation.override("ja"):
        rendered = pgettext("app name", label)
    # Assert
    assert rendered == "マイプロジェクト"


@pytest.mark.django_db
def test_grid_names_public_projects_in_japanese(compiled_catalogs):
    # Arrange
    label = _tile_label("launcher-rows-ja2", "discovery")
    # Act
    with translation.override("ja"):
        rendered = pgettext("app name", label)
    # Assert
    assert rendered == "パブリックプロジェクト"


@pytest.mark.django_db
def test_grid_names_settings_in_japanese(compiled_catalogs):
    # Arrange
    label = _tile_label("launcher-rows-ja3", "settings")
    # Act
    with translation.override("ja"):
        rendered = pgettext("app name", label)
    # Assert
    assert rendered == "設定"


# EOF
