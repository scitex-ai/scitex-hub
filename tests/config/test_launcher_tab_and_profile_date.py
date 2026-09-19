#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The Home launcher tab names no project; the JA profile date reads naturally.

Site walkthrough 2026-09-14: /apps/ showed the last-opened project ("dotfiles")
in its tab, and the profile said "9月 2026 から利用" instead of "2026年9月から利用".
"""

from __future__ import annotations

import datetime
import re
import subprocess
import sys
from pathlib import Path

import pytest
from django.contrib.auth.models import User
from django.test import Client, override_settings
from django.urls import reverse
from django.utils import timezone, translation

from apps.infra.project_app.templatetags import branding_tags
from config import branding

from ._branding_helpers import FakeRequest

PROJECT_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module", autouse=True)
def compiled_catalogs():
    """*.mo is gitignored; compile the real .po the same way the image does."""
    subprocess.run(
        [sys.executable, str(PROJECT_ROOT / "scripts" / "i18n" / "compile_catalogs.py")],
        cwd=PROJECT_ROOT,
        capture_output=True,
        check=True,
    )
    translation.trans_real._translations.clear()
    yield


class _LastUsedProject:
    name = "dotfiles"
    slug = "dotfiles"


def _launcher_context():
    return {"request": FakeRequest("/apps/"), "current_project": _LastUsedProject()}


@override_settings(SCITEX_ENV="production", SCITEX_APP_MODE=branding.MODE_HUB)
def test_launcher_tab_is_home_even_with_a_last_used_project():
    # Arrange
    context = _launcher_context()
    # Act
    with translation.override("en"):
        title = branding_tags.page_title(context)
    # Assert
    assert title == "Home — SciTeX™"


@override_settings(SCITEX_ENV="production", SCITEX_APP_MODE=branding.MODE_HUB)
def test_launcher_tab_never_contains_the_last_used_project_name():
    # Arrange
    context = _launcher_context()
    # Act
    with translation.override("en"):
        title = branding_tags.page_title(context)
    # Assert
    assert "dotfiles" not in title


@override_settings(SCITEX_ENV="production", SCITEX_APP_MODE=branding.MODE_HUB)
def test_launcher_tab_is_translated_to_japanese():
    # Arrange
    context = _launcher_context()
    # Act
    with translation.override("ja"):
        title = branding_tags.page_title(context)
    # Assert
    assert title == "ホーム — SciTeX™"


def test_an_app_under_apps_keeps_its_own_tab_name():
    # Arrange
    path = "/apps/writer/"
    # Act
    label = branding.app_for_path(path)
    # Assert
    assert label == "Writer"


@pytest.mark.django_db
@override_settings(SCITEX_ENV="production", SCITEX_APP_MODE=branding.MODE_HUB)
def test_rendered_launcher_page_title_is_home():
    # Arrange
    user = User.objects.create_user(username="launcher-title-user", password="pw-unused-123")
    client = Client(HTTP_ACCEPT_LANGUAGE="en")
    client.force_login(user)
    # Act
    html = client.get("/apps/").content.decode()
    # Assert
    assert re.search(r"<title>\s*Home — SciTeX™\s*</title>", html)


def _profile_html(language):
    user = User.objects.create_user(username=f"joined-{language}", password="pw-unused-123")
    user.date_joined = timezone.make_aware(datetime.datetime(2026, 9, 3, 12, 0))
    user.save(update_fields=["date_joined"])
    client = Client(HTTP_ACCEPT_LANGUAGE=language)
    client.force_login(user)
    client.cookies["django_language"] = language
    return client.get(reverse("accounts_app:profile")).content.decode()


@pytest.mark.django_db
def test_japanese_profile_date_reads_year_then_month():
    # Arrange
    language = "ja"
    # Act
    html = _profile_html(language)
    # Assert
    assert "2026年9月から利用" in html


@pytest.mark.django_db
def test_english_profile_date_spells_the_month():
    # Arrange
    language = "en"
    # Act
    html = _profile_html(language)
    # Assert
    assert "Member since September 2026" in html
