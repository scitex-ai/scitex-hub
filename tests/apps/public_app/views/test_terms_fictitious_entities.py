#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Guard: /terms/ must not name people or companies that do not exist.

The page was built from a US corporate template and so extended its
liability cap and its indemnity to a corporate group SciTeX does not have
-- "our directors, employees, or agents", "our subsidiaries, affiliates,
and all of our respective officers, agents, partners, and employees" --
and addressed the reader to a "Legal Department". SciTeX is operated by
one person (operator ruling, 2026-07-30: 「リーガルデパートメントはない
です。すいません私1人会社です」).

That is not harmless boilerplate. An indemnity naming parties who do not
exist describes a different company than the one the user is contracting
with, on the page whose entire job is to state who they are contracting
with. It is the same defect class as the fabricated San Francisco address
that /cookies/ published until 2026-07-30.

WHY THIS ASSERTS ON THE RENDERED PAGE AND NOT ON THE TEMPLATE SOURCE:
the template deliberately carries a {% comment %} block that NAMES every
forbidden noun, to tell the next reader why they are absent. A guard that
grepped the template source would therefore fail on its own explanation.
Rendered HTML is the honest surface -- it is also what the user actually
receives, which is the thing we are making claims about.

ANTI-VACUITY. Every assertion here is negative ("this noun is gone"), and
a negative assertion passes for free once the text it searches is empty:
delete the Limitation of Liability clause outright and "no directors"
holds trivially. So no test reads a region directly. Each takes a fixture
that refuses to hand over the region unless it still contains the clause's
own load-bearing positive phrase. The pass condition is a CONJUNCTION --
"the clause is still here AND still says what it should AND names nobody
fictional" -- and it is stated in the fixture, before any test runs.
"""

import re

import pytest
from django.urls import reverse

# Clause boundaries in the rendered page. Each clause is delimited by its
# own anchor and the anchor of the clause that follows it.
LIABILITY_ANCHOR = 'id="limitation-of-liability"'
INDEMNITY_ANCHOR = 'id="indemnification"'
GOVERNING_LAW_ANCHOR = 'id="governing-law"'

# The load-bearing phrase each clause must still contain. These are the
# positive halves: they are what makes the absence assertions mean
# something, so they are asserted in the fixtures rather than in tests.
LIABILITY_KEY = "In no event will we be liable"
INDEMNITY_KEY = "defend, indemnify, and hold us harmless"
CONTACT_KEY = "Email SciTeX at"

# Nouns for parties SciTeX does not have. A one-person operation's
# liability and indemnity clauses name "we" and "us" and nobody else, so
# any of these reappearing inside those two clauses is a regression --
# including a reworded reintroduction such as "our officers and
# employees", which a phrase-level check would miss.
FICTITIOUS_PARTY_NOUNS = (
    "directors",
    "director",
    "subsidiaries",
    "subsidiary",
    "affiliates",
    "affiliate",
    "officers",
    "officer",
    "employees",
    "employee",
    "agents",
    "partners",
)

# Scoped to the two clauses, NOT the whole page, on purpose: SciTeX is an
# AI-agent product, so "agents" is a legitimate word elsewhere on the
# site and a page-wide ban would cry wolf at the first correct sentence.
FICTITIOUS_DEPARTMENT = "Legal Department"

# A clause region shorter than this is a heading with the prose gone.
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

    Fails loudly when an anchor is missing or the anchors are out of
    order, so a clause that stopped rendering raises here instead of
    yielding an empty string in which every absence assertion holds.
    """
    start = content.find(start_anchor)
    end = content.find(end_anchor)
    assert start != -1, (
        f"clause anchor {start_anchor!r} is missing from the rendered "
        "/terms/ page -- the clause is not rendering, so nothing that "
        "reads this region is actually being checked."
    )
    assert end != -1, (
        f"boundary anchor {end_anchor!r} is missing from the rendered "
        f"/terms/ page -- cannot delimit the clause starting at "
        f"{start_anchor!r}."
    )
    assert end > start, (
        f"{end_anchor!r} precedes {start_anchor!r} in the rendered page; "
        "the clause order changed and this guard would measure the wrong "
        "region."
    )
    return content[start:end]


def _party_nouns_present(text: str) -> tuple:
    """Return the fictitious-party nouns found in ``text``.

    Word-bounded and case-insensitive. Word-bounded matters here: a plain
    substring test for "officer" also matches "officers", and for
    "agents" also matches "agentsomething", which would make the failure
    message name the wrong noun.
    """
    found = []
    for noun in FICTITIOUS_PARTY_NOUNS:
        pattern = r"\b" + re.escape(noun) + r"(?![A-Za-z])"
        if re.search(pattern, text, re.IGNORECASE):
            found.append(noun)
    return tuple(found)


@pytest.fixture
def liability_clause(client) -> str:
    """The rendered liability clause, guaranteed to still cap liability.

    Carries the positive half for the liability assertion: a deleted or
    gutted clause fails here rather than passing an absence check.
    """
    region = _region(_fetch_terms(client), LIABILITY_ANCHOR, INDEMNITY_ANCHOR)
    assert len(region) >= MIN_CLAUSE_CHARS, (
        f"the Limitation of Liability clause rendered only {len(region)} "
        f"characters (< {MIN_CLAUSE_CHARS}); that is a heading with the "
        "prose gone, and an absence assertion over it proves nothing."
    )
    assert LIABILITY_KEY in region, (
        f"the liability clause no longer contains {LIABILITY_KEY!r}. Until "
        "that is fixed, 'this clause names no fictional parties' can pass "
        "simply because the clause stopped saying anything."
    )
    return region


@pytest.fixture
def indemnity_clause(client) -> str:
    """The rendered indemnity clause, guaranteed to still indemnify.

    Same pairing as ``liability_clause``, for the indemnity.
    """
    region = _region(_fetch_terms(client), INDEMNITY_ANCHOR, GOVERNING_LAW_ANCHOR)
    assert len(region) >= MIN_CLAUSE_CHARS, (
        f"the Indemnification clause rendered only {len(region)} "
        f"characters (< {MIN_CLAUSE_CHARS}); that is a heading with the "
        "prose gone, and an absence assertion over it proves nothing."
    )
    assert INDEMNITY_KEY in region, (
        f"the indemnity clause no longer contains {INDEMNITY_KEY!r}. Until "
        "that is fixed, 'this clause names no fictional parties' can pass "
        "simply because the clause stopped saying anything."
    )
    return region


@pytest.fixture
def contact_page(client) -> str:
    """The rendered page, guaranteed to still offer a legal contact.

    Carries the positive half for the "Legal Department" assertion: the
    contact route must still exist and still be labelled, so removing the
    address block cannot read as success.
    """
    content = _fetch_terms(client)
    assert CONTACT_KEY in content, (
        f"/terms/ no longer contains {CONTACT_KEY!r}, so the legal contact "
        "link has lost its accessible label. Until that is fixed, "
        "'Legal Department is absent' can pass because the whole contact "
        "block is absent."
    )
    return content


def test_liability_clause_names_no_parties_that_do_not_exist(liability_clause):
    """The liability cap covers "we" and nobody else."""
    # Arrange: the fixture has already proved the clause renders and still
    # contains its load-bearing phrase -- the positive half of this test.
    clause = liability_clause
    # Act
    found = _party_nouns_present(clause)
    # Assert
    assert not found, (
        f"the Limitation of Liability clause on /terms/ names {found!r}. "
        "SciTeX is operated by one person and has no directors, employees "
        "or agents, so capping their liability describes a company that "
        "does not exist. Remove them, or -- if SciTeX now genuinely has "
        "them -- name only the ones that exist and update "
        "FICTITIOUS_PARTY_NOUNS in this module deliberately."
    )


def test_indemnity_clause_names_no_parties_that_do_not_exist(indemnity_clause):
    """The indemnity runs to "us" and nobody else."""
    # Arrange: the fixture has already proved the clause renders and still
    # contains its load-bearing phrase -- the positive half of this test.
    clause = indemnity_clause
    # Act
    found = _party_nouns_present(clause)
    # Assert
    assert not found, (
        f"the Indemnification clause on /terms/ names {found!r}. An "
        "indemnity extended to subsidiaries, affiliates, officers, "
        "partners or employees that do not exist misdescribes the party "
        "the user is contracting with, on the page whose job is to state "
        "who that party is. Remove them, or name only the ones that "
        "exist and update FICTITIOUS_PARTY_NOUNS deliberately."
    )


def test_no_legal_department_is_addressed(contact_page):
    """There is no Legal Department to email."""
    # Arrange: the fixture has already proved the contact link renders with
    # an accessible label -- the positive half of this test.
    pattern = r"\b" + re.escape(FICTITIOUS_DEPARTMENT) + r"(?![A-Za-z])"
    # Act
    match = re.search(pattern, contact_page, re.IGNORECASE)
    # Assert
    assert match is None, (
        f"/terms/ addresses the reader to a {FICTITIOUS_DEPARTMENT!r}, "
        "which does not exist -- SciTeX is one person. This appeared in an "
        "aria-label, so it was invisible on screen and read aloud to "
        "screen-reader users only, which is why it survived a visual "
        "review. Label the link with who actually answers."
    )


def test_forbidden_noun_detector_actually_detects(liability_clause):
    """Positive control for the detector the three tests above rely on.

    Without this, all three could pass because ``_party_nouns_present``
    silently matches nothing -- a broken regex, an emptied noun tuple, a
    bad word boundary. This feeds it text that MUST match, so a detector
    that can no longer detect fails here instead of reporting the page
    clean.
    """
    # Arrange: seed the real clause with the exact phrase that was removed,
    # so the detector is fed text it MUST match.
    seeded = liability_clause + " our directors, employees, or agents "
    # Act
    found = _party_nouns_present(seeded)
    # Assert
    assert {"directors", "employees", "agents"}.issubset(set(found)), (
        "_party_nouns_present did not find 'directors', 'employees' and "
        f"'agents' in text that contains all three (it returned {found!r}). "
        "The detector is broken, so the absence results reported by the "
        "other tests in this module are vacuous and prove nothing."
    )
