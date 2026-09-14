#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""A credit/debit card is REQUIRED at signup — every page says so.

Operator, 2026-09-14: 「はい、カード登録必須です」. /tokushoho/ already states the
rule (「お申し込み時にメールアドレスとクレジットカード/デビットカードをご登録
いただきます」); /pricing/ and /auth/signup/ used to contradict it with "Sign up
free", "Creating an account does not start a paid subscription" and "use
SciTeX's free tier at no cost" (the Services SSOT has no free cloud tier).

Rendered through the REAL URLconf and middleware (the Django test client), in
English (the default) and Japanese (the ``django_language`` cookie).
"""

import re
import subprocess
import sys
from pathlib import Path

import pytest
from django.urls import reverse
from django.utils import translation

PROJECT_ROOT = Path(__file__).resolve().parents[3]

RETIRED_FREE_COPY = {
    "en": (
        "Sign up free",
        "free tier",
        "does not start a paid subscription",
        "does not activate this paid plan",
    ),
    "ja": (
        "無料で登録",
        "無料プラン",
        "有料のサブスクリプションは開始されません",
        "有料プランは開始されません",
    ),
}

PRICING_CARD_NOTE = {
    "en": "Card required at signup — no charge during the trial.",
    "ja": "登録時にカードの登録が必要です。トライアル期間中は課金されません。",
}

SIGNUP_CARD_NOTE = {
    "en": "Start your 30-day SciTeX Cloud trial — card required, no charge during the trial.",
    "ja": "SciTeX Cloud の30日間トライアルを開始します。カードの登録が必要で、トライアル期間中は課金されません。",
}

RETIRED_ACADEMIC_BENEFITS = (
    "Japanese Academic Benefits",
    "Priority support in Japanese",
    "Early access to new features",
    "Enhanced storage limits",
)


@pytest.fixture(scope="module", autouse=True)
def compiled_catalogs():
    """Compile locale/**/*.po -> .mo so the JA assertions read a real catalog."""
    script = PROJECT_ROOT / "scripts" / "i18n" / "compile_catalogs.py"
    result = subprocess.run(
        [sys.executable, str(script)], cwd=PROJECT_ROOT, capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr
    translation.trans_real._translations.clear()
    yield


def _visible(html: str) -> str:
    html = re.sub(r"<!--.*?-->|<(script|style)\b.*?</\1>", " ", html, flags=re.S | re.I)
    html = re.sub(r"<[^>]+>", " ", html)
    return re.sub(r"\s+", " ", html)


def _get(client, url_name: str, language: str) -> str:
    cookie = {"HTTP_COOKIE": "django_language=ja"} if language == "ja" else {}
    return client.get(reverse(url_name), **cookie).content.decode("utf-8")


@pytest.mark.django_db
@pytest.mark.parametrize("language", ["en", "ja"])
def test_pricing_page_drops_the_free_signup_copy(client, language):
    # Arrange
    retired = RETIRED_FREE_COPY[language]
    # Act
    visible = _visible(_get(client, "public_app:pricing", language))
    # Assert
    assert [term for term in retired if term in visible] == []


@pytest.mark.django_db
@pytest.mark.parametrize("language", ["en", "ja"])
def test_pricing_page_states_the_card_required_trial(client, language):
    # Arrange
    expected = PRICING_CARD_NOTE[language]
    # Act
    visible = _visible(_get(client, "public_app:pricing", language))
    # Assert
    assert expected in visible


@pytest.mark.django_db
@pytest.mark.parametrize("language", ["en", "ja"])
def test_services_page_drops_the_free_signup_copy(client, language):
    # Arrange
    retired = RETIRED_FREE_COPY[language]
    # Act
    visible = _visible(_get(client, "public_app:services", language))
    # Assert
    assert [term for term in retired if term in visible] == []


@pytest.mark.django_db
@pytest.mark.parametrize("language", ["en", "ja"])
def test_signup_page_drops_the_free_tier_copy(client, language):
    # Arrange
    retired = RETIRED_FREE_COPY[language]
    # Act
    visible = _visible(_get(client, "auth_app:signup", language))
    # Assert
    assert [term for term in retired if term in visible] == []


@pytest.mark.django_db
@pytest.mark.parametrize("language", ["en", "ja"])
def test_signup_page_states_the_card_required_trial(client, language):
    # Arrange
    expected = SIGNUP_CARD_NOTE[language]
    # Act
    visible = _visible(_get(client, "auth_app:signup", language))
    # Assert
    assert expected in visible


@pytest.mark.django_db
def test_signup_page_drops_the_unbacked_japanese_academic_benefits(client):
    """Hidden until an .ac.jp address was typed, then promised perks the SSOT lacks."""
    # Arrange
    retired = RETIRED_ACADEMIC_BENEFITS
    # Act
    html = _get(client, "auth_app:signup", "en")
    # Assert
    assert [term for term in retired if term in html] == []


@pytest.mark.django_db
def test_english_signup_translates_the_academic_email_hint(client):
    # Arrange
    japanese_source = "学術機関の例"
    # Act
    visible = _visible(_get(client, "auth_app:signup", "en"))
    # Assert
    assert (japanese_source in visible, "Academic email examples:" in visible) == (
        False,
        True,
    )


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("language", "label", "expected_href"),
    [
        ("en", "Specified Commercial Transactions Act disclosure", "/tokushoho-en/"),
        ("ja", "特定商取引法に基づく表記", "/tokushoho/"),
    ],
)
def test_pricing_disclosure_link_follows_the_active_language(
    client, language, label, expected_href
):
    # Arrange
    anchor = re.compile(rf'<a href="([^"]+)">\s*{re.escape(label)}\s*</a>')
    # Act
    hrefs = set(anchor.findall(_get(client, "public_app:pricing", language)))
    # Assert
    assert hrefs == {expected_href}
