#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Guard for the 準拠法 / 裁判管轄 clauses on /terms/.

The page shipped US boilerplate: it named a US state's law as the governing
law and a US city's state and federal courts as the venue, for a service
operated from Japan for Japanese users. Both were replaced (operator
decision, 2026-07-30):

- 準拠法 (governing law) -> the laws of Japan (日本法)
- 裁判管轄 (venue)        -> the Shizuoka District Court (静岡地方裁判所),
  the district court with jurisdiction over the registered office
  〒420-0839 静岡県静岡市葵区鷹匠2-8-10 (config/settings/settings_commerce.py)

The realistic regression is not someone deliberately re-Americanising a
Japanese company's terms — it is a future boilerplate refresh pasting a US
template back over these two clauses, which is exactly how the US text got
here in the first place. So these tests assert on the RENDERED page and:

- pair every "no US venue" negative with a positive on the same clause. The
  positive half lives in the clause fixtures below, which refuse to hand a
  region to a test unless it still names the value that replaced the US
  one. That is where a deleted clause is caught: without it, "California is
  absent" holds trivially on an empty string.
- extract each clause by its own anchor and fail loudly if the anchor is
  gone, so a template that stopped rendering cannot read as success.
- keep the two clauses SEPARATE, because 準拠法 and 裁判管轄 are different
  facts and collapsing them into one sentence loses one of them. Each
  positive value is asserted inside its OWN anchored region, so moving the
  court into the governing-law clause fails rather than passes.
"""

import re

import pytest
from django.urls import reverse

# Clause boundaries in the rendered page. GOVERNING_LAW -> DISPUTE is the
# 準拠法 clause; DISPUTE -> CONTACT is the 裁判管轄 clause.
GOVERNING_LAW_ANCHOR = 'id="governing-law"'
DISPUTE_ANCHOR = 'id="dispute-resolution"'
CONTACT_ANCHOR = 'id="contact-us"'

# The decided values. Each concept is pinned in English AND Japanese: an
# English-only rendering of a Japanese court name is not actionable for a
# reader who has to file there.
JAPANESE_LAW_MARKERS = ("laws of Japan", "日本法")
SHIZUOKA_COURT_MARKERS = ("Shizuoka District Court", "静岡地方裁判所")

# The one marker per clause that the fixtures require, so that every
# negative assertion in this module is paired with a positive one.
JAPANESE_LAW_KEY = "日本法"
SHIZUOKA_COURT_KEY = "静岡地方裁判所"

# Every US state (plus DC), so a boilerplate refresh cannot swap California
# for Delaware and slip through a California-only check.
US_STATES = (
    "Alabama",
    "Alaska",
    "Arizona",
    "Arkansas",
    "California",
    "Colorado",
    "Connecticut",
    "Delaware",
    "District of Columbia",
    "Florida",
    "Georgia",
    "Hawaii",
    "Idaho",
    "Illinois",
    "Indiana",
    "Iowa",
    "Kansas",
    "Kentucky",
    "Louisiana",
    "Maine",
    "Maryland",
    "Massachusetts",
    "Michigan",
    "Minnesota",
    "Mississippi",
    "Missouri",
    "Montana",
    "Nebraska",
    "Nevada",
    "New Hampshire",
    "New Jersey",
    "New Mexico",
    "New York",
    "North Carolina",
    "North Dakota",
    "Ohio",
    "Oklahoma",
    "Oregon",
    "Pennsylvania",
    "Rhode Island",
    "South Carolina",
    "South Dakota",
    "Tennessee",
    "Texas",
    "Utah",
    "Vermont",
    "Virginia",
    "Washington",
    "West Virginia",
    "Wisconsin",
    "Wyoming",
)

# US venue / US-court-system vocabulary. "forum non conveniens" is here
# because it is a common-law doctrine with no counterpart in Japanese civil
# procedure: its presence is a reliable fingerprint of pasted US text even
# when no state is named.
US_VENUE_MARKERS = (
    "United States",
    "U.S.",
    "San Francisco",
    "federal court",
    "federal courts",
    "state court",
    "state courts",
    "state and federal",
    "forum non conveniens",
)

US_MARKERS = US_STATES + US_VENUE_MARKERS

# The two literal strings that were actually on this page before
# 2026-07-30, each with the value that replaced it.
REPLACED_US_VALUES = (
    ("California", JAPANESE_LAW_KEY),
    ("San Francisco", SHIZUOKA_COURT_KEY),
)

# A clause region shorter than this is not a clause; it is a heading with
# the prose gone.
MIN_CLAUSE_CHARS = 100


def _fetch_terms(client) -> str:
    """Return the rendered /terms/ page, or fail if it did not render."""
    response = client.get(reverse("public_app:terms"))
    assert response.status_code == 200, (
        f"/terms/ returned {response.status_code}; every assertion in this "
        "module would be vacuous on a page that does not render."
    )
    return response.content.decode("utf-8")


def _region(content: str, start_anchor: str, end_anchor: str) -> str:
    """Slice one clause out of the rendered page by its anchors.

    Fails loudly when an anchor is missing or the anchors are out of order.
    This is half the anti-vacuity mechanism: a clause that stopped
    rendering raises here instead of yielding an empty string in which
    every "no US venue" assertion would trivially hold.
    """
    start = content.find(start_anchor)
    end = content.find(end_anchor)
    assert start != -1, (
        f"clause anchor {start_anchor!r} is missing from the rendered "
        "/terms/ page — the clause is not rendering, so nothing that reads "
        "this region is actually being checked."
    )
    assert end != -1, (
        f"boundary anchor {end_anchor!r} is missing from the rendered "
        f"/terms/ page — cannot delimit the clause starting at "
        f"{start_anchor!r}."
    )
    assert end > start, (
        f"{end_anchor!r} precedes {start_anchor!r} in the rendered page; "
        "the clause order changed and this guard would measure the wrong "
        "region."
    )
    return content[start:end]


def _us_marker_present(marker: str, text: str) -> bool:
    """Word-bounded, case-insensitive search for a US marker.

    Word-bounded on purpose: a plain substring test for the state "Maine"
    matches the ordinary word "remained", which would make this guard cry
    wolf at the first unrelated rewording.
    """
    pattern = r"\b" + re.escape(marker) + r"(?![A-Za-z])"
    return re.search(pattern, text, re.IGNORECASE) is not None


@pytest.fixture
def terms_page(client) -> str:
    """The rendered /terms/ page, guaranteed to name BOTH decided values.

    Carries the positive half of the whole-page negative assertions: a
    blank or half-rendered page cannot satisfy this, so "California is
    absent" cannot pass for the wrong reason.
    """
    content = _fetch_terms(client)
    for required in (JAPANESE_LAW_KEY, SHIZUOKA_COURT_KEY):
        assert required in content, (
            f"/terms/ no longer names {required!r}. Until that is fixed, no "
            "absence-of-US-values assertion on this page means anything."
        )
    return content


@pytest.fixture
def governing_law_clause(client) -> str:
    """The rendered 準拠法 clause, guaranteed to still name 日本法.

    Pairing lives here rather than in each test because STX-TQ007 allows a
    single assertion per test: the fixture supplies the positive half to
    every negative test that consumes it.
    """
    clause = _region(_fetch_terms(client), GOVERNING_LAW_ANCHOR, DISPUTE_ANCHOR)
    assert JAPANESE_LAW_KEY in clause, (
        f"the Governing Law clause no longer names {JAPANESE_LAW_KEY!r}, so "
        "the absence of a US governing law in it would prove nothing. "
        f"Clause: {clause!r}"
    )
    return clause


@pytest.fixture
def venue_clause(client) -> str:
    """The rendered 裁判管轄 clause, guaranteed to still name 静岡地方裁判所."""
    clause = _region(_fetch_terms(client), DISPUTE_ANCHOR, CONTACT_ANCHOR)
    assert SHIZUOKA_COURT_KEY in clause, (
        f"the Dispute Resolution clause no longer names "
        f"{SHIZUOKA_COURT_KEY!r}, so the absence of a US venue in it would "
        f"prove nothing. Clause: {clause!r}"
    )
    return clause


@pytest.mark.django_db
class TestTermsClausesRender:
    """Anti-vacuity: both clause regions exist and carry prose.

    Every other test in this module reads one of these regions. If these
    fail, the negative assertions elsewhere are measuring nothing.
    """

    def test_terms_page_returns_http_200(self, client):
        # Arrange
        url = reverse("public_app:terms")

        # Act
        response = client.get(url)

        # Assert
        assert response.status_code == 200

    def test_governing_law_heading_renders(self, client):
        # Arrange
        expected = "Governing Law"

        # Act
        content = _fetch_terms(client)

        # Assert
        assert expected in content

    def test_dispute_resolution_heading_renders(self, client):
        # Arrange: a heading of its own — 裁判管轄 is not a sub-point of 準拠法
        expected = "Dispute Resolution"

        # Act
        content = _fetch_terms(client)

        # Assert
        assert expected in content

    def test_governing_law_clause_renders_prose_not_just_a_heading(self, client):
        # Arrange
        content = _fetch_terms(client)

        # Act
        clause = _region(content, GOVERNING_LAW_ANCHOR, DISPUTE_ANCHOR)

        # Assert
        assert len(clause) > len(GOVERNING_LAW_ANCHOR) + MIN_CLAUSE_CHARS, (
            f"the Governing Law clause rendered essentially empty: {clause!r}"
        )

    def test_dispute_resolution_clause_renders_prose_not_just_a_heading(
        self, client
    ):
        # Arrange
        content = _fetch_terms(client)

        # Act
        clause = _region(content, DISPUTE_ANCHOR, CONTACT_ANCHOR)

        # Assert
        assert len(clause) > len(DISPUTE_ANCHOR) + MIN_CLAUSE_CHARS, (
            "the Dispute Resolution clause rendered essentially empty: "
            f"{clause!r}"
        )


@pytest.mark.django_db
class TestTermsGoverningLawIsJapaneseLaw:
    """準拠法: the laws of Japan (日本法)."""

    @pytest.mark.parametrize("expected", JAPANESE_LAW_MARKERS)
    def test_governing_law_clause_names_japanese_law(self, client, expected):
        # Arrange: asserted inside the governing-law region only, so moving
        # this into another clause fails instead of passing
        content = _fetch_terms(client)

        # Act
        clause = _region(content, GOVERNING_LAW_ANCHOR, DISPUTE_ANCHOR)

        # Assert
        assert expected in clause, (
            f"the Governing Law clause must name {expected!r}; got: {clause!r}"
        )

    @pytest.mark.parametrize("forbidden", US_MARKERS)
    def test_governing_law_clause_names_no_us_law(
        self, governing_law_clause, forbidden
    ):
        """No US state or US court system in 準拠法.

        Paired positively by the ``governing_law_clause`` fixture, which
        requires 日本法 to still be there.
        """
        # Arrange
        clause = governing_law_clause

        # Act
        found = _us_marker_present(forbidden, clause)

        # Assert
        assert not found, (
            f"US governing-law marker {forbidden!r} reappeared in the "
            "Governing Law clause. This page is governed by Japanese law "
            f"(operator decision 2026-07-30). Clause: {clause!r}"
        )


@pytest.mark.django_db
class TestTermsVenueIsShizuokaDistrictCourt:
    """裁判管轄: the Shizuoka District Court (静岡地方裁判所)."""

    @pytest.mark.parametrize("expected", SHIZUOKA_COURT_MARKERS)
    def test_venue_clause_names_the_shizuoka_district_court(
        self, client, expected
    ):
        # Arrange: both renderings are required — an English-only court name
        # is not something a reader can act on
        content = _fetch_terms(client)

        # Act
        clause = _region(content, DISPUTE_ANCHOR, CONTACT_ANCHOR)

        # Assert
        assert expected in clause, (
            f"the Dispute Resolution clause must name {expected!r} "
            "(operator decision 2026-07-30 — the court with jurisdiction "
            f"over the registered office); got: {clause!r}"
        )

    @pytest.mark.parametrize("forbidden", US_MARKERS)
    def test_venue_clause_names_no_us_court(self, venue_clause, forbidden):
        """No US state or US court system in 裁判管轄.

        Paired positively by the ``venue_clause`` fixture, which requires
        静岡地方裁判所 to still be there.
        """
        # Arrange
        clause = venue_clause

        # Act
        found = _us_marker_present(forbidden, clause)

        # Assert
        assert not found, (
            f"US venue marker {forbidden!r} reappeared in the Dispute "
            "Resolution clause. Disputes are heard by 静岡地方裁判所 "
            f"(operator decision 2026-07-30). Clause: {clause!r}"
        )


@pytest.mark.django_db
class TestTermsPageHasNoReplacedUsValues:
    """The two literal strings that were actually on this page.

    Checked across the WHOLE page, not just the two clauses: a boilerplate
    refresh that reintroduces California under some other heading is the
    same defect. Paired positively by the ``terms_page`` fixture.
    """

    @pytest.mark.parametrize("forbidden, replaced_by", REPLACED_US_VALUES)
    def test_replaced_us_value_is_absent_from_the_whole_page(
        self, terms_page, forbidden, replaced_by
    ):
        # Arrange
        content = terms_page

        # Act
        found = _us_marker_present(forbidden, content)

        # Assert
        assert not found, (
            f"{forbidden!r} is back on /terms/. It was replaced by "
            f"{replaced_by!r} on 2026-07-30 by operator decision (Japanese "
            "law, 静岡地方裁判所). If this came from a boilerplate refresh, "
            "redo the two clauses instead of reverting them."
        )


if __name__ == "__main__":
    import os

    import pytest

    pytest.main([os.path.abspath(__file__)])

# EOF
