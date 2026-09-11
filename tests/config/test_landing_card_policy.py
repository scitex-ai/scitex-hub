#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SEMANTIC POLICY REGRESSION: no card, and no AUTOMATIC conversion.

OPERATOR RULE (2026-09-11)
    Free signup and free use require NO card. Card/payment details are requested
    only after a SEPARATE, EXPLICIT paid-subscription or paid-trial action.

WHY THIS IS A SEMANTIC TEST AND NOT A STRING TEST
The first version of this copy was "corrected" and still wrong: it dropped "a
card is required" but kept "30-day free trial. Continue and you'll be billed for
the first month from day one" — passive automatic conversion. That still
contradicts the rule, because the rule is about WHEN payment is requested, not
merely about whether a card is mentioned. A test that looks for one banned word
would have passed it. So this asserts the POLICY:

  * the CTA must say free signup/use needs no card;
  * it must tie payment details to an EXPLICIT user action;
  * it must NOT describe conversion happening by itself.

It checks the English SOURCE and the Japanese CATALOG together, because the rule
is about what a user is told, and a user reading Japanese was told the opposite
of a user reading English.
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

from apps.infra.public_app.pricing import load_pricing, published_price_groups
from apps.infra.public_app.templatetags.landing_i18n import translate_dynamic

REPO = Path(__file__).resolve().parents[2]
HERO = (
    REPO
    / "apps/infra/public_app/templates/public_app/landing_partials/landing_hero.html"
)
SIGNUP = REPO / "apps/infra/auth_app/templates/auth_app/signup.html"
JA_PO = REPO / "locale/ja/LC_MESSAGES/django.po"

#: Phrases that describe conversion happening WITHOUT a further user action.
#: Each is a different way of saying the same forbidden thing.
AUTOMATIC_CONVERSION = (
    "you'll be billed",
    "you will be billed",
    "30-day free trial",
    "継続すると",
    "初月から課金",
)

FORBIDDEN_RENDERED_COPY = {
    "en": (
        "30-day free trial",
        "billed from signup",
        "one per email/card",
        "email + credit/debit card",
        "card registration is required",
    ),
    "ja": (
        "30日間無料トライアル",
        "初回分を登録日から課金",
        "1 メール/カードにつき1回",
        "メール認証 + クレジット/デビットカード",
        "クレジットカード / デビットカードの登録が必要です",
    ),
}

EXPLICIT_PAID_FLOW_COPY = {
    "en": "card details are requested only if you explicitly start this paid plan or its trial",
    "ja": "この有料プランまたはトライアルを明示的に開始する場合にのみ、カード情報をお願いします",
}

FREE_SIGNUP_COPY = {
    "en": "sign up free — no card needed",
    "ja": "無料で登録（カード不要）",
}


def _empty_response(_request, **_kwargs):
    return HttpResponse()


# Minimal URL contract for rendering the whole landing template. This keeps a
# copy regression independent from optional workspace packages and the DB.
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
                        "tests/<str:category>/",
                        _empty_response,
                        name="tests_category",
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


@override_settings(ROOT_URLCONF=__name__)
def _rendered_landing(language: str, section: str | None = None) -> str:
    pricing = load_pricing()
    context = {
        "published_price_groups": published_price_groups(),
        "tax_note": pricing.get("tax_note", ""),
        "pricing_notes": pricing["notes"],
    }
    request = RequestFactory().get("/landing/", HTTP_ACCEPT_LANGUAGE=language)
    request.user = AnonymousUser()
    request.session = {}
    with translation.override(language):
        html = render_to_string("public_app/landing.html", context, request=request)
    if section is not None:
        match = re.search(
            rf'<section\b[^>]*id="{re.escape(section)}".*?</section>', html, re.S
        )
        assert match, f"rendered landing has no {section!r} section"
        html = match.group()
    html = re.sub(r"<!--.*?-->|<(script|style)\b.*?</\1>", " ", html, flags=re.S | re.I)
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html))


def test_whole_english_landing_pricing_has_no_japanese_literals():
    pricing = _rendered_landing("en", section="pricing")
    assert re.search(r"[\u3040-\u30ff\u3400-\u9fff]", pricing) is None


def test_runtime_pricing_values_use_the_active_language():
    source = "定価 2,980円、早期導入割引 50%。2027年7月末までの早期導入価格。"
    with translation.override("en"):
        rendered = translate_dynamic(source)
    assert rendered.startswith("List price ¥2,980")


@pytest.mark.parametrize("language", ["en", "ja"])
def test_whole_landing_rejects_generic_card_or_trial_claims(language):
    visible = _rendered_landing(language).lower()
    contradictions = [
        phrase
        for phrase in FORBIDDEN_RENDERED_COPY[language]
        if phrase.lower() in visible
    ]
    assert contradictions == []


@pytest.mark.parametrize("language", ["en", "ja"])
def test_whole_landing_qualifies_card_request_as_explicit_paid_action(language):
    visible = _rendered_landing(language).lower()
    assert EXPLICIT_PAID_FLOW_COPY[language].lower() in visible


@pytest.mark.parametrize("language", ["en", "ja"])
def test_whole_landing_says_generic_signup_is_cardless(language):
    visible = _rendered_landing(language).lower()
    assert FREE_SIGNUP_COPY[language].lower() in visible


def _hero_cta_note_source() -> str:
    """The hero CTA note's English translatable string."""
    text = HERO.read_text(encoding="utf-8")
    match = re.search(
        r'<p class="hero-cta-note">\{%\s*trans\s*"(?P<msg>.*?)"\s*%\}</p>',
        text,
        re.DOTALL,
    )
    assert match, "the hero CTA note is no longer a {% trans %} string"
    return match.group("msg")


def _signup_card_policy_source() -> str:
    text = SIGNUP.read_text(encoding="utf-8")
    match = re.search(
        r'<p class="text-muted signup-card-policy">\s*'
        r'\{%\s*trans\s*"(?P<msg>.*?)"\s*%\}\s*</p>',
        text,
        re.DOTALL,
    )
    assert match, "the signup card policy is no longer a {% trans %} string"
    return match.group("msg")


def test_signup_page_states_free_tier_is_cardless_until_explicit_paid_action():
    source = _signup_card_policy_source().lower()
    assert "free-tier use require no card" in source and "explicitly start" in source


def test_japanese_signup_page_carries_the_same_cardless_policy():
    translated = _ja_catalog()[_signup_card_policy_source()]
    assert (
        "無料プラン" in translated
        and "カードは不要" in translated
        and "明示的" in translated
    )


def _ja_catalog() -> dict[str, str]:
    """msgid -> msgstr from the Japanese catalog (block form)."""
    entries: dict[str, str] = {}
    msgid: str | None = None
    for line in JA_PO.read_text(encoding="utf-8").splitlines():
        if line.startswith("msgid "):
            msgid = line[len("msgid ") :].strip().strip('"')
        elif line.startswith("msgstr ") and msgid is not None:
            entries[msgid] = line[len("msgstr ") :].strip().strip('"')
            msgid = None
    return entries


def test_the_cta_states_that_free_use_needs_no_card():
    source = _hero_cta_note_source().lower()
    assert "no card" in source, (
        "the generic signup CTA must say plainly that free signup/use needs no "
        f"card; it says: {source!r}"
    )


def test_the_cta_ties_payment_to_an_explicit_user_action():
    source = _hero_cta_note_source().lower()
    assert "explicitly" in source, (
        "payment details must be tied to a SEPARATE, EXPLICIT action; the rule is "
        f"about when they are requested. It says: {source!r}"
    )


@pytest.mark.parametrize("phrase", AUTOMATIC_CONVERSION)
def test_the_english_source_never_promises_automatic_conversion(phrase):
    source = _hero_cta_note_source()
    assert phrase not in source, (
        f"the CTA still describes conversion without a further user action "
        f"({phrase!r}). That is passive automatic conversion, which the operator "
        f"rule forbids: {source!r}"
    )


def test_the_japanese_catalog_carries_the_same_policy():
    """A user reading Japanese must not be told the opposite of one reading
    English — which is exactly what the previous wording did."""
    msgid = _hero_cta_note_source()
    catalog = _ja_catalog()
    assert msgid in catalog, (
        "the Japanese catalog has NO entry for the current English source, so "
        "the CTA renders ENGLISH under ja. The msgid drifted; regenerate or "
        "update the catalog."
    )
    msgstr = catalog[msgid]
    assert msgstr, "the Japanese entry is untranslated"
    assert "カード" in msgstr, (
        f"the Japanese CTA must address the card question; it says: {msgstr!r}"
    )
    assert "明示的" in msgstr, (
        f"the Japanese CTA must tie payment to an EXPLICIT action; it says: {msgstr!r}"
    )


@pytest.mark.parametrize("phrase", AUTOMATIC_CONVERSION)
def test_the_japanese_catalog_never_promises_automatic_conversion(phrase):
    """The catalog is checked as a WHOLE, not just the current entry: a stale
    entry for a superseded msgid is still shipped to users."""
    for msgid, msgstr in _ja_catalog().items():
        assert phrase not in msgstr, (
            f"the Japanese catalog still contains {phrase!r} in the entry for "
            f"{msgid!r}: {msgstr!r}"
        )


def test_no_superseded_automatic_conversion_msgid_survives():
    """The old English sentence must be gone from the catalog entirely, so a
    revert of the template cannot silently resurrect it."""
    catalog = _ja_catalog()
    stale = [msgid for msgid in catalog if "free trial" in msgid.lower()]
    assert stale == [], f"superseded trial msgids still in the catalog: {stale}"
