#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The mobile hero CTA must stack, not sit beside its own caption.

`.hero-cta` has TWO children — `.hero-cta-container` (the buttons) and
`.hero-cta-note` ("No sign-up needed…"). Inside the <=992px media query it is
`display: flex`, so WITHOUT an explicit `flex-direction: column` they lay out as
a row and the button column is starved to its min-content width.

Measured on prod at 390x844 before the fix: container 106px wide, note 208px
beside it, and the primary CTA wrapped onto three lines ("Enter" / "as" /
"visitor"). After adding column: CTA 106->164 wide, 88->43 tall (one line), note
moved below at full width.

That failure also silently defeated `.hero-cta-button { width: 100% }` in
landing/15-responsive.css — 100% of a starved parent is still starved — so
someone had already tried to fix this at the wrong level. A source guard is
cheap insurance that the declaration is not dropped again.

This is a SOURCE assertion, not a rendering test: it cannot prove the pixels,
only that the rule survives. The pixel evidence lives in the commit message.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from django.conf import settings

CSS_REL = "apps/infra/public_app/static/public_app/css/landing-hero-fix.css"

# The breakpoint that governs tablet+phone. .hero-cta's row-flex bug lived here.
MOBILE_BREAKPOINT = "@media (max-width: 992px)"


def _css_text():
    return (Path(settings.BASE_DIR) / CSS_REL).read_text(encoding="utf-8")


def _mobile_block(css):
    """Return the text of the <=992px media block, brace-matched.

    Brace-counted rather than regex-sliced so a nested rule cannot end the block
    early and silently shorten what the assertions below inspect.
    """
    start = css.find(MOBILE_BREAKPOINT)
    if start == -1:
        return ""
    i = css.find("{", start)
    if i == -1:
        return ""
    depth = 0
    for j in range(i, len(css)):
        if css[j] == "{":
            depth += 1
        elif css[j] == "}":
            depth -= 1
            if depth == 0:
                return css[i : j + 1]
    return ""


def _hero_cta_rule(block):
    """The `.hero-cta { ... }` declaration body inside the given block.

    Anchored so it cannot match `.hero-cta-container` / `.hero-cta-note` /
    `.hero-cta-button`, which are different selectors with different jobs.
    """
    m = re.search(r"\.hero-cta\s*\{([^}]*)\}", block)
    return m.group(1) if m else None


@pytest.fixture
def mobile_block():
    return _mobile_block(_css_text())


@pytest.fixture
def hero_cta_declarations(mobile_block):
    return _hero_cta_rule(mobile_block)


def test_mobile_media_block_is_present(mobile_block):
    """Anti-vacuity: every later assertion reads this block."""
    # Arrange
    minimum_length = 200

    # Act
    length = len(mobile_block)

    # Assert
    assert length > minimum_length, (
        f"the {MOBILE_BREAKPOINT} block in {CSS_REL} parsed as {length} chars, "
        f"expected more than {minimum_length}. If the breakpoint was renamed, "
        "update MOBILE_BREAKPOINT — do not delete this test, or the checks "
        "below would pass on an empty string."
    )


def test_hero_cta_rule_exists_in_mobile_block(hero_cta_declarations):
    """Anti-vacuity: a missing rule must fail loudly, not read as compliant."""
    # Arrange
    expected_present = True

    # Act
    is_present = hero_cta_declarations is not None

    # Assert
    assert is_present == expected_present, (
        f"no `.hero-cta {{ ... }}` rule inside {MOBILE_BREAKPOINT} of {CSS_REL}. "
        "Either it moved (update this test) or it was deleted (the mobile CTA "
        "layout is now unguarded)."
    )


def test_hero_cta_stacks_as_column_on_mobile(hero_cta_declarations):
    """The declaration that keeps the primary CTA on one line."""
    # Arrange
    normalized = re.sub(r"\s+", " ", hero_cta_declarations or "")

    # Act
    has_column = "flex-direction: column" in normalized

    # Assert
    assert has_column, (
        "`.hero-cta` inside the <=992px media query is display:flex WITHOUT "
        "flex-direction: column, so .hero-cta-container and .hero-cta-note lay "
        "out as a ROW; the button column starves to ~106px and 'Enter as "
        f"visitor' wraps onto three lines. Declarations found: {normalized!r}"
    )


# EOF
