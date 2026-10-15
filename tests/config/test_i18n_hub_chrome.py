#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: tests/config/test_i18n_hub_chrome.py
"""Hub-chrome i18n fill (owner ask 2026-09-27): every hub-owned surface renders
EN+JA behind the EN|JA switcher.

Scope is hub chrome ONLY — landing, launcher, nav, dock, footer, auth,
App Store. Leaf-app content (Scholar/Cards/Storage/Agents/…) is DEFERRED and
has no tests here.

WHY PAIRED CHECKS
-----------------
Django resolves a missing translation by returning the msgid — the English
source string. So EVERY failure mode here is silent: a template that lost its
{% trans %}, a catalog entry that was never added, a .mo that was never
compiled. Each Japanese assertion is therefore paired with its
English-under-en control: the pair proves the RENDER is language-sensitive
rather than the fixture being.

WHY THE FIXTURE COMPILES
------------------------
`*.mo` is gitignored, so a fresh checkout has catalogs in source form only.
These tests compile them in-process (the project's own
scripts/i18n/compile_catalogs.py — msgfmt is absent from the image) so they
exercise the real .po content rather than a stale artifact.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest
from django.template.loader import render_to_string
from django.test import Client
from django.utils import translation

PROJECT_ROOT = Path(__file__).resolve().parents[2]
MODAL_TEMPLATE = "global_base_partials/auth_required_modal.html"
MODULES_TEMPLATE = "public_app/landing_partials/landing_modules.html"


@pytest.fixture(scope="module", autouse=True)
def compiled_catalogs():
    """Compile locale/**/*.po -> .mo before any assertion reads a catalog."""
    script = PROJECT_ROOT / "scripts" / "i18n" / "compile_catalogs.py"
    result = subprocess.run(
        [sys.executable, str(script)],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"catalog compilation failed ({result.returncode}):\n"
        f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )
    # Django caches translation objects per language; anything loaded before
    # the .mo existed would be an empty catalog that never reloads.
    translation.trans_real._translations.clear()
    yield


# (msgid, japanese) — one string per hub-chrome surface, no duplicates.
CHROME_CASES = [
    # Launcher.
    ("Active project", "アクティブなプロジェクト"),
    ("Favorites", "お気に入り"),
    ("All apps", "すべてのアプリ"),
    # Nav / header.
    ("Help", "ヘルプ"),
    ("Close", "閉じる"),
    ("All", "すべて"),
    # App Store.
    ("App Store", "アプリストア"),
    ("Popular", "人気順"),
    ("Newest", "新しい順"),
    ("My Apps", "マイアプリ"),
    ("Review Queue", "レビューキュー"),
    ("Coming Soon", "近日公開"),
    ("No apps found", "アプリが見つかりません"),
    ("Search apps", "アプリを検索"),
    ("Install", "インストール"),
    # Auth.
    ("Sign in", "ログイン"),
    ("Sign up", "新規登録"),
    ("Logout", "ログアウト"),
    ("Confirm Password", "パスワード（確認）"),
    ("Delete Account", "アカウントの削除"),
    ("Forgot Password", "パスワードをお忘れの方"),
    ("Reset Password", "パスワードの再設定"),
    ("Verify Email", "メールを確認"),
    ("Email Address", "メールアドレス"),
    # Footer dev tools.
    ("Dev Tools:", "開発ツール:"),
    ("Clear Cache", "キャッシュをクリア"),
    # Landing SDK section.
    ("Create your own app with the SDK.", "SDKで独自アプリを作る。"),
    ("Start building", "開発を始める"),
    # Pricing storage tiers.
    ("Hot", "ホット"),
    ("Warm", "ウォーム"),
    ("Cool", "クール"),
    ("Cold", "コールド"),
    # Landing demo stat rows (features/* partials).
    ("research modules, batteries included", "研究モジュール40種以上、全部入り"),
    ("one context from phone to HPC", "スマホからHPCまでひとつのコンテキスト"),
    ("academic works searchable locally", "学術文献をローカルで検索可能"),
    ("figure layout designed for journals", "学術誌向けの図版レイアウト"),
    ("LaTeX compile with live PDF preview", "LaTeXをコンパイルしてPDFをライブプレビュー"),
    ("Real-time", "リアルタイム"),
    ("mm-precise", "ミリ単位の精度"),
    ("1 project", "1つのプロジェクト"),
]

# (msgctxt, msgid, japanese) — same source word, different surfaces.
CHROME_CONTEXT_CASES = [
    ("store section", "About", "概要"),
    ("store action", "Publish", "公開する"),
    ("sort option", "Rating", "評価順"),
]


@pytest.mark.parametrize(("msgid", "japanese"), CHROME_CASES, ids=str)
def test_chrome_catalog_translates_under_japanese(msgid, japanese):
    # Arrange
    expected = japanese
    # Act
    with translation.override("ja"):
        actual = translation.gettext(msgid)
    # Assert
    assert actual == expected, f"msgid {msgid!r} has no JA entry"


@pytest.mark.parametrize(("msgid", "japanese"), CHROME_CASES, ids=str)
def test_chrome_catalog_leaves_english_alone(msgid, japanese):
    """Control — proves the JA result above comes from the catalog."""
    # Arrange
    expected = msgid
    # Act
    with translation.override("en"):
        actual = translation.gettext(msgid)
    # Assert
    assert actual == expected


@pytest.mark.parametrize(("ctx", "msgid", "japanese"), CHROME_CONTEXT_CASES, ids=str)
def test_chrome_context_catalog_translates_under_japanese(ctx, msgid, japanese):
    # Arrange
    expected = japanese
    # Act
    with translation.override("ja"):
        actual = translation.pgettext(ctx, msgid)
    # Assert
    assert actual == expected, f"({ctx!r}, {msgid!r}) has no JA entry"


@pytest.mark.parametrize(("ctx", "msgid", "japanese"), CHROME_CONTEXT_CASES, ids=str)
def test_chrome_context_catalog_leaves_english_alone(ctx, msgid, japanese):
    """Control — proves the JA result above comes from the catalog."""
    # Arrange
    expected = msgid
    # Act
    with translation.override("en"):
        actual = translation.pgettext(ctx, msgid)
    # Assert
    assert actual == expected


# ---------------------------------------------------------------------------
# The auth modal renders in the selected language (context-free partial)
# ---------------------------------------------------------------------------
def test_auth_modal_renders_japanese():
    # Arrange
    expected = "ログインが必要です"
    # Act
    with translation.override("ja"):
        html = render_to_string(MODAL_TEMPLATE, {})
    # Assert
    assert expected in html


def test_auth_modal_renders_english():
    """Control: the same partial, the other language."""
    # Arrange
    expected = "Sign In Required"
    # Act
    with translation.override("en"):
        html = render_to_string(MODAL_TEMPLATE, {})
    # Assert
    assert expected in html


def test_auth_modal_leaves_no_untranslated_english():
    """Catches a {% trans %} dropped during an edit."""
    # Arrange
    forbidden = "This feature requires authentication."
    # Act
    with translation.override("ja"):
        html = render_to_string(MODAL_TEMPLATE, {})
    # Assert
    assert forbidden not in html


# ---------------------------------------------------------------------------
# The landing SDK section renders in the selected language
# ---------------------------------------------------------------------------
def test_modules_sdk_renders_japanese():
    # Arrange
    expected = "SDKで独自アプリを作る。"
    # Act
    with translation.override("ja"):
        html = render_to_string(MODULES_TEMPLATE, {})
    # Assert
    assert expected in html


def test_modules_sdk_renders_english():
    """Control: the same partial, the other language."""
    # Arrange
    expected = "Create your own app with the SDK."
    # Act
    with translation.override("en"):
        html = render_to_string(MODULES_TEMPLATE, {})
    # Assert
    assert expected in html


# ---------------------------------------------------------------------------
# The storage-tier meaning reaches the JA landing (pricing.py _(meaning) fix)
# ---------------------------------------------------------------------------
TIER_MEANING_JA = "利用中のデータセット向けの高速な永続ストレージ"
TIER_MEANING_EN = "High-speed persistent storage for active datasets"


def _landing(client_cookie=None):
    from django.test import Client

    c = Client()
    if client_cookie:
        c.cookies["django_language"] = client_cookie
    return c.get("/landing/", HTTP_ACCEPT_LANGUAGE="ja-JP,ja;q=0.9,en;q=0.5").content.decode(
        "utf-8", "replace"
    )


def test_landing_tier_meaning_renders_japanese_when_selected():
    """tier_label() translates the pricing.json meaning — without _(meaning)
    the JA table falls back to English for the one line with no cell."""
    # Arrange
    expected = TIER_MEANING_JA
    # Act
    html = _landing(client_cookie="ja")
    # Assert
    assert expected in html


def test_landing_tier_meaning_leaves_no_english_when_selected():
    # Arrange
    forbidden = TIER_MEANING_EN
    # Act
    html = _landing(client_cookie="ja")
    # Assert
    assert forbidden not in html


def test_landing_tier_meaning_renders_english_by_default():
    """Control: the default landing stays English for the same row."""
    # Arrange
    expected = TIER_MEANING_EN
    # Act
    html = _landing()
    # Assert
    assert expected in html
