"""Rendered policy guard for the landing-page signup funnel.

POLICY CHANGE, lead decision 2026-09-30 (Free-on-Cool STANDS): the Free tier
needs NO card (pricing.json: subscription-free has no_card_required=true with
2 GB Cool included_storage), and the landing pricing card is the unified
compare-plans table (operator-authored commit 662f236fc): four columns
(SciTeX™ Cloud Free / SciTeX™ Cloud Pro, recommended / SciTeX™ Self-Hosted
AGPL / Enterprise), one CTA per column, Pro recommended, academic pricing
in-cell — never a hand-written copy. The card therefore shows generic signup
CTAs ("Create a free account", "Start with Pro") and NO card-required copy:
live render shows 'Create a free account'x1, 'Card required'x0.

The previous policy pinned here (Cloud 30-day-trial funnel entry, "Card
required at signup", Free pane dropped) contradicted the SSoT and is retired.
The /auth/signup/ half of this guard moved to
tests/apps/public_app/test_card_required_copy.py, which renders the real page
through the real URLconf (the old version patched allauth's provider list).

These tests render the complete landing page in both supported languages;
source-word checks alone previously blessed contradictory copy hidden in an
included pricing partial.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest
from django.contrib.auth.models import AnonymousUser
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.test import RequestFactory, override_settings
from django.urls import include, path
from django.utils import translation

from apps.infra.public_app.pricing import (
    load_pricing,
    published_price_rows,
)

REPO = Path(__file__).resolve().parents[2]

EXPECTED_UNIFIED_TABLE = {
    # Unified compare-plans table (operator 662f236fc): four columns —
    # SciTeX™ Cloud Free / SciTeX™ Cloud Pro (recommended) / SciTeX™
    # Self-Hosted AGPL / Enterprise — one CTA per column, academic pricing
    # in the Pro price cell, Free-on-Cool storage (Free 2 GB, Pro 32 GB).
    # Prices are USD (always) on the marketing card; JPY lives on /tokushoho/.
    "en": (
        "SciTeX™ Cloud Free",
        "SciTeX™ Cloud Pro",
        "Recommended",
        "Create a free account",
        "Start with Pro",
        "Get the source",
        "Contact us",
        "$39/mo",
        "$19/mo",
        "academic (50% off)",
        "2 GB included",
        "32 GB included",
    ),
    "ja": (
        "SciTeX™ Cloud Free",
        "SciTeX™ Cloud Pro",
        "おすすめ",
        "無料アカウントを作成",
        "Pro で始める",
        "ソースを取得",
        "お問い合わせ",
        "無料",
        "$39/mo",
        "$19/mo",
        "アカデミック (50% オフ)",
        "2 GB 込み",
        "32 GB 込み",
    ),
}

EXPECTED_FREE_SIGNUP_CTA = {
    "en": "Create a free account",
    "ja": "無料アカウントを作成",
}

# No card-required copy anywhere on the landing (Free needs no card).
CARD_REQUIRED_NEEDLE = "Card required"

# Copy that demanded a card at signup. Retired 2026-09-30 (Free-on-Cool).
RETIRED_CARD_REQUIRED_COPY = (
    "Card required at signup",
    "no charge during the trial",
    "Start your 30-day trial",
    "登録時にカードの登録が必要です",
    "トライアル期間中は課金されません",
)


def _empty_response(_request, **_kwargs):
    return HttpResponse()


# Minimal URL contract for whole-template rendering without importing optional
# workspace packages. Reversal is presentation plumbing, not this policy.
# ("open_source": the landing open-source section links it since #1007.)
_PUBLIC_NAMES = (
    "about",
    "api_docs",
    "contact",
    "contributors",
    "cookies",
    "demos",
    "donate",
    "open_source",
    "pricing",
    "privacy",
    "publications",
    "recruit",
    "releases",
    "server_status",
    "services",
    "setup",
    "terms",
    "tokushoho",
    "tokushoho_en",
)
urlpatterns = [
    path("i18n/setlang/", _empty_response, name="set_language"),
    # The global header's search palette reverses this for its data-endpoint.
    path("api/search/", _empty_response, name="api_header_search"),
    path(
        "auth/",
        include(
            (
                [
                    path("signup/", _empty_response, name="signup"),
                    path("login/", _empty_response, name="signin"),
                ],
                "auth_app",
            ),
            namespace="auth_app",
        ),
    ),
    path(
        "public/",
        include(
            (
                [
                    path(f"{name}/", _empty_response, name=name)
                    for name in _PUBLIC_NAMES
                ],
                "public_app",
            ),
            namespace="public_app",
        ),
    ),
    path(
        "accounts/",
        include(
            ([path("profile/", _empty_response, name="profile_edit")], "accounts_app"),
            namespace="accounts_app",
        ),
    ),
    path(
        "dev/",
        include(
            (
                [
                    path("design/", _empty_response, name="design"),
                    path(
                        "tests/<str:category>/", _empty_response, name="tests_category"
                    ),
                ],
                "dev_app",
            ),
            namespace="dev_app",
        ),
    ),
]


@pytest.fixture(scope="module", autouse=True)
def compiled_catalogs():
    result = subprocess.run(
        [sys.executable, str(REPO / "scripts/i18n/compile_catalogs.py")],
        cwd=REPO,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    translation.trans_real._translations.clear()


def _request(path: str):
    request = RequestFactory().get(path)
    request.user = AnonymousUser()
    request.session = {}
    return request


@override_settings(ROOT_URLCONF=__name__)
def _rendered_landing(language: str) -> str:
    # The context must be built INSIDE the override: published_price_rows()
    # localizes price/price_note/included/storage at CALL time (2026-09-11),
    # so baking it under the ambient test language would pin the wrong
    # language into the render and make the test fail (or worse, pass) for
    # reasons unrelated to what it asserts.
    from apps.infra.public_app.pricing import tier_rows
    from apps.infra.public_app.views.landing import _pricing_rows_for_landing

    pricing = load_pricing()
    request = _request("/landing/")
    with translation.override(language):
        from apps.infra.public_app.pricing import plan_comparison

        sub_rows = _pricing_rows_for_landing()
        context = {
            "sub_rows": sub_rows,
            "onprem_tier": next(
                (t for t in tier_rows() if t["id"] == "selfhosted"), None
            ),
            "tax_note": pricing.get("tax_note", ""),
            "pricing_notes": pricing["notes"],
            # Unified compare-plans table (662f236fc): the pricing partial
            # renders plan_comparison, never sub_rows alone. Built INSIDE
            # the override like published_price_rows() — it localizes every
            # cell at CALL time.
            "plan_comparison": plan_comparison(),
        }
        return render_to_string("public_app/landing.html", context, request=request)


def _visible_text(html: str) -> str:
    html = re.sub(r"<!--.*?-->|<(script|style)\b.*?</\1>", " ", html, flags=re.S | re.I)
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html)).strip()


def _section(html: str, section_id: str) -> str:
    match = re.search(
        rf'<section\b[^>]*id="{re.escape(section_id)}".*?</section>', html, re.S
    )
    assert match, f"rendered landing has no {section_id!r} section"
    return match.group()


@pytest.mark.parametrize("language", ["en", "ja"])
def test_complete_landing_keeps_the_unified_table_visible(language):
    """Deletion-sensitive: columns, CTAs, prices, and storage must exist."""
    # Arrange
    expected = EXPECTED_UNIFIED_TABLE[language]
    # Act
    visible = _visible_text(_rendered_landing(language))
    # Assert
    assert [value for value in expected if value not in visible] == []


@pytest.mark.parametrize("language", ["en", "ja"])
def test_landing_pricing_states_no_card_requirement(language):
    # Arrange: the Free column CTA is a generic signup, and no card-required
    # copy may appear anywhere on the page (Free needs no card).
    expected = EXPECTED_FREE_SIGNUP_CTA[language]
    # Act
    pricing = _visible_text(_section(_rendered_landing(language), "pricing"))
    whole = _visible_text(_rendered_landing(language))
    # Assert
    assert expected in pricing
    assert CARD_REQUIRED_NEEDLE not in whole


@pytest.mark.parametrize("language", ["en", "ja"])
def test_landing_pricing_drops_the_card_required_copy(language):
    # Arrange
    retired = RETIRED_CARD_REQUIRED_COPY
    # Act
    visible = _visible_text(_section(_rendered_landing(language), "pricing"))
    # Assert
    assert [term for term in retired if term in visible] == []


def test_pricing_ctas_are_generic_signup_not_paid_activation():
    # Arrange: the unified table carries one CTA per column; both Cloud CTAs
    # (Free "Create a free account", Pro "Start with Pro") are the generic
    # /auth/signup/, never a paid-activation or trial-start URL.
    pattern = r'<a href="([^"]+)"[^>]*class="btn[^"]*btn-block">'
    # Act
    section = _section(_rendered_landing("en"), "pricing")
    hrefs = re.findall(pattern, section)
    visible = _visible_text(section)
    # Assert
    assert hrefs.count("/auth/signup/") == 2
    assert "Create a free account" in visible
    assert "Start with Pro" in visible


@pytest.mark.parametrize(
    ("language", "expected", "forbidden"),
    [
        ("en", "32 GB Cool storage included", "ストレージ"),
        ("ja", "Cool ストレージ 32 GB 込み", "storage"),
    ],
)
def test_runtime_pricing_values_follow_the_active_language(
    language, expected, forbidden
):
    """Call-time localization in published_price_rows() (2026-09-11)."""
    # Arrange
    row_id = "subscription-student"
    # Act
    with translation.override(language):
        rendered = [
            row["storage"] for row in published_price_rows() if row["id"] == row_id
        ][0]
    # Assert
    assert (rendered == expected, forbidden in rendered) == (True, False)


def test_english_pricing_has_no_japanese_literals():
    # Arrange
    japanese = re.compile(r"[぀-ヿ㐀-鿿]")
    # Act
    pricing = _visible_text(_section(_rendered_landing("en"), "pricing"))
    # Assert
    assert japanese.search(pricing) is None


def test_japanese_landing_renders_the_japanese_pricing_strings():
    """The JA landing shows the Japanese renderings of the EN-source SSoT."""
    # Arrange
    expected = (
        "おすすめ",
        "無料アカウントを作成",
        "Pro で始める",
        "ソースを取得",
        "お問い合わせ",
        "$19/mo",
        "アカデミック (50% オフ)",
        "2 GB 込み",
        "32 GB 込み",
        "セルフホスト",
    )
    # Act
    pricing = _visible_text(_section(_rendered_landing("ja"), "pricing"))
    # Assert
    assert [value for value in expected if value not in pricing] == []
