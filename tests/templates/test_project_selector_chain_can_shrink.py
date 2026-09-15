#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Every box between .header-left and the project name must be able to shrink.

WHY THIS TEST EXISTS, AND IT IS A CORRECTION TO #743.

#743 fixed the mobile hamburger (48px off-screen -> on-screen) and claimed it
ALSO made the project name truncate with an ellipsis instead of being clipped
mid-glyph. The first claim is true and verified on the deployed site. THE SECOND
WAS NOT SHIPPED.

The live experiment that justified #743 mutated FOUR elements. The PR carried
THREE. Measured on scitex.ai AFTER that deploy, at 390x844:

    state                                  inline  btn  txt  ELLIPSIS
    as deployed (#743)                       187   187  155   false
    + .header-project-selector-inline{mw:0}  115   115   83   TRUE
    reverted                                 187   187  155   false

So three correct declarations sat inert because ONE floor two levels up was
missing. `.header-project-selector-inline` is a flex item of `.header-left`; its
`min-width: auto` resolves to min-content, so it never narrows;
`.project-selector-btn { width: 100% }` then resolves against an un-narrowed
187px parent and returns 187px; the text span is never squeezed; and
`text-overflow: ellipsis` has no overflow to act on.

THE GENERAL RULE, which is why this file asserts the CHAIN rather than one rule:
the automatic-minimum floor must hold at EVERY level between the constrained
ancestor and the text. Zeroing the ends is not enough. A single `min-width: auto`
anywhere in between silently disables everything below it, and every individual
declaration still reads as correct in review.

This is the FOURTH instance of that rule in this codebase in one day:
    .apps-grid { grid-template-columns: 1fr }   -> track 797px        (#741)
    .header-left { min-width: auto }            -> nav 48px off-screen (#743)
    .project-selector-text { flex: 1 }          -> dead ellipsis       (#743)
    .header-project-selector-inline             -> THIS ONE, which made the
                                                   other two inert

SCOPE: source assertions. They prove the declarations survive in the
stylesheets; they cannot prove the pixels. The pixel evidence is in the commit
message and was taken against the deployed site, not a local build.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from django.conf import settings

#: One entry per box in the shrink chain, outermost first. The ORDER is the
#: documentation: each box must be able to narrow before the next one can.
CHAIN = (
    (
        "static/shared/css/components/header/02-layout.css",
        ".header-project-selector-inline",
        r"min-width\s*:\s*0",
        "flex item of .header-left; without a zero floor it stays at its "
        "min-content width and everything below it is inert",
    ),
    (
        "static/shared/css/components/header/12-project-selector.css",
        ".project-selector-text",
        r"min-width\s*:\s*0",
        "flex: 1 cannot take it below min-content without this, so its "
        "text-overflow: ellipsis never has an overflow to act on",
    ),
)

_DEFECT = (
    "the project name was clipped mid-glyph instead of ellipsised on mobile, "
    "because .header-project-selector-inline kept min-width: auto and so never "
    "narrowed -- leaving #743's other three declarations inert"
)


def _strip_css_comments(css: str) -> str:
    """Remove `/* ... */` before rule-body matching.

    A CSS comment may legally contain braces, and this change's own rationale
    quotes `{ grid-template-columns: 1fr }`. Without stripping, a `[^}]*` scan
    stops at the brace INSIDE the comment and reports a rule body that excludes
    the declaration under test.
    """
    return re.sub(r"/\*.*?\*/", "", css, flags=re.DOTALL)


def _rule_body(css: str, selector: str) -> str | None:
    match = re.search(re.escape(selector) + r"\s*\{([^}]*)\}", css)
    return match.group(1) if match else None


def _read(rel: str) -> str:
    return (Path(settings.BASE_DIR) / rel).read_text(encoding="utf-8")


@pytest.mark.parametrize(
    "rel,selector,pattern,why", CHAIN, ids=[c[1] for c in CHAIN]
)
@pytest.mark.guards(defect=_DEFECT)
def test_every_box_in_the_chain_can_shrink(rel, selector, pattern, why):
    """One assertion, run once per link — a failure names WHICH box is stuck."""
    # Arrange
    body = _rule_body(_strip_css_comments(_read(rel)), selector)
    normalized = re.sub(r"\s+", " ", body or "")

    # Act
    can_shrink = bool(re.search(pattern, normalized))

    # Assert
    assert can_shrink, (
        f"`{selector}` in {rel} cannot shrink: {why}. The whole chain must "
        "hold — zeroing only the ends leaves the middle box at its min-content "
        "width and silently disables every declaration below it. "
        f"Declarations found: {normalized!r}"
    )


@pytest.mark.guards(defect=_DEFECT)
def test_the_button_still_fills_its_parent():
    """The other half of the pair, shipped in #743 — assert it did not regress.

    `.project-selector-btn` is a <button>, and form controls are shrink-to-fit:
    `width: auto` resolves to max-content rather than to the containing block.
    `width: 100%` is what ties it to its parent. It is useless without the
    chain above, and the chain is useless without it, so a change that drops
    either one silently restores the defect.
    """
    # Arrange
    rel = "static/shared/css/components/header/14-responsive.css"
    body = _rule_body(_strip_css_comments(_read(rel)), ".project-selector-btn")
    normalized = re.sub(r"\s+", " ", body or "")

    # Act
    fills_parent = bool(re.search(r"width\s*:\s*100%", normalized))

    # Assert
    assert fills_parent, (
        f"`.project-selector-btn` in {rel} lost `width: 100%`. It is a "
        "<button>, so width:auto is max-content (187px measured) rather than "
        "its parent's width -- it overflows, and the shrink chain above it "
        f"cannot reach the text. Declarations found: {normalized!r}"
    )


# EOF
