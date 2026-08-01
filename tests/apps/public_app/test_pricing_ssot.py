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

# Already reading from data/pricing.json. These must stay at ZERO literals.
_MIGRATED = {"services.html"}

# The un-migrated backlog, as measured 2026-08-02. ONLY EVER LOWER THIS.
#   pricing.html  18  — blocked on which future ladder is real
#                       ($16/$32/$64 vs $29-$999); both are currently published
#   landing.py     6  — blocked on the FX/USD decision. Note a hard-coded
#                       exchange rate becomes a SECOND price the moment it ages,
#                       which is the very bug this file exists to prevent, so
#                       "just convert the JPY" is not automatically the fix.
# When a page migrates, drop this number in the same commit. Raising it to make
# a build green is the mask growing, not the gate passing.
MAX_REMAINING_LITERALS = 24

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


def test_migrated_files_have_no_price_literals(offenders: list[str]) -> None:
    """A file that has been migrated must never regain a literal.

    This is the half that must be exactly zero. Everything named in
    ``_MIGRATED`` reads from data/pricing.json today; a literal reappearing
    there is a regression, not inherited debt.
    """
    # Arrange
    regressions = [o for o in offenders if any(m in o for m in _MIGRATED)]
    # Act
    got = regressions
    # Assert
    assert got == [], (
        "A migrated file hard-codes a money amount again:\n  "
        + "\n  ".join(got)
        + "\nRender it via public_app.pricing instead. If the page genuinely "
        "needs a new kind of amount, add it to data/pricing.json."
    )


def test_remaining_literals_do_not_grow(offenders: list[str]) -> None:
    """The un-migrated backlog ratchets DOWN, never up.

    Mirrors tests/develop/test_audit.py's masked-violation ceiling, and carries
    the same rule: when this fails, migrate a page — do NOT raise the ceiling.
    Raising it is the mask growing, not the gate passing.
    """
    # Arrange
    ceiling = MAX_REMAINING_LITERALS
    # Act
    remaining = len(offenders)
    # Assert
    assert remaining <= ceiling, (
        f"{remaining} hard-coded prices remain (ceiling {ceiling}). The "
        "backlog grew. Move the new amount into data/pricing.json rather than "
        "raising MAX_REMAINING_LITERALS."
    )
