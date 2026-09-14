#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: tests/apps/apps_app/test_launcher_rows_and_my_projects.py
"""Launcher rows and the "My Projects" / "Public Projects" names.

Operator, 2026-09-14:
  * "Projects" is "My Projects" (JA 「マイプロジェクト」); the existing Explore
    app is relabelled "Public Projects" (JA 「パブリックプロジェクト」) — same
    URL, same module name.
  * Row 1 (infrastructure): My Projects, Public Projects, Agents, Cards.
  * Row 2 (research): Scholar, FigRecipe, [Stats — not an app yet], Writer.
  * Row 3 (settings / other): Tools (Console, Clew if ever shown).
  * Last row: Docs, App Store, Storage.

WHY LABELS ARE READ FROM THE MANIFEST FILES, NOT THE REGISTRY
Agents and Cards are optional plugin tiles: the registry only knows them where
their package is installed, and in CI the registry has been measured reading
order=50 for every manifest (see test_app_order_is_the_operators_order.py). The
curated list is what the grid sorts by, and the manifest files are the SSoT for
labels, so joining those two is the deterministic statement of what a user sees.
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest
from django.contrib.auth.models import User
from django.test import RequestFactory, TestCase
from django.utils import translation

from apps.workspace.apps_app.views.launcher_order import (
    DEFAULT_LAUNCHER_ORDER,
    default_order_value,
)
from config.context_processors import header_app_launcher

_REPO_ROOT = Path(__file__).resolve().parents[3]

EXPECTED_TILE_ORDER = [
    # row 1 — infrastructure
    "My Projects",
    "Public Projects",
    "Agents",
    "Cards",
    # row 2 — research (Stats slots in between FigRecipe and Writer later)
    "Scholar",
    "FigRecipe",
    "Writer",
    # row 3 — settings / other
    "Tools",
    "Console",
    "Clew",
    # last row
    "Docs",
    "App Store",
    "Storage",
]


def _manifest_labels():
    labels = {}
    for path in sorted((_REPO_ROOT / "apps" / "workspace").glob("*/manifest.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        labels[data["name"]] = data["label"]
    return labels


def test_curated_launcher_reads_infra_then_research_then_other_then_last_row():
    # Arrange
    labels = _manifest_labels()
    # Act
    tile_names = [labels.get(name, name) for name in DEFAULT_LAUNCHER_ORDER]
    # Assert
    assert tile_names == EXPECTED_TILE_ORDER


class HeaderLauncherTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.staff = User.objects.create_user(
            username="launcher-rows-staff",
            password="TestPass123!",  # pragma: allowlist secret
            is_staff=True,
        )

    def _header_apps(self):
        request = RequestFactory().get("/")
        request.user = self.staff
        return header_app_launcher(request)["header_apps"]

    def test_header_launcher_follows_the_curated_grid_order(self):
        # Arrange
        ids = [app["id"] for app in self._header_apps()]
        # Act
        curated = sorted(ids, key=default_order_value)
        # Assert
        assert ids == curated

    def test_header_launcher_names_the_projects_app_my_projects(self):
        # Arrange
        apps = self._header_apps()
        # Act
        names = {app["id"]: app["name"] for app in apps}
        # Assert
        assert names.get("home") == "My Projects"

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


@pytest.mark.django_db
def test_header_launcher_names_my_projects_in_japanese(compiled_catalogs):
    # Arrange
    user = User.objects.create_user(username="launcher-rows-ja", is_staff=True)
    request = RequestFactory().get("/")
    request.user = user
    # Act
    with translation.override("ja"):
        apps = header_app_launcher(request)["header_apps"]
    # Assert
    assert {a["id"]: a["name"] for a in apps}.get("home") == "マイプロジェクト"


@pytest.mark.django_db
def test_header_launcher_names_public_projects_in_japanese(compiled_catalogs):
    # Arrange
    user = User.objects.create_user(username="launcher-rows-ja2", is_staff=True)
    request = RequestFactory().get("/")
    request.user = user
    # Act
    with translation.override("ja"):
        apps = header_app_launcher(request)["header_apps"]
    # Assert
    assert {a["id"]: a["name"] for a in apps}.get("discovery") == "パブリックプロジェクト"


# EOF
