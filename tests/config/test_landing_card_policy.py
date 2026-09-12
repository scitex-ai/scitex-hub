"""Rendered policy guard for the anonymous signup funnel.

The landing and signup pages are pre-upgrade surfaces. They may describe the
free account/tier and show paid-plan prices, but must not introduce trial or
payment-card terms before a user deliberately starts a paid action. These tests
render the complete pages in both supported languages; source-word checks alone
previously blessed contradictory copy hidden in an included pricing partial.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest
from django.contrib.auth.models import AnonymousUser
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.test import RequestFactory, override_settings
from django.urls import include, path
from django.utils import translation

from apps.infra.auth_app.forms import SignupForm
from apps.infra.public_app.pricing import (
    load_pricing,
    published_price_rows,
)
from apps.infra.public_app.templatetags.landing_i18n import translate_dynamic

REPO = Path(__file__).resolve().parents[2]

EXPECTED_FREE_FUNNEL = {
    # Two-plan landing row (operator 2026-09-12): the Free pane is DROPPED —
    # Pro's 30-day free trial is the funnel entry. Pro (Academic/Non-Academic
    # switcher) + On-Prem (AGPL/Custom). The Pro price + a feature line prove
    # the paid plans render from the SSoT in the active language. Prices are
    # USD (always) on the marketing card; JPY lives on /tokushoho/.
    "en": (
        "Pro",
        "30-day free trial",
        "Sign up free",
        "$19/mo/user",
        "32 GB storage per month (Standard speed)",
    ),
    "ja": (
        "プロ",
        "30日間の無料トライアル",
        "無料で登録",
        "$19/mo/user",
        "32 GB ストレージ / 月 (Standard speed)",
    ),
}

EXPECTED_SIGNUP_POLICY = {
    "en": "Create your account and use SciTeX's free tier at no cost.",
    "ja": "アカウントを作成して、SciTeX の無料プランをご利用いただけます。",
}

# Terms that must NOT appear on the SIGNUP page (before the user consents) —
# they would pressure a pre-account visitor with payment/trial terms. The
# landing PRICING card DOES state "30-day free trial" (it's the Pro plan's
# feature, operator 2026-09-12), so the trial phrases are not in this list —
# only the pre-consent payment pressure terms are.
PRE_ACTION_PAID_DISCLOSURES = (
    "optional paid-plan trial",
    "credit or debit card",
    "payment card",
    "有料プラントライアル",
    "クレジットカード",
    "デビットカード",
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

    pricing = load_pricing()
    request = _request("/landing/")
    with translation.override(language):
        rows = published_price_rows()
        sub_rows = [
            {**r, "is_academic": r["id"] == "subscription-student"}
            for r in rows
            if r["category"] == "subscription"
        ]
        context = {
            "sub_rows": sub_rows,
            "onprem_tier": next(
                (t for t in tier_rows() if t["id"] == "onprem"), None
            ),
            "tax_note": pricing.get("tax_note", ""),
            "pricing_notes": pricing["notes"],
        }
        return render_to_string(
            "public_app/landing.html", context, request=request
        )


@override_settings(ROOT_URLCONF=__name__)
def _rendered_signup(language: str) -> str:
    with (
        translation.override(language),
        patch(
            "allauth.socialaccount.adapter.DefaultSocialAccountAdapter.list_providers",
            return_value=[],
        ),
    ):
        return render_to_string(
            "auth_app/signup.html",
            {"form": SignupForm()},
            request=_request("/signup/"),
        )


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
def test_complete_landing_keeps_the_free_funnel_visible(language):
    """Deletion-sensitive: hero, pricing include, CTA, note, and data must exist."""
    visible = _visible_text(_rendered_landing(language))
    assert all(expected in visible for expected in EXPECTED_FREE_FUNNEL[language])


@pytest.mark.parametrize("language", ["en", "ja"])
def test_complete_signup_keeps_the_free_tier_policy_visible(language):
    """Deletion-sensitive: removing the signup policy block fails in both locales."""
    visible = _visible_text(_rendered_signup(language))
    assert EXPECTED_SIGNUP_POLICY[language] in visible


@pytest.mark.parametrize("language", ["en", "ja"])
def test_pre_action_pricing_has_no_trial_or_payment_card_disclosure(language):
    pricing_html = _section(_rendered_landing(language), "pricing")
    visible = _visible_text(pricing_html).lower()
    has_disclosure = any(
        term.lower() in visible for term in PRE_ACTION_PAID_DISCLOSURES
    )
    assert 'class="pricing-trial"' not in pricing_html and not has_disclosure


@pytest.mark.parametrize("language", ["en", "ja"])
def test_pre_action_signup_has_no_trial_or_payment_card_disclosure(language):
    visible = _visible_text(_rendered_signup(language)).lower()
    assert not any(term.lower() in visible for term in PRE_ACTION_PAID_DISCLOSURES)


def test_pricing_ctas_are_generic_signup_not_paid_activation():
    pricing_html = _section(_rendered_landing("en"), "pricing")
    hrefs = re.findall(
        r'<a href="([^"]+)" class="btn btn-primary btn-block">', pricing_html
    )
    # Free pane is dropped (operator 2026-09-12): Pro's 30-day free trial is the
    # entry, so the Pro CTA is the single signup button. It must still be the
    # generic /auth/signup/ (no card / paid activation on the landing).
    assert hrefs == ["/auth/signup/"]


@pytest.mark.parametrize(
    ("language", "expected", "forbidden"),
    [
        ("en", "32 GB storage per month (Standard speed)", "ストレージ"),
        ("ja", "32 GB ストレージ / 月 (Standard speed)", "Storage"),
    ],
)
def test_runtime_pricing_values_follow_the_active_language(
    language, expected, forbidden
):
    """Call-time localization in published_price_rows() (2026-09-11).

    The SSoT is English-source; the storage cell is computed by pricing.py and
    translated when the active language is set. (This used to test
    translate_dynamic on a JA source string — the double-translation path that
    caused the en-callback bug and was removed from the landing template.)
    """
    with translation.override(language):
        rendered = [
            row["storage"]
            for row in published_price_rows()
            if row["id"] == "subscription-student"
        ][0]
    assert rendered == expected and forbidden not in rendered


def test_english_pricing_has_no_japanese_literals():
    pricing = _visible_text(_section(_rendered_landing("en"), "pricing"))
    assert re.search(r"[\u3040-\u30ff\u3400-\u9fff]", pricing) is None


def test_japanese_landing_renders_the_japanese_pricing_strings():
    """The JA landing shows the Japanese renderings of the EN-source SSoT.

    (Renamed from ``..._keeps_the_japanese_ssot_values``: the SSoT is now
    English-source — the Japanese text is the *rendered* catalog output, not
    the stored value.)"""
    pricing = _visible_text(_section(_rendered_landing("ja"), "pricing"))
    expected = (
        "サブスク",
        "学術",
        "月額 1,490円",
        "50 GB ストレージ / 月 (Standard)",
        "通常利用の範囲の通信",
    )
    assert all(value in pricing for value in expected)
