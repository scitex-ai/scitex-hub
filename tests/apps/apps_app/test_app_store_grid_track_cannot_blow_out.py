#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The app-store grid track must be `minmax(0, 1fr)`, never a bare `1fr`.

A bare `1fr` is shorthand for `minmax(auto, 1fr)`, and that automatic minimum
resolves to the GRID ITEM's min-content width. The track therefore cannot shrink
below the widest `.ap-card`, however narrow the grid itself is.

Measured on prod at 390x844, anonymous, before the fix:

    .apps-container   390px, overflow-x: hidden   (correct — the mobile cap)
    .apps-grid        362px                       (correct — width: 100%)
    grid track        796.95px                    <- the defect
    .ap-card          797px

`.apps-container` CLIPS, so the excess was not merely ugly, it was UNREACHABLE:
25 of 90 visible controls sat entirely past the clip edge — every card's star
button (292px beyond) and status trigger (326px beyond). No gesture reveals
them.

Changing only `grid-template-columns` in the live page: track 796.95 -> 362,
card 797 -> 362, unreachable controls 25 -> 1. Reverting restored all three, so
the declaration is the cause and not a coincidence. (The remaining 1 is the
hamburger, a separate header-overflow defect.)

This also explains why the existing mobile work did NOT land. Capping the
container and the grid's outer width leaves the TRACK free to size to content,
and `.ap-card { flex-wrap: wrap }` in cards.css then wraps inside a 797px box —
correct rules, no visible effect, because both sat downstream of this floor.
That is why `test_mobile_container_cap_survives` is here: the cap is
load-bearing and must not be deleted on the theory that this fix replaced it.

SCOPE, stated plainly: these are SOURCE assertions. They prove the declarations
survive in the stylesheet; they cannot prove the pixels. The pixel evidence is
the before/after/revert triple above and in the commit message. A rendering
guard would need a browser at 390px, which this suite does not have.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from django.conf import settings

CSS_REL = "apps/workspace/apps_app/static/apps_app/css/apps/layout.css"

# The breakpoint that pins the store to the phone viewport. Load-bearing, and
# not the fix under test — see the module docstring.
MOBILE_BREAKPOINT = "@media (max-width: 640px)"


def _css_text():
    return (Path(settings.BASE_DIR) / CSS_REL).read_text(encoding="utf-8")


def _rule_body(css, selector):
    """The declaration body of `selector { ... }`, or None.

    Anchored on a `{` that follows the selector directly so `.apps-grid` cannot
    match `.apps-grid-empty` or a compound selector that merely contains it.
    """
    pattern = re.escape(selector) + r"\s*\{([^}]*)\}"
    match = re.search(pattern, css)
    return match.group(1) if match else None


@pytest.fixture
def css_text():
    return _css_text()


@pytest.fixture
def apps_grid_declarations(css_text):
    return _rule_body(css_text, ".apps-grid")


def test_stylesheet_is_present_and_non_trivial(css_text):
    """Anti-vacuity: every assertion below reads this file."""
    # Arrange
    minimum_length = 1000

    # Act
    length = len(css_text)

    # Assert
    assert length > minimum_length, (
        f"{CSS_REL} parsed as {length} chars, expected more than "
        f"{minimum_length}. If the stylesheet moved, update CSS_REL — do not "
        "delete this test, or the checks below would pass on an empty string."
    )


def test_apps_grid_rule_exists(apps_grid_declarations):
    """Anti-vacuity: a missing rule must fail loudly, not read as compliant."""
    # Arrange
    expected_present = True

    # Act
    is_present = apps_grid_declarations is not None

    # Assert
    assert is_present == expected_present, (
        f"no `.apps-grid {{ ... }}` rule in {CSS_REL}. Either it moved (update "
        "this test) or it was deleted (the app-store grid track is now "
        "unguarded and can blow out again)."
    )


def test_grid_track_has_a_zero_minimum(apps_grid_declarations):
    """The declaration that lets the track shrink to the phone viewport."""
    # Arrange
    normalized = re.sub(r"\s+", " ", apps_grid_declarations or "")

    # Act
    has_zero_minimum = bool(
        re.search(r"grid-template-columns\s*:\s*minmax\(\s*0\s*,", normalized)
    )

    # Assert
    assert has_zero_minimum, (
        "`.apps-grid` does not declare `grid-template-columns: minmax(0, 1fr)`. "
        "A bare `1fr` means `minmax(auto, 1fr)`, whose automatic minimum is the "
        "widest .ap-card's min-content width, so the track cannot shrink below "
        "it. Measured consequence at 390px: track 796.95px, card 797px, and 25 "
        "of 90 controls clipped out of reach by .apps-container's "
        f"overflow-x: hidden. Declarations found: {normalized!r}"
    )


def test_grid_track_is_not_a_bare_fr(apps_grid_declarations):
    """Reject the exact regression, not merely the absence of the fix.

    Separate from the test above because a future edit could add a second
    `grid-template-columns` line and leave the bare `1fr` winning by cascade
    order — that would satisfy "contains minmax(0," while rendering the defect.
    """
    # Arrange
    normalized = re.sub(r"\s+", " ", apps_grid_declarations or "")

    # Act
    bare_fr_declarations = re.findall(
        r"grid-template-columns\s*:\s*1fr\s*;", normalized
    )

    # Assert
    assert bare_fr_declarations == [], (
        "`.apps-grid` still carries a bare `grid-template-columns: 1fr`, which "
        "resolves to minmax(auto, 1fr) and re-introduces the min-content floor. "
        f"Found: {bare_fr_declarations!r} in {normalized!r}"
    )


def test_mobile_container_cap_survives(css_text):
    """The <=640px cap is load-bearing and independent of the track fix.

    It bounds .apps-container to the viewport and clips the residual. Without
    it the store sizes to content again — a different route to the same
    user-facing defect, so removing it must fail here rather than silently.
    """
    # Arrange
    expected_present = True

    # Act
    is_present = MOBILE_BREAKPOINT in css_text and "width: 100vw" in css_text

    # Assert
    assert is_present == expected_present, (
        f"the {MOBILE_BREAKPOINT} block pinning .apps-container to "
        f"`width: 100vw` is gone from {CSS_REL}. It is NOT superseded by "
        "minmax(0, 1fr): the track fix stops the card from forcing the track "
        "wider, the cap stops the store column from sizing to content. Both "
        "are needed; each hides the other's absence on a wide screen."
    )


# EOF
