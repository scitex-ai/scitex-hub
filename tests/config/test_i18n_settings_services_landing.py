#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: tests/config/test_i18n_settings_services_landing.py
"""English default, complete Japanese: Account Settings, /services/, landing note.

Operator directive 2026-09-14: 「英語がデフォルト、日本語訳を用意」 — no page
may mix English and Japanese. A live audit found three surfaces that did:

1. Account Settings — under ja the nav still read "PERSONAL / Profile /
   INTEGRATIONS / Git platforms / … / REPOSITORIES / Repository Health", and
   the billing page told users "Card payment is not configured on this
   deployment" (an operator-facing sentence) instead of a user-facing one.
2. /services/ — the section kickers "Plans / Services / Principles / Pricing /
   Contact" and the hero panel title stayed English under ja.
3. Landing pricing note — built from fragments, so ja rendered
   「詳細は 料金ページ 、 services , plus the 特定商取引法に基づく表記 をご覧ください。
   (tax included)」 and en left "(tax included)" dangling after the sentence.

Every ja assertion is paired with an en control. Django returns the msgid for a
missing translation, so "the ja page has no English" alone would also pass for
a page that rendered nothing; the en control proves the spot really renders.

The .mo catalogs are gitignored, so the module fixture compiles them with the
project's babel-based script (msgfmt is absent from the prod image).
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest
from django.conf import settings
from django.template.loader import render_to_string
from django.test import Client, RequestFactory, override_settings
from django.urls import reverse
from django.utils import translation

PROJECT_ROOT = Path(__file__).resolve().parents[2]

_JAPANESE = re.compile(r"[぀-ヿ㐀-鿿＀-￯]")
_LATIN_WORD = re.compile(r"[A-Za-z]{2,}")
_COMMENT = re.compile(r"<!--.*?-->", re.S)
_NON_TEXT = re.compile(r"<(script|style)\b.*?</\1>", re.S | re.I)
_TAG = re.compile(r"<[^>]+>")
_WS = re.compile(r"\s+")

NAV_TEMPLATE = "accounts_app/partials/settings_nav.html"
LANDING_PRICING_TEMPLATE = "public_app/landing_partials/landing_pricing.html"

# The nav labels the audit saw in English under ja.
NAV_ENGLISH_LABELS = [
    "Personal",
    "Profile",
    "Integrations",
    "Git platforms",
    "AI providers",
    "Authentication",
    "SSH keys",
    "Billing",
    "Repositories",
    "Repository Health",
]

# /services/ section labels the audit saw in English under ja.
SERVICES_ENGLISH_LABELS = [
    "Plans",
    "Services",
    "Principles",
    "Pricing",
    "Contact",
    "From fragmented work to reproducible workflow",
]

# Settings pages whose <h1> must follow the active language.
SETTINGS_URL_NAMES = [
    "accounts_app:profile_edit",
    "accounts_app:appearance",
    "accounts_app:privacy_settings",
    "accounts_app:git_integrations",
    "accounts_app:ai_providers",
    "accounts_app:mcp_tools",
    "accounts_app:ssh_keys",
    "accounts_app:api_keys",
    "accounts_app:repository_health",
    "accounts_app:billing",
]


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


def _visible_text(html):
    html = _COMMENT.sub(" ", html)
    html = _NON_TEXT.sub(" ", html)
    html = _TAG.sub(" ", html)
    return _WS.sub(" ", html).strip()


def _nav_text(language):
    request = RequestFactory().get("/accounts/settings/profile/")
    from django.contrib.auth.models import AnonymousUser

    request.user = AnonymousUser()
    with translation.override(language):
        html = render_to_string(NAV_TEMPLATE, {"request": request, "active": "profile"})
    return _visible_text(html)


def _nav_labels(language):
    """Each nav header / item label as its own string, so "Profile" does not
    match inside "Public profile"."""
    request = RequestFactory().get("/accounts/settings/profile/")
    from django.contrib.auth.models import AnonymousUser

    request.user = AnonymousUser()
    with translation.override(language):
        html = render_to_string(NAV_TEMPLATE, {"request": request, "active": "profile"})
    headers = re.findall(r'class="settings-nav-header">(.*?)</div>', html, re.S)
    items = re.findall(r"<span>(.*?)</span>", html, re.S)
    return [_WS.sub(" ", label).strip() for label in headers + items]


def _get(client, path, language):
    client.cookies[settings.LANGUAGE_COOKIE_NAME] = language
    return client.get(path).content.decode()


def _main_content(html):
    match = re.search(r'<main class="settings-content">(.*?)</main>', html, re.S)
    return match.group(1) if match else ""


def _settings_title(html):
    match = re.search(r'<h1 class="settings-title">(.*?)</h1>', html, re.S)
    return _visible_text(match.group(1)) if match else ""


def _services_labels(html):
    kickers = re.findall(r'<p class="svc-kicker">(.*?)</p>', html, re.S)
    panel = re.findall(r'<p class="svc-panel-title">(.*?)</p>', html, re.S)
    return [_visible_text(label) for label in kickers + panel]


def _landing_note(language):
    with translation.override(language):
        html = render_to_string(LANDING_PRICING_TEMPLATE, {})
    match = re.search(r'<div class="pricing-notes">(.*?)</div>', html, re.S)
    # Inline <a> tags sit inside the sentence, so drop them without a space.
    return _WS.sub(" ", _TAG.sub("", _COMMENT.sub("", match.group(1)))).strip() if match else ""


@pytest.fixture
def signed_in_client(django_user_model):
    user = django_user_model.objects.create_user(
        username="i18n-settings-user", email="i18n-settings@example.com", password="x-Pass-12345"
    )
    client = Client()
    client.force_login(user)
    return client


# ---------------------------------------------------------------------------
# 1. Account Settings
# ---------------------------------------------------------------------------
def test_settings_nav_under_japanese_shows_no_english_labels():
    # Arrange
    english_labels = set(NAV_ENGLISH_LABELS)
    # Act
    labels = _nav_labels("ja")
    # Assert
    assert english_labels.isdisjoint(labels), f"English under ja: {english_labels & set(labels)}"


def test_settings_nav_under_english_says_projects_and_has_no_japanese():
    # Arrange
    expected = {"Projects", "Project Health"}
    # Act
    labels = _nav_labels("en")
    # Assert
    assert (
        expected <= set(labels)
        and not any("Repositor" in label for label in labels)
        and not _JAPANESE.search(_nav_text("en"))
    ), labels


@pytest.mark.django_db
@override_settings(STRIPE_SECRET_KEY="")
def test_billing_unavailable_under_english_points_users_to_contact(signed_in_client):
    # Arrange
    contact_href = 'href="%s"' % reverse("public_app:contact")
    # Act
    main = _main_content(_get(signed_in_client, reverse("accounts_app:billing"), "en"))
    # Assert
    assert contact_href in main and "not configured on this deployment" not in main, main


@pytest.mark.django_db
@override_settings(STRIPE_SECRET_KEY="")
def test_billing_unavailable_under_japanese_has_no_english_sentences(signed_in_client):
    # Arrange — brand names are the same in both languages.
    brands = re.compile(r"\b(Stripe|SciTeX)\b")
    # Act
    text = _visible_text(_main_content(_get(signed_in_client, reverse("accounts_app:billing"), "ja")))
    # Assert
    assert _JAPANESE.search(text) and not _LATIN_WORD.search(brands.sub("", text)), text


@pytest.mark.django_db
@pytest.mark.parametrize("url_name", SETTINGS_URL_NAMES)
def test_settings_page_title_follows_active_language(signed_in_client, url_name):
    # Arrange
    english_title = _settings_title(_get(signed_in_client, reverse(url_name), "en"))
    # Act
    japanese_title = _settings_title(_get(signed_in_client, reverse(url_name), "ja"))
    # Assert
    assert english_title and _JAPANESE.search(japanese_title), (english_title, japanese_title)


# ---------------------------------------------------------------------------
# 2. /services/
# ---------------------------------------------------------------------------
@pytest.mark.django_db
def test_services_section_labels_under_japanese_are_translated():
    # Arrange
    english_labels = set(SERVICES_ENGLISH_LABELS)
    # Act
    labels = _services_labels(_get(Client(), reverse("public_app:services"), "ja"))
    # Assert
    assert labels and english_labels.isdisjoint(labels), labels


@pytest.mark.django_db
def test_services_section_labels_under_english_are_english():
    # Arrange
    expected = SERVICES_ENGLISH_LABELS
    # Act
    labels = _services_labels(_get(Client(), reverse("public_app:services"), "en"))
    # Assert
    assert labels == expected, labels


# ---------------------------------------------------------------------------
# 3. Landing pricing note
# ---------------------------------------------------------------------------
def test_landing_pricing_note_under_japanese_has_no_english_fragments():
    # Arrange
    language = "ja"
    # Act
    note = _landing_note(language)
    # Assert
    assert _JAPANESE.search(note) and not _LATIN_WORD.search(note), note


def test_landing_pricing_note_under_english_is_whole_sentences():
    # Arrange
    expected = (
        "For details, see the pricing page, the services page, and the legal notice "
        "under Japan's Specified Commercial Transactions Act. All displayed prices include tax."
    )
    # Act
    note = _landing_note("en")
    # Assert
    assert note == expected, note
