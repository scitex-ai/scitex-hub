"""Prices live in data/pricing.json and nowhere else.

Operator decision 2026-08-01:「SSOT にしましょう」/「価格はjson あたりに」.

The bug this guards against is not a wrong number — it is TWO numbers. Before
the SSoT, ``/services/`` hard-coded nine JPY rows in its template and
``/landing/`` hard-coded twelve USD items in its view. Both were public, they
disagreed by up to 2.7x on the same service, and nothing could detect it
because each was individually self-consistent.

``test_price_scanner_matches_a_known_literal`` is the POSITIVE CONTROL for the
scanner. A "no literal prices anywhere" assertion passes for free the moment
the regex stops matching anything — a typo in the pattern would turn this file
into a check that can never fail, which is worse than not having it.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
PUBLIC_APP = REPO / "apps" / "infra" / "public_app"

# A literal money amount in source: 11,000円 / 110000円 / $299 / ¥33,000.
_PRICE_LITERAL = re.compile(r"(?:[$¥]\s?\d[\d,]*)|(?:\d[\d,]*\s?円)")

# Files that are ALLOWED to contain amounts: the SSoT itself, this test, and
# the module that formats them.
_ALLOWED = {"pricing.json", "test_pricing_ssot.py", "pricing.py"}

# EXEMPT, each with a written reason — never a blanket pattern. An exclusion
# nobody can justify is how a guard quietly stops guarding.
_EXEMPT = {
    # donate.html's $5/$15/$50/$500 are SUGGESTED DONATION AMOUNTS, not prices
    # for a service. They are a different fact-class from "what SciTeX charges"
    # and do not belong in pricing.json, which the /services/ and /landing/
    # tables read. If donation tiers ever start drifting between pages they
    # need their own SSoT — they do not get folded into this one to make a
    # scanner quiet.
    "donate.html",
}


def _scan_targets() -> list[Path]:
    """Public-facing templates and views that a visitor's price could come from."""
    targets: list[Path] = []
    targets.extend((PUBLIC_APP / "templates").rglob("*.html"))
    targets.extend((PUBLIC_APP / "views").rglob("*.py"))
    return [p for p in targets if p.name not in _ALLOWED | _EXEMPT]


@pytest.fixture(name="offenders")
def _offenders() -> list[str]:
    """Files that still hard-code a money amount."""
    targets = _scan_targets()
    if not targets:
        raise AssertionError(
            f"Found no templates or views to scan under {PUBLIC_APP}. The "
            "scanner is looking in the wrong place, so a clean result here "
            "would mean nothing."
        )
    found = []
    for path in targets:
        text = path.read_text(encoding="utf-8", errors="replace")
        for match in _PRICE_LITERAL.finditer(text):
            found.append(f"{path.relative_to(REPO)}: {match.group(0)!r}")
    return found


def test_price_scanner_matches_a_known_literal() -> None:
    """POSITIVE CONTROL — the pattern must actually match a real price string.

    Without this, a broken regex makes every other test in this file pass by
    matching nothing at all.
    """
    # Arrange
    sample = '<td class="svc-price-cell">11,000円</td>'
    # Act
    matched = _PRICE_LITERAL.search(sample)
    # Assert
    assert matched is not None, (
        "The price-literal pattern no longer matches a known price string, so "
        "the SSoT guard below cannot detect anything. Fix the pattern."
    )


def test_price_scanner_ignores_a_plain_number() -> None:
    """NEGATIVE CONTROL — the pattern must not fire on every integer."""
    # Arrange
    sample = '<div class="col-8">2026</div>'
    # Act
    matched = _PRICE_LITERAL.search(sample)
    # Assert
    assert matched is None, (
        "The price-literal pattern matches a bare number, so it would report "
        "false offenders and train everyone to ignore this guard."
    )


def test_every_exemption_is_still_earning_its_place() -> None:
    """An exemption for a file with no amounts left is dead config — delete it.

    Without this, ``_EXEMPT`` accumulates names forever and silently widens
    the hole in the guard as files change underneath it.
    """
    # Arrange
    stale = []
    for name in _EXEMPT:
        matches = list(PUBLIC_APP.rglob(name))
        if not matches or not any(
            _PRICE_LITERAL.search(p.read_text(encoding="utf-8", errors="replace"))
            for p in matches
        ):
            stale.append(name)
    # Act
    got = stale
    # Assert
    assert got == [], (
        "These _EXEMPT entries no longer correspond to a file containing a "
        f"money amount: {got}. Remove them — an exemption that exempts "
        "nothing is a hole in the guard that nobody is watching."
    )


def test_no_public_template_or_view_hardcodes_a_price(offenders: list[str]) -> None:
    """Every published price must come from data/pricing.json."""
    # Arrange
    expected: list[str] = []
    # Act
    got = offenders
    # Assert
    assert got == expected, (
        "These files hard-code a money amount instead of reading "
        "data/pricing.json:\n  " + "\n  ".join(got) + "\nMove the number into "
        "the SSoT and render it via public_app.pricing.pricing_rows()."
    )
