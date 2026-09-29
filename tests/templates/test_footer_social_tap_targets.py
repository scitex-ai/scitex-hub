#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The footer social links must be targets, not glyphs.

Card: fix-footer-social-tap-targets-20260917 (D1 from the baseline audit
gui-baseline-scitex-hub-20260917).

Measured on the running Hub at 390x844 (chromium, DPR3) before this fix:
`/landing/` and `/pricing/` rendered the six `.footer-social a` links at
12x21, 12x21, 12x21, 13x21, 13x21 and 15x21 px, with their nearest neighbouring
target only 19-21px away. That fails WCAG 2.2 SC 2.5.8 (Target Size Minimum, AA)
on both of its tests: the 24x24 CSS px minimum AND the spacing exception, which
needs at least 24px clear of any other target.

Root cause: `.footer-social a` set only color, text-decoration, font-size and
transition, so the hit box was the icon glyph itself.

These are stylesheet-contract assertions, which is what can be checked without a
running app; the behavioural proof is the measured before/after in the card's
evidence (chromium against the real page, with the patched sheet applied).
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
FOOTER_CSS = REPO / "static/shared/css/components/footer.css"
COMMON_CSS = REPO / "static/shared/css/common.css"

# The floor from the standard, in CSS px.
WCAG_TARGET_MIN = 24
# The platform's own touch-target floor for the shell (SSOT §4).
PLATFORM_TAP_MIN = 44


def _css() -> str:
    return FOOTER_CSS.read_text()


def _block(css: str, selector: str, *, nth: int = 1) -> str:
    """Return the nth rule body for ``selector`` (declarations only)."""
    pattern = re.compile(re.escape(selector) + r"\s*\{([^}]*)\}")
    matches = pattern.findall(css)
    assert len(matches) >= nth, f"{selector!r} rule #{nth} not found in footer.css"
    return matches[nth - 1]


def _px(block: str, prop: str) -> int:
    m = re.search(rf"{prop}\s*:\s*(\d+)px", block)
    assert m, f"{prop} with a px value not found in {block!r}"
    return int(m.group(1))


def test_footer_css_is_actually_loaded():
    """A rule in a stylesheet nobody imports renders nothing.

    footer.css reaches a browser through common.css's @import; landing-hero-demo.css
    was the counter-example (imported by nothing, its rules never applied).
    """
    assert COMMON_CSS.is_file(), "common.css moved — update this guard"
    assert "components/footer.css" in COMMON_CSS.read_text(), (
        "footer.css is no longer imported by common.css; the rules below would "
        "never reach a browser"
    )


def test_the_social_links_are_boxed_to_the_standard_minimum():
    block = _block(_css(), ".footer-social a")

    assert "inline-flex" in block, (
        "the link must lay out as a box; as an inline glyph the hit area is the icon"
    )
    assert _px(block, "min-width") >= WCAG_TARGET_MIN, (
        f"min-width must be >= {WCAG_TARGET_MIN}px (WCAG 2.2 SC 2.5.8)"
    )
    assert _px(block, "min-height") >= WCAG_TARGET_MIN, (
        f"min-height must be >= {WCAG_TARGET_MIN}px (WCAG 2.2 SC 2.5.8)"
    )


def test_the_phone_width_rule_raises_them_to_the_platform_tap_floor():
    """At the width where thumbs are, 24px is not enough."""
    css = _css()
    # The mobile rule lives inside a max-width media query; assert both the rule
    # and that it is scoped to a narrow width rather than applied everywhere.
    mobile_blocks = re.findall(
        r"@media[^{]*max-width:\s*(\d+)px[^{]*\{(.*?)\n\}", css, re.S
    )
    assert mobile_blocks, "no max-width media query found in footer.css"

    hits = []
    for width, body in mobile_blocks:
        if re.search(r"\.footer-social a\s*\{", body):
            scoped = re.search(r"\.footer-social a\s*\{([^}]*)\}", body)
            assert scoped
            hits.append((int(width), scoped.group(1)))

    assert hits, "no phone-width rule for .footer-social a"
    width, block = hits[0]
    assert width <= 768, f"the rule is scoped to {width}px, which is not a phone width"
    assert _px(block, "min-width") >= PLATFORM_TAP_MIN
    assert _px(block, "min-height") >= PLATFORM_TAP_MIN


def test_the_gap_between_social_links_is_not_negative_space():
    """Boxes must not overlap or collapse into each other."""
    css = _css()
    block = _block(css, ".footer-social")
    m = re.search(r"gap\s*:\s*([^;]+);", block)
    assert m, ".footer-social no longer declares a gap"
    gap = m.group(1).strip()
    assert "0" != gap, "a zero gap makes adjacent targets touch"


# EOF
