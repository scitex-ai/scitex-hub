#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The mobile header row must be able to shrink, or the primary nav leaves screen.

THE DEFECT THESE GUARD. On a 390x844 phone viewport the hamburger button --
the PRIMARY NAVIGATION CONTROL, and the only route to the mobile menu --
rendered 48px past the right edge of the viewport.

`.global-header-inner` is `display: flex; flex-wrap: nowrap` with 364px of
content box at 390px. Measured on prod, /apps/store/, mobile UA, anonymous:

    .header-left                  253px   flex 0 1 auto   min-width auto
    .header-visitor-badge-mobile  142px   flex 0 1 auto   min-width auto
    .mobile-hamburger              15px   flex 0 1 auto   min-width auto
    + 2 gaps                      ----
                                  426px   against 364px available

Every child is `flex-shrink: 1` AND `min-width: auto`. On a flex item the
automatic minimum is its MIN-CONTENT size, so flex-shrink cannot act. Nothing
shrinks, the row stays 438px, and the hamburger -- last in source order --
absorbs the whole overflow. The document then scrolls horizontally by 48px.

This is the SAME MECHANISM as `.apps-grid { grid-template-columns: 1fr }`
(= `minmax(auto, 1fr)`, automatic minimum = min-content), fixed in #741 and
guarded by tests/apps/apps_app/test_app_store_grid_track_cannot_blow_out.py.
Two layout modes, two pages, one root cause: a shrinkable box whose automatic
minimum was never zeroed.

WHY `overflow: hidden` IS PART OF THE FIX AND NOT DECORATION. `min-width: 0`
alone is a WORSE bug than the one it fixes: it shrinks `.header-left`'s BOX to
181px while its CONTENT stays 253px, so the project selector paints on top of
the visitor badge. That is invisible to getBoundingClientRect(), which reports
BOXES -- the box overlap measures 65px with and without the clip, so the
obvious metric would reject the correct fix. `document.elementFromPoint()`
answers the paint question because it respects clipping; five probes across the
badge showed 2 of 5 points painted by `.header-left` under `min-width: 0`
alone, and 0 of 5 once clipped.

SCOPE, STATED PLAINLY: these are SOURCE assertions. They prove the declarations
survive in the stylesheet. They cannot prove the pixels, and a regression
arriving from another stylesheet or a scitex-ui shell upgrade would pass here.

The pixels belong in tests/e2e/playwright/. Note the state of that suite when
this was written: every test in it was SKIPPED in CI from 2026-03-30 until
2026-09-06 because the workflow stopped passing `--browser`, so the job was
green having executed nothing (PR #742). A source guard that runs is worth
more than a pixel guard that does not -- but the pixel guard is the real one,
and this file is not a substitute for it.

KNOWN RESIDUE, DELIBERATELY NOT FIXED HERE. The clip cuts the project name at
an arbitrary pixel instead of ellipsising it. `.project-selector-text` already
declares `overflow: hidden; text-overflow: ellipsis; white-space: nowrap`, so
the machinery exists -- it never fires because the squeeze never reaches it.
Measured: with `min-width: 0` on both `.header-left` and
`.header-project-selector-inline`, the inline box shrinks 187 -> 115 while
`.project-selector-btn` stays 187 and overflows. Making the ellipsis fire is a
separate change against a separate rule. An off-screen primary nav is a P1; a
mid-glyph clip is cosmetic; holding the former for the latter is the wrong
trade.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from django.conf import settings

#: The stylesheet under test, relative to BASE_DIR.
CSS_REL = "static/shared/css/components/header/14-responsive.css"

#: The rule that carries the fix. Written out rather than imported: this is a
#: selector the templates depend on, and asserting it against a constant that
#: produces it would keep passing through a rename that broke the page.
SELECTOR = ".header-left"

#: The breakpoint the fix is scoped to. The mobile header (hamburger + visitor
#: badge) is only assembled below this width, so the rule must live inside it.
MOBILE_BREAKPOINT = "@media (max-width: 768px)"

_DEFECT = (
    "the mobile hamburger -- the primary navigation control -- rendered 48px "
    "off the right edge at 390x844, because every child of "
    ".global-header-inner has min-width: auto and so cannot shrink"
)


def _strip_css_comments(css: str) -> str:
    """Remove `/* ... */` blocks before any rule-body matching.

    NOT cosmetic. Rule bodies are extracted with a `[^}]*` scan, and a CSS
    comment may legally contain braces -- this file's own comment quotes
    `.apps-grid { grid-template-columns: 1fr }`. Without this step the scan
    would stop at the brace INSIDE the comment and report a rule body that
    excludes the declarations under test, i.e. a test that fails for a reason
    having nothing to do with the page.
    """
    return re.sub(r"/\*.*?\*/", "", css, flags=re.DOTALL)


def _css_text() -> str:
    return (Path(settings.BASE_DIR) / CSS_REL).read_text(encoding="utf-8")


def _rule_body(css: str, selector: str) -> str | None:
    match = re.search(re.escape(selector) + r"\s*\{([^}]*)\}", css)
    return match.group(1) if match else None


@pytest.fixture
def css_text() -> str:
    return _css_text()


@pytest.fixture
def header_left_declarations(css_text: str) -> str | None:
    return _rule_body(_strip_css_comments(css_text), SELECTOR)


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


def test_comment_stripper_retains_real_declarations(css_text):
    """Control for the helper itself, which is the only novel machinery here.

    A stripper with a greedy `.*` swallows everything between the FIRST `/*`
    and the LAST `*/` — the whole stylesheet, in a file that opens with a
    comment. Every assertion below would then read an empty rule body and fail
    with a message blaming the CSS instead of the helper.

    An earlier version of this control asserted a RETAINED-BYTES RATIO above
    50%, and it failed on its first run: this file is now majority-comment,
    because the fix's own rationale block is ~70 lines. The ratio was encoding
    an assumption about comment DENSITY, which is nobody's contract and which
    the change under test invalidated. Asserting the PROPERTY — a declaration
    outside any comment survives — tests the helper instead.
    """
    # Arrange — present in this rule both before and after the fix, so the
    # control does not move when the fix lands.
    known_declaration = "gap: 8px"

    # Act
    survives = known_declaration in _strip_css_comments(css_text)

    # Assert
    assert survives, (
        f"_strip_css_comments removed {known_declaration!r} from {CSS_REL}, so "
        "it is eating real declarations and every assertion below is measuring "
        "the stripper rather than the stylesheet."
    )


def test_comment_stripper_actually_removes_comment_text(css_text):
    """The other half: a no-op stripper would also pass the test above.

    Separate test because the two failures mean opposite things — one says the
    helper is too greedy, the other says it does nothing. A helper that
    returned its input unchanged would satisfy the retention control while
    leaving the brace-in-a-comment problem it exists to solve.
    """
    # Arrange — this phrase appears only inside the fix's rationale comment.
    comment_only_phrase = "min-content"

    # Act
    removed = comment_only_phrase not in _strip_css_comments(css_text)

    # Assert
    assert removed, (
        f"_strip_css_comments left {comment_only_phrase!r} in {CSS_REL}, a "
        "phrase that appears only inside a comment. The helper is not "
        "stripping, so a brace inside a comment will truncate every rule body "
        "read below."
    )


def test_header_left_rule_exists(header_left_declarations):
    """Anti-vacuity: a missing rule must fail loudly, not read as compliant."""
    # Arrange
    expected_present = True

    # Act
    is_present = header_left_declarations is not None

    # Assert
    assert is_present == expected_present, (
        f"no `{SELECTOR} {{ ... }}` rule in {CSS_REL}. Either it moved (update "
        "this test) or it was deleted, in which case the mobile header row is "
        "unguarded and the hamburger can leave the viewport again."
    )


@pytest.mark.guards(defect=_DEFECT)
def test_header_left_has_a_zero_minimum(header_left_declarations):
    """The declaration that lets the header row shrink to the phone viewport."""
    # Arrange
    normalized = re.sub(r"\s+", " ", header_left_declarations or "")

    # Act
    has_zero_minimum = bool(re.search(r"min-width\s*:\s*0", normalized))

    # Assert
    assert has_zero_minimum, (
        f"`{SELECTOR}` does not declare `min-width: 0`. Its automatic minimum "
        "is then its min-content width, so flex-shrink cannot act and the "
        "438px header row cannot fit 390px. Measured consequence: the "
        "hamburger renders 48px off-screen and the document scrolls "
        f"horizontally. Declarations found: {normalized!r}"
    )


@pytest.mark.guards(defect=_DEFECT)
def test_header_left_clips_its_overflow(header_left_declarations):
    """Without this, the fix above RELOCATES the defect instead of curing it.

    Separate test from the zero-minimum one, because the two failures need
    different responses: a missing `min-width: 0` means the hamburger is
    off-screen, a missing `overflow: hidden` means the project selector is
    painted on top of the visitor badge. A single combined assertion would
    report the wrong one half the time.
    """
    # Arrange
    normalized = re.sub(r"\s+", " ", header_left_declarations or "")

    # Act
    clips = bool(re.search(r"overflow\s*:\s*hidden", normalized))

    # Assert
    assert clips, (
        f"`{SELECTOR}` declares a zero minimum without `overflow: hidden`. "
        "Its BOX then shrinks to 181px while its CONTENT stays 253px, and the "
        "project selector paints over the visitor badge — measured as 2 of 5 "
        "hit-test points inside the badge returning .header-left. Note the box "
        "overlap is 65px either way, so getBoundingClientRect cannot see this; "
        f"only elementFromPoint can. Declarations found: {normalized!r}"
    )


@pytest.mark.guards(defect=_DEFECT)
def test_the_fix_is_scoped_to_the_mobile_breakpoint(css_text):
    """`overflow: hidden` on the desktop header would clip working UI.

    The rule is only correct where the compact mobile header is assembled. If
    a future edit hoists it out of the media query, the desktop header starts
    clipping content that has room to render — a new defect wearing this fix's
    clothes.
    """
    # Arrange
    stripped = _strip_css_comments(css_text)
    breakpoint_at = stripped.find(MOBILE_BREAKPOINT)
    rule_at = stripped.find(SELECTOR + " {")

    # Act
    is_scoped = breakpoint_at != -1 and rule_at > breakpoint_at

    # Assert
    assert is_scoped, (
        f"the `{SELECTOR}` fix is not inside `{MOBILE_BREAKPOINT}` in "
        f"{CSS_REL} (breakpoint at {breakpoint_at}, rule at {rule_at}). "
        "Applied unconditionally, `overflow: hidden` clips the desktop header "
        "where nothing needed clipping."
    )


# EOF
