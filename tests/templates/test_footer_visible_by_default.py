#!/usr/bin/env python3
"""The footer must be VISIBLE by default and hidden only where the app shell renders.

Card hub-footer-hidden-everywhere-but-landing-legal-links-invisible-20260803.

WHY THIS FILE EXISTS — a bug that every check we had reported as PASSING.

`workspace-layout.css` used to hide the footer globally and restore it for one
allow-listed page:

    .global-footer, .site-footer   { display: none !important; }
    body.landing-page .site-footer { display: block !important; }

Deny-by-default with a single exception means every page that is not /landing/
ships an invisible footer, and every NEW page inherits that silently. Measured on
prod 2026-08-03:

    https://scitex.ai/pricing/   <body ... class="">          <- nothing restores it
    https://scitex.ai/landing/   <body ... class="workspace-page landing-page">
    both pages: id="site-footer" present; /pricing/ also carried 特定商取引 x2

So /pricing/ — the page where a customer decides to pay — served its Terms,
Privacy, Cookies and 特定商取引法に基づく表記 links inside a `display:none`
element. That notice is a statutory disclosure for paid services in Japan and
payment processors check for it.

WHY EVERY EXISTING GUARD STAYED GREEN — this is the part worth keeping:
the markup was always present. A template test, a link checker, a curl grep for
`id="site-footer"`, and a 200-status assertion ALL pass while the footer is
invisible. Presence is not visibility. So these tests assert on the CASCADE —
which body classes the hide selector actually matches — because that is the
thing that decides whether a human can see the link.

Note the shape of the sibling failure in test_body_class_landing_page.py: there,
`landing-page` was applied to a page that IS the app shell and collapsed it to
0x0. Both bugs are the same root cause — one class ("landing-page") carrying two
opposite meanings, "hide the app shell" AND "show the footer". The fix keys the
footer rule on `workspace-page` instead, so each class means one thing.

WHAT THIS MODEL DOES AND DOES NOT DO — state it plainly, because a reader who
mistakes it for a cascade engine will trust it too far. It collects `display:none`
rules targeting the footer element and asks which body classes they match. It
does NOT evaluate specificity, source order, or `display:block` overrides. So a
file that hides the footer globally and restores it by exception is reported as
HIDDEN even on the restored page.

That is deliberate, not a gap: hide-globally-restore-by-exception IS the bug this
file exists to prevent, so the model is built to fail on it. Concretely, run
against the pre-fix CSS this suite goes 3 failed / 8 passed, and one of those
three (`test_footer_is_visible_on_landing`) fails for that modelling reason
rather than because landing was actually broken — landing did render its footer
before this change. The two that carry the real signal are
`test_footer_is_visible_on_public_pages` and
`test_no_unscoped_rule_hides_the_footer_everywhere`.

If a future change legitimately needs an override-based rule here, this model is
the wrong tool and should be replaced with a real cascade evaluation — do not
weaken the assertions to fit it.

No mocks. One assertion per test (STX-TQ007).
"""

import re
from pathlib import Path

import pytest
from django.conf import settings

CSS_RULE_PATH = "static/shared/css/components/workspace-layout.css"

# Body classes as emitted by templates/global_base.html:73, per branch.
# The empty string is the one that mattered: /pricing/, /terms/, /privacy/,
# /docs/ and every other public page fall through every {% elif %} with no
# {% else %}, so they carry NO class at all.
PUBLIC_PAGE_CLASSES = frozenset()
LANDING_CLASSES = frozenset({"workspace-page", "landing-page"})
AUTHED_ROOT_CLASSES = frozenset({"workspace-page", "no-transition", "app-home"})
MODULE_CLASSES = frozenset({"workspace-page", "writer-module", "no-transition"})
EXPLORE_CLASSES = frozenset({"workspace-page", "explore-page"})


def _css_text() -> str:
    path = Path(settings.BASE_DIR) / CSS_RULE_PATH
    return path.read_text(encoding="utf-8")


# The footer ELEMENT, not merely any class containing the word "footer".
# Matching the substring instead cost a false failure the first time this file
# ran: `body.workspace-page .footer-collapse-toggle { display:none }` is a
# collapse BUTTON, and counting it reported the footer as hidden on /landing/,
# where it is plainly shown. Worse, it made the "is hidden" tests pass for the
# wrong reason. Key on the element the rule actually targets.
FOOTER_ELEMENT = re.compile(r"\.(?:site|global)-footer\b")


def _footer_hiding_selectors(css: str) -> list[str]:
    """Selectors in this file that set `display:none` on the footer ELEMENT.

    Comment blocks are stripped first — this file documents the OLD rules inside
    a comment so the next reader understands what changed, and a naive scan would
    match that prose and report the bug as still present.
    """
    without_comments = re.sub(r"/\*.*?\*/", "", css, flags=re.DOTALL)
    hiding = []
    for block in re.finditer(r"([^{}]+)\{([^{}]*)\}", without_comments):
        selector, body = block.group(1).strip(), block.group(2)
        # A group selector may mix the footer with unrelated elements; keep only
        # the comma-separated parts that target the footer itself.
        parts = [p for p in selector.split(",") if FOOTER_ELEMENT.search(p)]
        if not parts:
            continue
        if re.search(r"display\s*:\s*none", body):
            hiding.extend(" ".join(p.split()) for p in parts)
    return hiding


def _selector_matches(selector: str, body_classes: frozenset) -> bool:
    """Does this selector's `body...` prefix match a <body> carrying these classes?

    Only the shapes this file actually uses are supported — bare `.site-footer`,
    `body.X .site-footer`, and `body.X:not(.Y) .site-footer`. Anything else raises
    rather than silently returning False, because a quietly-unmatched selector is
    how a hide rule would slip past this guard.
    """
    head = selector.split()[0]
    if not head.startswith("body"):
        # An unscoped rule like `.site-footer` applies to every page.
        return True
    required = set(re.findall(r"(?<!not\()\.([a-zA-Z0-9_-]+)", head))
    excluded = set(re.findall(r":not\(\.([a-zA-Z0-9_-]+)\)", head))
    required -= excluded
    if not required and not excluded:
        raise AssertionError(f"unsupported selector shape, extend this helper: {selector!r}")
    return required <= set(body_classes) and not (excluded & set(body_classes))


def _footer_hidden_for(body_classes: frozenset) -> bool:
    return any(
        _selector_matches(sel, body_classes)
        for sel in _footer_hiding_selectors(_css_text())
    )


def test_css_file_declares_footer_hiding_rules():
    """POSITIVE CONTROL: the parser finds rules at all.

    Without this, every assertion below passes vacuously the moment the parser
    breaks or the file is renamed — 'no hide rules match' would read as 'the
    footer is visible everywhere', which is the answer we want to hear.
    """
    # Arrange
    css = _css_text()
    # Act
    selectors = _footer_hiding_selectors(css)
    # Assert
    assert selectors


def test_footer_is_visible_on_public_pages():
    """THE BUG. /pricing/, /terms/, /privacy/ carry no body class at all."""
    # Arrange
    classes = PUBLIC_PAGE_CLASSES
    # Act
    hidden = _footer_hidden_for(classes)
    # Assert
    assert not hidden


def test_footer_is_visible_on_landing():
    """Unchanged behaviour — #499/#501 fixed this and it must stay fixed."""
    # Arrange
    classes = LANDING_CLASSES
    # Act
    hidden = _footer_hidden_for(classes)
    # Assert
    assert not hidden


def test_footer_is_visible_on_the_app_home():
    """CHANGED DELIBERATELY 2026-08-10, on the operator's report.

    This previously asserted the footer was HIDDEN at `/` when signed in, on
    the reasoning that the app shell owns the viewport. That reasoning holds
    for workspace surfaces and still does -- see the module/workspace/explore
    tests below, which are unchanged.

    It does not hold for the launcher. The operator reported that without a
    footer there is no route to the 特定商取引法 disclosure, the policy pages
    or contact details:

        「フッターがないとですね。あの特商法の表示がとか法律がとか
          後は連絡先がとかってわかりにくいんで」

    Those pages all exist (public_app/urls/pages.py:44-51); the footer was the
    only thing linking them, and it was hidden on the one screen a signed-in
    user lands on. Reachability of a statutory disclosure outranks giving the
    launcher the whole viewport, so `.app-home` is excluded from the hide rule.

    The signed-in launcher now carries `workspace-page no-transition app-home`.
    """
    # Arrange
    classes = AUTHED_ROOT_CLASSES
    # Act
    hidden = _footer_hidden_for(classes)
    # Assert
    assert not hidden


def test_footer_stays_hidden_on_a_workspace_page_without_the_app_home_marker():
    """The exclusion must be the LAUNCHER, not `workspace-page` generally.

    Guards the obvious over-correction: widening the escape hatch until every
    app-shell surface shows the footer, which is the bug the sibling
    `test_body_class_landing_page.py` records from the other direction.
    """
    # Arrange
    classes = AUTHED_ROOT_CLASSES - {"app-home"}
    # Act
    hidden = _footer_hidden_for(classes)
    # Assert
    assert hidden


def test_footer_is_hidden_on_module_pages():
    """Unchanged behaviour."""
    # Arrange
    classes = MODULE_CLASSES
    # Act
    hidden = _footer_hidden_for(classes)
    # Assert
    assert hidden


def test_footer_is_hidden_on_explore():
    """Unchanged behaviour."""
    # Arrange
    classes = EXPLORE_CLASSES
    # Act
    hidden = _footer_hidden_for(classes)
    # Assert
    assert hidden


def test_no_unscoped_rule_hides_the_footer_everywhere():
    """The root cause, asserted directly.

    An unscoped `.site-footer { display:none }` is what made every non-landing
    page ship an invisible footer. Keeping this as its own test means a future
    reintroduction fails with the reason, not just a downstream symptom.
    """
    # Arrange
    css = _css_text()
    # Act
    unscoped = [
        sel
        for sel in _footer_hiding_selectors(css)
        if not sel.split()[0].startswith("body")
    ]
    # Assert
    assert unscoped == []


@pytest.mark.parametrize(
    "classes",
    [LANDING_CLASSES, AUTHED_ROOT_CLASSES, MODULE_CLASSES, EXPLORE_CLASSES],
)
def test_every_app_shell_variant_carries_workspace_page(classes):
    """The fix keys on `workspace-page`, so this must hold or the scoping is wrong.

    If a shell page ever ships without `workspace-page`, the hide rule stops
    matching it and the footer reappears inside the app — a silent regression in
    the opposite direction.
    """
    # Arrange
    marker = "workspace-page"
    # Act
    present = marker in classes
    # Assert
    assert present
