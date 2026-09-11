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
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
HERO = (
    REPO
    / "apps/infra/public_app/templates/public_app/landing_partials/landing_hero.html"
)
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
        "the Japanese CTA must tie payment to an EXPLICIT action; it says: "
        f"{msgstr!r}"
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
