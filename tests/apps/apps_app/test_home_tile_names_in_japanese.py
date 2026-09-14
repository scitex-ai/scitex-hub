#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: tests/apps/apps_app/test_home_tile_names_in_japanese.py
"""Home tile names in Japanese, and how they wrap (walkthrough 2026-09-14).

  * Agents, Cards, Storage, Tools, Docs and App Store had no JA entry.
  * JA names wrapped inside a katakana run ("マイプロジェク/ト"): names now
    break only at <wbr> hints, with keep-all for Japanese.
"""

import re
import subprocess
import sys
from pathlib import Path

import pytest
from django.utils import translation
from django.utils.translation import pgettext

from apps.workspace.apps_app.templatetags.launcher_text import phrase_breaks

_REPO_ROOT = Path(__file__).resolve().parents[3]
_LAUNCHER_CSS = _REPO_ROOT / "apps/workspace/apps_app/static/apps_app/css/launcher"


@pytest.fixture(name="compiled_catalogs", scope="module")
def _compiled_catalogs():
    script = _REPO_ROOT / "scripts" / "i18n" / "compile_catalogs.py"
    subprocess.run([sys.executable, str(script)], cwd=_REPO_ROOT, check=True)
    translation.trans_real._translations.clear()
    yield
    translation.trans_real._translations.clear()


@pytest.mark.parametrize(
    ("label", "expected"),
    [
        ("Agents", "エージェント"),
        ("Cards", "カード"),
        ("Storage", "ストレージ"),
        ("Tools", "ツール"),
        ("Docs", "ドキュメント"),
        ("App Store", "アプリストア"),
    ],
)
def test_home_tile_name_is_translated_to_japanese(compiled_catalogs, label, expected):
    # Arrange
    context = "app name"
    # Act
    with translation.override("ja"):
        rendered = pgettext(context, label)
    # Assert
    assert rendered == expected


def test_public_projects_may_break_between_its_two_words():
    # Arrange
    name = "パブリックプロジェクト"
    # Act
    rendered = phrase_breaks(name)
    # Assert
    assert rendered == "パブリック<wbr>プロジェクト"


def test_my_projects_may_break_only_before_projects():
    # Arrange
    name = "マイプロジェクト"
    # Act
    rendered = phrase_breaks(name)
    # Assert
    assert rendered == "マイ<wbr>プロジェクト"


def test_english_name_is_left_as_is():
    # Arrange
    name = "App Store"
    # Act
    rendered = phrase_breaks(name)
    # Assert
    assert rendered == "App Store"


def test_tile_name_is_html_escaped():
    # Arrange
    name = "<b>x</b>"
    # Act
    rendered = phrase_breaks(name)
    # Assert
    assert rendered == "&lt;b&gt;x&lt;/b&gt;"


def test_japanese_tile_names_never_break_inside_a_word():
    # Arrange
    css = (_LAUNCHER_CSS / "grid.css").read_text("utf-8")
    # Act
    rule = re.search(r"\.launcher-tile-name:lang\(ja\)\s*\{([^}]*)\}", css)
    # Assert
    assert rule and "word-break: keep-all" in rule.group(1)
