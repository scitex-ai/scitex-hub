#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Account Settings -> Project Health: the client-rendered list is bilingual.

The list, dialogs and error messages on this page are built in TypeScript, so
translating the template alone left them English under Japanese. The view now
ships a string catalog via ``json_script:"project-health-i18n"`` that the TS
helper ``t(key, fallbackEnglish)`` reads. These tests render the real page
under en and ja and read that catalog back out of the HTML.

The .mo catalogs are gitignored, so the module fixture compiles them with the
project's babel-based script (same as tests/config/test_i18n_*.py).
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import pytest
from django.conf import settings
from django.test import Client
from django.urls import reverse
from django.utils import translation

PROJECT_ROOT = Path(__file__).resolve().parents[4]
CATALOG_ID = "project-health-i18n"

_JAPANESE = re.compile(r"[぀-ヿ㐀-鿿＀-￯]")
_CATALOG_SCRIPT = re.compile(
    r'<script id="%s" type="application/json">(.*?)</script>' % CATALOG_ID, re.S
)


@pytest.fixture(scope="module", autouse=True)
def compiled_catalogs():
    """Compile locale/**/*.po -> .mo so the ja render reads the real catalog."""
    script = PROJECT_ROOT / "scripts" / "i18n" / "compile_catalogs.py"
    result = subprocess.run(
        [sys.executable, str(script)], cwd=PROJECT_ROOT, capture_output=True, text=True
    )
    assert result.returncode == 0, result.stdout + result.stderr
    translation.trans_real._translations.clear()
    yield


@pytest.fixture
def signed_in_client(django_user_model):
    user = django_user_model.objects.create_user(
        username="project-health-i18n",
        email="project-health-i18n@example.com",
        password="x-Pass-12345",
    )
    client = Client()
    client.force_login(user)
    return client


def _catalog(client, language):
    client.cookies[settings.LANGUAGE_COOKIE_NAME] = language
    html = client.get(reverse("accounts_app:repository_health")).content.decode()
    match = _CATALOG_SCRIPT.search(html)
    return json.loads(match.group(1)) if match else {}


@pytest.mark.django_db
def test_catalog_under_english_carries_english_value(signed_in_client):
    # Arrange
    key = "error.sync"
    # Act
    catalog = _catalog(signed_in_client, "en")
    # Assert
    assert catalog.get(key) == "Failed to sync project", catalog


@pytest.mark.django_db
def test_catalog_under_japanese_carries_japanese_value(signed_in_client):
    # Arrange
    key = "error.sync"
    # Act
    catalog = _catalog(signed_in_client, "ja")
    # Assert
    assert catalog.get(key) == "プロジェクトを同期できませんでした", catalog


@pytest.mark.django_db
def test_catalog_under_japanese_has_every_value_translated(signed_in_client):
    # Arrange
    # Brand names stay as they are; every string still needs Japanese text.
    # Act
    catalog = _catalog(signed_in_client, "ja")
    # Assert
    untranslated = {k: v for k, v in catalog.items() if not _JAPANESE.search(v)}
    assert catalog and not untranslated, untranslated


@pytest.mark.django_db
def test_catalog_under_english_has_no_japanese(signed_in_client):
    # Arrange
    # Act
    catalog = _catalog(signed_in_client, "en")
    # Assert
    japanese = {k: v for k, v in catalog.items() if _JAPANESE.search(v)}
    assert catalog and not japanese, japanese


@pytest.mark.django_db
def test_catalog_under_english_says_project_not_repositories(signed_in_client):
    # Arrange
    # "Repository" stays only where it literally means a git repository; the
    # plural "Repositories" never names the user's projects.
    # Act
    catalog = _catalog(signed_in_client, "en")
    # Assert
    assert catalog.get("action.sync") == "Sync Project" and not any(
        "Repositories" in v for v in catalog.values()
    ), catalog
