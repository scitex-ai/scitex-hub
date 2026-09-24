#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The public price pages match "SciTeX Services SSOT — Provisional v1.0" (USD).

Operator decisions of 2026-09-14 pinned here, against the RENDERED pages:
- prices are USD (Cloud Academic $19/mo, Cloud Standard $39/mo, Self-Hosted
  Enterprise License from $2,400/year, Setup from $2,000, Maintenance from
  $650/mo, Custom Development from $1,300/project, Consulting from $65/hr) and
  32 GB Cool storage is included;
- no JPY price band, and no retired early-adopter strikethrough;
- tier names only (Hot / Warm / Cool / Cold), never an internal hardware name;
- unbuilt features (compute credit, spending cap, compute billing) carry a
  coming-soon label (EN "Coming soon", JA 「近日提供」).
"""

import re
import subprocess
import sys
from pathlib import Path

import pytest
from django.urls import reverse
from django.utils import translation

PROJECT_ROOT = Path(__file__).resolve().parents[3]

SSOT_USD_PRICES = (
    "$19/mo",
    "$39/mo",
    "from $2,400/year",
    "from $2,000",
    "from $650/mo",
    "from $1,300/project",
    "from $65/hr",
    "32 GB",
)
STORAGE_TIERS = ["Hot", "Warm", "Cool", "Cold"]
JPY_BAND = re.compile(r"¥\s?\d|\d[\d,]*\s?円|\d+\s?万円")
HARDWARE_NAME = re.compile(r"NAS-\d|NVMe", re.IGNORECASE)
JA_COMING_SOON_ITEMS = (
    "計算クレジット $10 / 請求サイクル（近日提供）",
    "月間の利用上限を利用者が設定（近日提供）",
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


def _get(client, name: str, language: str = "en") -> str:
    cookie = {"HTTP_COOKIE": "django_language=ja"} if language == "ja" else {}
    return client.get(reverse(f"public_app:{name}"), **cookie).content.decode("utf-8")


def _storage_tier_names(html: str) -> list[str]:
    table = re.search(r'data-rate-card="storage".*?</table>', html, re.S)
    if table is None:
        return []
    return re.findall(r'class="pricing-storage-tier">([^<]+)<', table.group())


@pytest.mark.django_db
@pytest.mark.parametrize("page_name", ["pricing", "services", "tokushoho_en"])
def test_page_shows_every_ssot_usd_price(client, page_name):
    # Arrange
    expected = SSOT_USD_PRICES
    # Act
    visible = _visible(_get(client, page_name))
    # Assert
    assert [price for price in expected if price not in visible] == []


@pytest.mark.django_db
@pytest.mark.parametrize("language", ["en", "ja"])
def test_services_page_shows_no_jpy_price_band(client, language):
    # Arrange
    pattern = JPY_BAND
    # Act
    visible = _visible(_get(client, "services", language))
    # Assert
    assert pattern.findall(visible) == []


@pytest.mark.django_db
@pytest.mark.parametrize("language", ["en", "ja"])
def test_pricing_page_shows_no_jpy_price_band_and_prices_the_commercial_license(
    client, language
):
    # Arrange
    commercial_price = "$2,400/year"
    # Act
    visible = _visible(_get(client, "pricing", language))
    # Assert
    assert (JPY_BAND.findall(visible), commercial_price in visible) == ([], True)


@pytest.mark.django_db
@pytest.mark.parametrize("page_name", ["tokushoho", "tokushoho_en"])
def test_tokushoho_drops_the_retired_early_adopter_strikethrough(client, page_name):
    # Arrange
    retired = ("50% OFF", "$38/mo", "$78/mo", "tokushoho-list-price")
    # Act
    html = _get(client, page_name)
    # Assert
    assert ([r for r in retired if r in html], "$2,400/year" in html) == ([], True)


@pytest.mark.django_db
@pytest.mark.parametrize("page_name", ["pricing", "services", "tokushoho", "tokushoho_en"])
def test_storage_is_described_by_tier_names_never_hardware(client, page_name):
    # Arrange
    expected = (STORAGE_TIERS, [])
    # Act
    html = _get(client, page_name)
    # Assert
    assert (_storage_tier_names(html), HARDWARE_NAME.findall(html)) == expected


@pytest.mark.django_db
def test_pricing_page_labels_unbuilt_features_coming_soon(client):
    # Arrange
    needles = (
        "$10 compute credit per billing cycle (Coming soon)",
        "Monthly spending cap set by the user (Coming soon)",
        "trial compute credit (credit: Coming soon)",
    )
    # Act
    html = _get(client, "pricing")
    compute_badge = re.search(
        r'Compute billing\s*<span class="pricing-coming-soon">Coming soon</span>', html
    )
    # Assert
    assert ([n for n in needles if n not in html], compute_badge is not None) == ([], True)


@pytest.mark.django_db
@pytest.mark.parametrize("page_name", ["services", "tokushoho"])
def test_japanese_pages_label_unbuilt_features_kinjitsu_teikyo(client, page_name):
    # Arrange
    needles = JA_COMING_SOON_ITEMS + ("計算資源の課金",)
    # Act
    html = _get(client, page_name, "ja")
    # Assert
    assert [n for n in needles if n not in html] == []
