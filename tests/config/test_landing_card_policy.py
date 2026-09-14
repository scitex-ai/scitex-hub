"""Rendered policy guard for the landing-page signup funnel.

POLICY CHANGE, operator 2026-09-14: 「はい、カード登録必須です」 — a credit/debit
card is REQUIRED at signup, as /tokushoho/ already states. The landing pricing
card therefore says so: the Cloud CTA starts the 30-day trial and the card
requirement is shown next to it. The previous policy pinned here (a free tier,
and NO card wording before a paid action) contradicted the 特商法 page and is
retired. The /auth/signup/ half of this guard moved to
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

EXPECTED_TRIAL_FUNNEL = {
    # Two-plan landing row (operator 2026-09-12): the Free pane is DROPPED —
    # Cloud's 30-day free trial is the funnel entry. Cloud (Academic/Non-Academic
    # switcher) + Self-Hosted. The Cloud price + a feature line prove the paid
    # plans render from the SSoT in the active language. Prices are USD
    # (always) on the marketing card; JPY lives on /tokushoho/.
    "en": (
        "Cloud",
        "30-day free trial",
        "Start your 30-day trial",
        "$19/mo",
        "32 GB Cool storage included",
    ),
    "ja": (
        "クラウド",
        "30日間の無料トライアル",
        "30日間のトライアルを開始",
        "$19/mo",
        "Cool ストレージ 32 GB 込み",
    ),
}

EXPECTED_LANDING_CARD_NOTE = {
    "en": "Card required at signup — no charge during the trial.",
    "ja": "登録時にカードの登録が必要です。トライアル期間中は課金されません。",
}

# Copy that promised a free, card-less signup. Retired 2026-09-14.
RETIRED_FREE_SIGNUP_COPY = (
    "Sign up free",
    "free tier",
    "does not activate this paid plan",
    "無料で登録",
    "無料プラン",
    "有料プランは開始されません",
)


def _empty_response(_request, **_kwargs):
    return HttpResponse()


# Minimal URL contract for whole-template rendering without importing optional
# workspace packages. Reversal is presentation plumbing, not this policy.
_PUBLIC_NAMES = (
    "about",
    "api_docs",
    "contact",
    "contributors",
    "cookies",
    "demos",
    "donate",
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
        sub_rows = _pricing_rows_for_landing()
        context = {
            "sub_rows": sub_rows,
            "onprem_tier": next(
                (t for t in tier_rows() if t["id"] == "selfhosted"), None
            ),
            "tax_note": pricing.get("tax_note", ""),
            "pricing_notes": pricing["notes"],
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
def test_complete_landing_keeps_the_trial_funnel_visible(language):
    """Deletion-sensitive: hero, pricing include, CTA, note, and data must exist."""
    # Arrange
    expected = EXPECTED_TRIAL_FUNNEL[language]
    # Act
    visible = _visible_text(_rendered_landing(language))
    # Assert
    assert [value for value in expected if value not in visible] == []


@pytest.mark.parametrize("language", ["en", "ja"])
def test_landing_pricing_states_that_a_card_is_required(language):
    # Arrange
    expected = EXPECTED_LANDING_CARD_NOTE[language]
    # Act
    visible = _visible_text(_section(_rendered_landing(language), "pricing"))
    # Assert
    assert expected in visible


@pytest.mark.parametrize("language", ["en", "ja"])
def test_landing_pricing_drops_the_free_signup_copy(language):
    # Arrange
    retired = RETIRED_FREE_SIGNUP_COPY
    # Act
    visible = _visible_text(_section(_rendered_landing(language), "pricing"))
    # Assert
    assert [term for term in retired if term in visible] == []


def test_pricing_ctas_are_generic_signup_not_paid_activation():
    # Arrange: the Free pane is dropped (operator 2026-09-12); the Cloud CTA is
    # the single signup button and must still be the generic /auth/signup/.
    pattern = r'<a href="([^"]+)" class="btn btn-primary btn-block">'
    # Act
    hrefs = re.findall(pattern, _section(_rendered_landing("en"), "pricing"))
    # Assert
    assert hrefs == ["/auth/signup/"]


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
        "クラウド",
        "学術",
        "$19/mo",
        "Cool ストレージ 32 GB 込み",
        "インターネットへの送信",
    )
    # Act
    pricing = _visible_text(_section(_rendered_landing("ja"), "pricing"))
    # Assert
    assert [value for value in expected if value not in pricing] == []
