#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""No legal page may publish a FABRICATED postal address.

WHAT WENT WRONG. /cookies/ published, inside ``<address>``::

    SciTeX
    Attn: Privacy Officer
    123 Science Park
    San Francisco, CA 94107

Every line of that but the first was invented. The app ALREADY held the real
registered address (``settings.COMPANY_ADDRESS``, 特定商取引法 disclosure) and
already rendered it correctly on /services/tokushoho/ — so the privacy page did
not lack information, it CONTRADICTED a value the app owned, in violation of the
project's explicit no-fake-data rule, on a privacy contact.

WHY A SOURCE-LEVEL TEST WOULD NOT HAVE BEEN ENOUGH. The obvious repair is to
write ``{{ company_address }}`` into the template. That renders EMPTY: only the
tokushoho VIEW puts ``company_address`` in its context, and ``cookie_policy``
renders with no extra context at all, so a template outside that view sees
nothing. Django does not raise on an unknown variable — it substitutes the empty
string — so the page would ship an ``<address>`` block with no address in it,
which is WORSE than a wrong one. That is the same class of bug as
``templates/500.html`` (rendered with no context processors at all). A test
asserting the template *mentions* a variable would pass while the page renders
blank. So the checks below FETCH the page through the real URLconf and assert on
the RENDERED BYTES.

PAIRING. Every negative assertion here has a positive partner, because a
negative alone cannot tell "clean" from "looked at nothing":

    the state+ZIP regex finds nothing   <->  the same regex matches known US
                                             addresses (incl. the exact removed
                                             string), and matches NEITHER the
                                             real Japanese address nor the
                                             out-of-scope "San Francisco,
                                             California" governing-law clause
    no template holds a US address      <->  the swept file list is non-empty,
                                             complete, and each file is readable
    /cookies/ has no invented role      <->  /cookies/ renders the REAL address
                                             and the privacy mailto

OUT OF SCOPE, DELIBERATELY. ``terms_of_use.html`` puts governing law and venue
in "San Francisco, California". That is a substantive legal TERM, not a
fabricated fact, and the operator has approved moving it to a Japanese court but
has not yet chosen which one. The regex below requires a five-digit ZIP
precisely so it does NOT match that clause — a negative control pins this, so
widening the pattern later cannot quietly drag the venue clause into scope.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from django.conf import settings
from django.test import RequestFactory
from django.urls import reverse

from config.context_processors import site_branding

LEGAL_TEMPLATE_DIR = "apps/infra/public_app/templates/public_app/legal"

# Every legal template, discovered from disk rather than hand-listed, so a new
# sibling page is swept the day it is added. Discovery is itself asserted below
# (``test_every_expected_legal_template_was_discovered``) — a glob that returns
# nothing would otherwise make every parametrized sweep vacuous.
LEGAL_TEMPLATES = tuple(
    sorted(
        f"{LEGAL_TEMPLATE_DIR}/{path.name}"
        for path in (Path(settings.BASE_DIR) / LEGAL_TEMPLATE_DIR).glob("*.html")
    )
)

# The pages that existed when this guard was written. Named literally so a
# RENAME or DELETION fails loudly instead of shrinking the swept set in silence.
EXPECTED_LEGAL_TEMPLATES = (
    "contact.html",
    "cookie_policy.html",
    "donate.html",
    "marketplace_terms.html",
    "privacy_policy.html",
    "terms_of_use.html",
    "tokushoho.html",
)

# A US-style "<CITY>, <ST> <ZIP>" tail: two capitals, whitespace, five digits,
# optional +4. The five-digit ZIP is REQUIRED — that is what separates a
# fabricated mailing address from the legitimate "San Francisco, California"
# governing-law clause, which carries no ZIP and is out of scope.
US_STATE_ZIP_RE = re.compile(r"\b[A-Z]{2}\s+[0-9]{5}(?:-[0-9]{4})?\b")

# Strings the regex MUST match, or it is broken and every sweep below is
# vacuous. The first is the exact string that shipped on /cookies/.
US_ADDRESS_SAMPLES = (
    "San Francisco, CA 94107",
    "New York, NY 10001",
    "Austin, TX 78701-1234",
)

# Strings the regex MUST NOT match. The Japanese address is the value the pages
# are supposed to show, and the venue clause is explicitly out of scope; a regex
# that flagged either would make this guard unlandable for the wrong reason.
NON_US_ADDRESS_SAMPLES = (
    "〒420-0839 静岡県静岡市葵区鷹匠2-8-10",
    "San Francisco, California",
    "SciTeX",
)

# Invented specifics that were on the page. Kept as literals because these are
# exactly what must never come back; they are not derived from any constant.
FABRICATED_LITERALS = (
    "123 Science Park",
    "Science Park",
    "Privacy Officer",
)

# Pages that must SHOW the registered address, with the url name to fetch it by.
# /terms/ and /privacy/ are deliberately absent: the operator ruled they show
# name + email only until incorporation completes (2026-08-08).
PAGES_CARRYING_THE_ADDRESS = (
    "public_app:cookies",
    "public_app:tokushoho",
)


def _read(rel):
    return (Path(settings.BASE_DIR) / rel).read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# The regex itself: positive and negative controls
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("sample", US_ADDRESS_SAMPLES)
def test_state_zip_regex_matches_a_known_us_address(sample):
    """Anti-vacuity: a broken regex must fail HERE, not pass every sweep."""
    # Arrange
    pattern = US_STATE_ZIP_RE

    # Act
    matched = bool(pattern.search(sample))

    # Assert
    assert matched, (
        f"US_STATE_ZIP_RE ({pattern.pattern!r}) does not match {sample!r}. The "
        "sweeps below assert this regex finds NOTHING in the legal templates; if "
        "the regex matches nothing anywhere, those sweeps pass while a fabricated "
        "address sits on a live page. Fix the regex, do not delete this test."
    )


@pytest.mark.parametrize("sample", NON_US_ADDRESS_SAMPLES)
def test_state_zip_regex_ignores_non_us_text(sample):
    """The guard must not flag the real address or the venue clause."""
    # Arrange
    pattern = US_STATE_ZIP_RE

    # Act
    matched = bool(pattern.search(sample))

    # Assert
    assert not matched, (
        f"US_STATE_ZIP_RE ({pattern.pattern!r}) matches {sample!r}, which it must "
        "not. Either it now flags the registered Japanese address the pages are "
        "supposed to show, or it has been widened to catch "
        "'San Francisco, California' — the governing-law clause that is tracked "
        "separately and deliberately out of this guard's scope."
    )


# ---------------------------------------------------------------------------
# The swept set: it must be non-empty and complete
# ---------------------------------------------------------------------------
def test_legal_templates_were_discovered():
    """A glob returning [] would make every parametrized sweep vacuous."""
    # Arrange
    directory = LEGAL_TEMPLATE_DIR

    # Act
    found = LEGAL_TEMPLATES

    # Assert
    assert found, (
        f"no *.html discovered under {directory}. Every sweep below is "
        "parametrized over this list, so zero files means zero tests run and the "
        "suite goes green without checking anything. Did the directory move?"
    )


@pytest.mark.parametrize("name", EXPECTED_LEGAL_TEMPLATES)
def test_every_expected_legal_template_was_discovered(name):
    """A renamed page must fail loudly, not silently leave the swept set."""
    # Arrange
    expected = f"{LEGAL_TEMPLATE_DIR}/{name}"

    # Act
    discovered = LEGAL_TEMPLATES

    # Assert
    assert expected in discovered, (
        f"{expected} is not in the discovered legal templates {discovered}. If the "
        "page was intentionally renamed or removed, update "
        "EXPECTED_LEGAL_TEMPLATES in the same commit — otherwise a page silently "
        "dropped out of the fabricated-address sweep."
    )


@pytest.mark.parametrize("rel", LEGAL_TEMPLATES)
def test_legal_template_is_readable(rel):
    """Anti-vacuity: ``findall`` over an empty string also returns []."""
    # Arrange
    minimum_bytes = 50

    # Act
    size = len(_read(rel))

    # Assert
    assert size > minimum_bytes, (
        f"{rel} read as {size} bytes, so the content assertions below would pass "
        "on an empty string and a truncated template would read as perfectly "
        "clean. Do not delete this check."
    )


# ---------------------------------------------------------------------------
# The sweep: no legal template may hold a fabricated address
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("rel", LEGAL_TEMPLATES)
def test_legal_template_has_no_us_state_zip_address(rel):
    """A US mailing address on these pages is fabricated by construction."""
    # Arrange
    expected = []

    # Act
    found = sorted(set(US_STATE_ZIP_RE.findall(_read(rel))))

    # Assert
    assert found == expected, (
        f"{rel} contains US-style state+ZIP address text {found}. SciTeX is "
        "registered in Japan and the real address is settings.COMPANY_ADDRESS, "
        "exported to templates as {{ COMPANY_ADDRESS }} by "
        "config.context_processors.site_branding. A US address here is invented — "
        "render the real one instead of hardcoding any address."
    )


@pytest.mark.parametrize("rel", LEGAL_TEMPLATES)
@pytest.mark.parametrize("literal", FABRICATED_LITERALS)
def test_legal_template_has_no_fabricated_placeholder(rel, literal):
    """The specific invented strings that shipped must not return."""
    # Arrange
    content = _read(rel)

    # Act
    present = literal in content

    # Assert
    assert not present, (
        f"{rel} contains {literal!r}, which was fabricated placeholder text on "
        "/cookies/. 'Science Park' was an invented street; 'Privacy Officer' "
        "asserted a named role inside an organisation that is still "
        "法人設立手続き中 (incorporation in progress) with one declared "
        "representative. Neither is a fact the app can support."
    )


# ---------------------------------------------------------------------------
# The context processor must actually export the address
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("name", ("COMPANY_ADDRESS", "COMPANY_NAME"))
def test_site_branding_exports_the_company_value(name):
    """A template variable that is not exported renders as the empty string."""
    # Arrange
    exported = site_branding(RequestFactory().get("/"))

    # Act
    present = name in exported

    # Assert
    assert present, (
        f"config.context_processors.site_branding does not export {name}. Django "
        "renders an unknown variable as the EMPTY string rather than raising, so a "
        "template using it would ship an <address> block with no address — the "
        "exact failure this guard exists to prevent."
    )


def test_site_branding_company_address_is_the_settings_value():
    """The exported address must be the owned setting, not a private copy."""
    # Arrange
    expected = settings.COMPANY_ADDRESS

    # Act
    actual = site_branding(RequestFactory().get("/"))["COMPANY_ADDRESS"]

    # Assert
    assert actual == expected, (
        f"site_branding exports COMPANY_ADDRESS as {actual!r} but "
        f"settings.COMPANY_ADDRESS is {expected!r}. settings_commerce.py OWNS this "
        "value as a 特定商取引法 legal disclosure; the context processor only "
        "widens READ access and must never hold its own copy."
    )


def test_company_address_setting_is_configured():
    """Anti-vacuity: the render assertions below are empty-string-satisfiable."""
    # Arrange
    minimum_length = 5

    # Act
    address = settings.COMPANY_ADDRESS

    # Assert
    assert len(address) >= minimum_length, (
        f"settings.COMPANY_ADDRESS is {address!r}. The render checks below assert "
        "this string appears in the page body — with an empty or near-empty value "
        "that assertion is trivially true of every response, so they would prove "
        "nothing. Set SCITEX_HUB_COMPANY_ADDRESS."
    )


# ---------------------------------------------------------------------------
# RENDER PROOF: the address must ARRIVE in the response body
# ---------------------------------------------------------------------------
# This is the point of the whole file. Source-level checks cannot distinguish
# "renders the real address" from "renders an empty <address>", because both
# templates contain the same {{ COMPANY_ADDRESS }} token.
@pytest.mark.django_db
@pytest.mark.parametrize("url_name", PAGES_CARRYING_THE_ADDRESS)
def test_page_carrying_the_address_returns_http_200(url_name, client):
    """Anti-vacuity: an error page contains no address either."""
    # Arrange
    expected_status = 200

    # Act
    status = client.get(reverse(url_name)).status_code

    # Assert
    assert status == expected_status, (
        f"{url_name} returned HTTP {status}. The assertion below reads the "
        "response body for the address, so it would be vacuous on an error page."
    )


@pytest.mark.django_db
@pytest.mark.parametrize("url_name", PAGES_CARRYING_THE_ADDRESS)
def test_page_renders_the_registered_company_address(url_name, client):
    """The real address must reach the rendered page, not just the template."""
    # Arrange
    expected = settings.COMPANY_ADDRESS

    # Act
    content = client.get(reverse(url_name)).content.decode("utf-8")

    # Assert
    assert expected in content, (
        f"{url_name} does not render settings.COMPANY_ADDRESS ({expected!r}). "
        "Either the template lost its address reference, or it is rendered WITHOUT "
        "the site_branding context processor — in which case the page shows an "
        "<address> block with no address, which is worse than a wrong one. Note "
        "the tokushoho VIEW passes a lowercase 'company_address' for that page "
        "only; every other template must use {{ COMPANY_ADDRESS }}."
    )


@pytest.mark.django_db
@pytest.mark.parametrize("literal", FABRICATED_LITERALS)
def test_cookie_policy_renders_no_fabricated_text(literal, client):
    """Paired with the positive render check above, on the reported page."""
    # Arrange
    url = reverse("public_app:cookies")

    # Act
    content = client.get(url).content.decode("utf-8")

    # Assert
    assert literal not in content, (
        f"/cookies/ still renders {literal!r}. This is checked on the RENDERED "
        "page as well as in the template source because an included partial or a "
        "block override could reintroduce it without the source sweep noticing."
    )


@pytest.mark.django_db
def test_cookie_policy_renders_no_us_state_zip_address(client):
    """The reported defect, asserted against the bytes a visitor receives."""
    # Arrange
    url = reverse("public_app:cookies")

    # Act
    found = sorted(set(US_STATE_ZIP_RE.findall(client.get(url).content.decode("utf-8"))))

    # Assert
    assert found == [], (
        f"/cookies/ renders US-style state+ZIP address text {found}. This is the "
        "operator-reported defect (「このページじゅうしょがちがいます」) — the page "
        "published a San Francisco address for a company registered in Japan."
    )


@pytest.mark.django_db
def test_cookie_policy_renders_no_unincorporated_company_name(client):
    """株式会社 SciTeX does not legally exist until 2026-08-08.

    Paired with ``test_cookie_policy_renders_the_site_name`` below: the page must
    name SOMETHING, and what it names must be true today. Replacing a fabricated
    address with a company that does not yet exist would be the same defect in a
    new costume, on the same page.
    """
    # Arrange
    forbidden = settings.COMPANY_NAME

    # Act
    content = client.get(reverse("public_app:cookies")).content.decode("utf-8")

    # Assert
    assert forbidden not in content, (
        f"/cookies/ renders settings.COMPANY_NAME ({forbidden!r}). That entity is "
        "not incorporated until 2026-08-08 — /services/tokushoho/ still says "
        "法人設立手続き中 — so this page must render SITE_NAME until then, as "
        "/terms/ and /privacy/ do. After incorporation, delete this test in the "
        "same commit that switches the template."
    )


@pytest.mark.django_db
def test_cookie_policy_renders_the_site_name(client):
    """Positive partner: the address block must still identify who you write to."""
    # Arrange
    from config import branding

    expected = branding.SITE_NAME

    # Act
    content = client.get(reverse("public_app:cookies")).content.decode("utf-8")

    # Assert
    assert expected in content, (
        f"/cookies/ does not render {expected!r}. Without this, the "
        "company-name check above would pass on a page that names nobody at all."
    )


@pytest.mark.django_db
@pytest.mark.parametrize("marker", ("{#", "{%", "{{"))
def test_cookie_policy_renders_no_raw_template_syntax(marker, client):
    """Unrendered template syntax in the body means a tag silently did not fire.

    This exists because it actually happened while writing this fix. Django's
    hash-style comment is SINGLE-LINE only — its lexer regex is compiled without
    re.DOTALL, so the dot cannot cross a newline. A multi-line hash comment is
    therefore not a comment: the whole block renders as visible body text AND the
    variables inside it are interpolated. The draft comment explaining why the
    company name must not be printed yet would itself have printed it.

    Asserting on the RENDERED body catches the entire class — any tag that failed
    to tokenize leaves its own braces behind in the output.
    """
    # Arrange
    url = reverse("public_app:cookies")

    # Act
    content = client.get(url).content.decode("utf-8")

    # Assert
    assert marker not in content, (
        f"/cookies/ renders raw template syntax {marker!r}, so a tag or comment "
        "did not tokenize and is being shown to visitors as text. The usual cause "
        "is a multi-line hash-style comment, which Django does not support — use "
        "a comment TAG instead."
    )


@pytest.mark.django_db
def test_cookie_policy_does_not_render_its_own_source_comment(client):
    """The comment explaining the fix must not become part of the page.

    A sentinel phrase rather than a brace pattern: this cannot false-positive on
    inline JS or a CSS rule, so it keeps working even if the brace markers above
    ever have to be narrowed.
    """
    # Arrange
    sentinel = "Keep this a comment TAG"

    # Act
    content = client.get(reverse("public_app:cookies")).content.decode("utf-8")

    # Assert
    assert sentinel not in content, (
        f"/cookies/ renders {sentinel!r}, so the explanatory comment above the "
        "<address> block is being shown to visitors as body text. Django's "
        "hash-style comment does not span lines — use a comment TAG. If that "
        "comment is ever reworded, update this sentinel in the same commit."
    )


@pytest.mark.django_db
def test_cookie_policy_renders_the_privacy_contact_email(client):
    """Positive partner: the contact route must survive the address repair."""
    # Arrange
    from config import branding

    expected = f"mailto:{branding.PRIVACY_EMAIL}"

    # Act
    content = client.get(reverse("public_app:cookies")).content.decode("utf-8")

    # Assert
    assert expected in content, (
        f"/cookies/ does not render {expected}. Removing the fabricated postal "
        "address must not take the working contact with it — the email is the "
        "route a privacy-concerned reader actually uses."
    )


if __name__ == "__main__":
    import os

    pytest.main([os.path.abspath(__file__)])

# EOF
