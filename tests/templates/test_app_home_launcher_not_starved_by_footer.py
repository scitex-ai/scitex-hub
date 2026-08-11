#!/usr/bin/env python3
"""The app home may not lock the body to the viewport while rendering a footer.

Card hub-apps-home-missing-footer-on-desktop-20260810 / operator report
2026-08-11: on an iPhone the signed-in app home rendered the header, then the
FOOTER, and no app icons at all.

WHAT ACTUALLY HAPPENED — measured on prod, 390x844, https://scitex.ai/ :

    #workspace-layout   height 143px   (its own CSS asks for 100dvh - 44px)
    #app-launcher       height 687px   -> clipped to 143px, unreachable
    .site-footer        height 656px
    header               45px
                        ---------------
                        844px = the whole viewport

Three rules combine into that:

    global-base.css:101   body.workspace-page { height:100vh; max-height:100vh;
                                                overflow:hidden }
    global-base.css:140   body.workspace-page .site-footer { flex-shrink: 0 }
    workspace-layout.css  .workspace-layout { height: calc(100dvh - 44px) }
                          (a flex BASIS — it shrinks, nothing pins it)

Body is a fixed 100vh flex column with `overflow:hidden`. The footer refuses to
shrink. The app shell is the only flexible item, so it absorbs the entire height
of the footer, and because the body cannot scroll there is no way to reach what
was clipped. On a phone the footer stacks its columns vertically (656px of an
844px viewport), which is why the launcher vanished on mobile while desktop —
where the footer is only 248px — still showed its tiles.

Nothing in PR #578 was wrong on its own terms: it made the footer VISIBLE on
`.app-home`, which the operator had asked for. What it did not account for is
the second-order effect of making a `flex-shrink:0` element visible inside a
container that is pinned to the viewport height. That is the invariant this file
guards, stated so it holds for surfaces that do not exist yet:

    A surface may not BOTH pin the body to the viewport AND render the footer.

Either the body scrolls (so the footer sits below a full-height shell), or the
footer stays hidden (so the shell owns the viewport). Doing both starves the
shell by exactly the height of the footer.

WHAT THIS MODEL DOES AND DOES NOT DO — the sibling
test_footer_visible_by_default.py carries the same warning and it applies here.
This resolves `height` / `max-height` / `overflow` for the BODY element from
`global-base.css` only, in source order, last-match-wins. It does not evaluate
specificity, `!important`, or other files. @media blocks are excluded on
purpose: the lock and its landing-page release are both unconditional, and a
media-scoped rule cannot be reported as the effective value without knowing the
viewport. If a future change moves the lock into a media query, this model is
the wrong tool — replace it with a real cascade evaluation rather than
weakening the assertions to fit it.

No mocks. One assertion per test (STX-TQ007).
"""

import re
from pathlib import Path

from django.conf import settings

CSS_PATH = "static/shared/css/layouts/global-base.css"

# Body classes as emitted by templates/global_base.html:73, per branch.
# Kept in step with test_footer_visible_by_default.py, which reads the same
# template branch for the footer-visibility question.
APP_HOME_CLASSES = frozenset({"workspace-page", "no-transition", "app-home"})
MODULE_CLASSES = frozenset({"workspace-page", "writer-module", "no-transition"})
LANDING_CLASSES = frozenset({"workspace-page", "landing-page"})

VIEWPORT_LOCKING = {
    "max-height": "100vh",
    "overflow": "hidden",
}


def _css_text() -> str:
    return (Path(settings.BASE_DIR) / CSS_PATH).read_text(encoding="utf-8")


def _strip_comments_and_media(css: str) -> str:
    """Remove /* */ comments, then every @media block including its contents.

    The comments must go first: this file's own rules are documented in prose
    that names the very declarations being searched for, and a naive scan would
    match the explanation instead of the code.
    """
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.DOTALL)
    out, i = [], 0
    while i < len(css):
        at = css.find("@media", i)
        if at == -1:
            out.append(css[i:])
            break
        out.append(css[i:at])
        brace = css.find("{", at)
        if brace == -1:
            break
        depth, j = 1, brace + 1
        while j < len(css) and depth:
            if css[j] == "{":
                depth += 1
            elif css[j] == "}":
                depth -= 1
            j += 1
        i = j
    return "".join(out)


def _body_rules(css: str) -> list[tuple[str, dict]]:
    """Top-level rules whose selector targets the BODY element itself."""
    rules = []
    for block in re.finditer(r"([^{}]+)\{([^{}]*)\}", _strip_comments_and_media(css)):
        selector = " ".join(block.group(1).split())
        # `body.x .site-footer` styles a DESCENDANT, not the body. Only a
        # selector that ends at the body element sets the body's own height.
        if not re.fullmatch(r"body[.a-zA-Z0-9_:()-]*", selector):
            continue
        # `body::before` styles a GENERATED box, not the body — global-base.css:26
        # uses one for the page background. Including it made all three tests
        # below fail on `unsupported selector shape` rather than on the defect,
        # which is a red for the wrong reason and would have been mistaken for
        # the real red. Single-colon `:not(...)` is kept; `::` is not.
        if "::" in selector:
            continue
        decls = {}
        for decl in block.group(2).split(";"):
            if ":" not in decl:
                continue
            prop, _, value = decl.partition(":")
            decls[prop.strip().lower()] = value.split("/*")[0].strip().lower()
        rules.append((selector, decls))
    return rules


def _selector_matches(selector: str, body_classes: frozenset) -> bool:
    """Does this `body...` selector match a <body> carrying these classes?

    Raises on a shape it does not understand rather than returning False — a
    quietly-unmatched selector is how a viewport lock would slip past this
    guard while every test still reported green.
    """
    required = set(re.findall(r"(?<!not\()\.([a-zA-Z0-9_-]+)", selector))
    excluded = set(re.findall(r":not\(\.([a-zA-Z0-9_-]+)\)", selector))
    required -= excluded
    if selector != "body" and not required and not excluded:
        raise AssertionError(f"unsupported selector shape, extend this helper: {selector!r}")
    return required <= set(body_classes) and not (excluded & set(body_classes))


def _effective_body_style(body_classes: frozenset) -> dict:
    """Resolve body height/overflow for these classes: source order, last wins."""
    effective = {}
    for selector, decls in _body_rules(_css_text()):
        if not _selector_matches(selector, body_classes):
            continue
        for prop in ("height", "max-height", "overflow", "overflow-y"):
            if prop in decls:
                effective[prop] = decls[prop]
    return effective


def _is_viewport_locked(body_classes: frozenset) -> bool:
    """Pinned to the viewport with no way to scroll to overflow."""
    style = _effective_body_style(body_classes)
    capped = style.get("max-height") == VIEWPORT_LOCKING["max-height"]
    scroll = style.get("overflow-y", style.get("overflow", ""))
    return capped and scroll == VIEWPORT_LOCKING["overflow"]


def test_the_model_finds_the_viewport_lock_on_a_workspace_module():
    """POSITIVE CONTROL: the parser resolves a real lock.

    Without this, every assertion below passes vacuously the moment the parser
    breaks or the file is renamed — 'no lock found' would read as 'nothing is
    starved', which is the answer we want to hear. A writer module SHOULD stay
    locked: it owns the viewport and its footer stays hidden.
    """
    # Arrange
    classes = MODULE_CLASSES
    # Act
    locked = _is_viewport_locked(classes)
    # Assert
    assert locked


def test_landing_page_releases_the_viewport_lock():
    """Unchanged behaviour, and the precedent this fix follows.

    global-base.css already releases the lock for `.landing-page` so that page
    scrolls to its footer. `.app-home` needs the same release for the same
    reason; the only difference is that landing hides the app shell entirely
    while the app home keeps it.
    """
    # Arrange
    classes = LANDING_CLASSES
    # Act
    locked = _is_viewport_locked(classes)
    # Assert
    assert not locked


def test_app_home_is_not_viewport_locked_because_it_renders_the_footer():
    """THE BUG (operator report 2026-08-11, iPhone: icons gone, footer only).

    `.app-home` shows the footer (PR #578) AND inherited
    `body.workspace-page { max-height:100vh; overflow:hidden }`. The footer is
    `flex-shrink:0`, so the app shell absorbed all 656px of it and the body
    could not scroll to what was clipped: the launcher measured 143px of the
    687px it needs.
    """
    # Arrange
    classes = APP_HOME_CLASSES
    # Act
    locked = _is_viewport_locked(classes)
    # Assert
    assert not locked


def _classes_excluded_from_the_footer_hide() -> set:
    """Classes that `:not(...)` out of a footer `display:none` rule.

    Read out of the CSS rather than listed here on purpose. Naming `.app-home`
    in this file would guard exactly one incident; the defect is structural, so
    the NEXT surface that un-hides its footer must be covered without anyone
    remembering that this happened. Today this returns
    {landing-page, app-home} from workspace-layout.css and footer.css — the two
    files that, by their own comments, encode one decision twice.
    """
    excluded = set()
    for rel in (
        "static/shared/css/components/workspace-layout.css",
        "static/shared/css/components/footer.css",
    ):
        css = (Path(settings.BASE_DIR) / rel).read_text(encoding="utf-8")
        css = re.sub(r"/\*.*?\*/", "", css, flags=re.DOTALL)
        for block in re.finditer(r"([^{}]+)\{([^{}]*)\}", css):
            selector, decls = block.group(1), block.group(2)
            if not re.search(r"\.(?:site|global)-footer\b", selector):
                continue
            if not re.search(r"display\s*:\s*none", decls):
                continue
            excluded |= set(re.findall(r":not\(\.([a-zA-Z0-9_-]+)\)", selector))
    return excluded


def test_the_footer_hide_rules_actually_exclude_something():
    """POSITIVE CONTROL for the derivation below.

    If the parser or the file names ever break, this returns an empty set and
    the generalised test below iterates over nothing — passing while checking
    nothing, which is the failure mode it exists to prevent.
    """
    # Arrange
    derive = _classes_excluded_from_the_footer_hide
    # Act
    excluded = derive()
    # Assert
    assert excluded


def test_no_surface_both_shows_the_footer_and_pins_the_body():
    """THE GENERAL INVARIANT — the reason this file is not about `.app-home`.

    A surface excluded from the footer hide rules RENDERS the footer. The footer
    is `flex-shrink:0` (global-base.css:140). So if that same surface also pins
    the body to the viewport, the app shell is the only item left to give, and
    it loses exactly the footer's height with no scroll to recover it. That is
    what reduced the launcher to 143px of 687px on an iPhone.

    Either the body scrolls or the footer stays hidden. Never both.
    """
    # Arrange
    excluded = _classes_excluded_from_the_footer_hide()
    # Act
    starved = sorted(
        cls
        for cls in excluded
        if _is_viewport_locked(frozenset({"workspace-page", cls}))
    )
    # Assert
    assert not starved


SHELL_ELEMENTS = re.compile(r"\.workspace-(?:layout|three-col)\b")

# Every stylesheet under this root is scanned. Naming a fixed list here is what
# failed the first time: the guard modelled global-base.css alone, passed, and
# prod stayed broken because a THIRD file held the same decision.
CSS_ROOT = "static/shared/css"


def _all_css_files() -> list:
    return sorted((Path(settings.BASE_DIR) / CSS_ROOT).rglob("*.css"))


def _rules_collapsing_the_shell() -> list:
    """Rules that force the app shell's height to 0.

    `height: 0` on `.workspace-layout` hands its size entirely to flex
    distribution. That is correct for a working surface that owns the viewport
    and fatal for one that renders a non-shrinking footer, because the footer
    takes its full height first and the shell absorbs the loss.
    """
    found = []
    for path in _all_css_files():
        css = re.sub(r"/\*.*?\*/", "", path.read_text(encoding="utf-8"), flags=re.DOTALL)
        for block in re.finditer(r"([^{}]+)\{([^{}]*)\}", css):
            selector, decls = block.group(1), block.group(2)
            if not SHELL_ELEMENTS.search(selector):
                continue
            if not re.search(r"(^|;)\s*height\s*:\s*0\b", decls):
                continue
            for part in selector.split(","):
                if SHELL_ELEMENTS.search(part):
                    found.append((path.name, " ".join(part.split())))
    return found


def _targets_the_app_home(selector: str) -> bool:
    """Does this descendant selector apply on a body carrying `app-home`?

    Only the body-scoped prefix decides; the part after it names the element.
    """
    head = selector.split()[0]
    required = set(re.findall(r"(?<!not\()\.([a-zA-Z0-9_-]+)", head))
    excluded = set(re.findall(r":not\(\.([a-zA-Z0-9_-]+)\)", head))
    required -= excluded
    if not head.startswith("body") and not required:
        return True  # unscoped: applies everywhere, app home included
    return required <= APP_HOME_CLASSES and not (excluded & APP_HOME_CLASSES)


def test_the_scan_finds_shell_collapsing_rules_at_all():
    """POSITIVE CONTROL for the scan below.

    footer-collapse.css legitimately collapses the shell on working surfaces.
    If this returns nothing, the scan is broken or the CSS moved, and the
    assertion below would pass while checking no files at all — which is
    exactly how the first version of this guard reported green on a prod that
    was still serving the bug.
    """
    # Arrange
    scan = _rules_collapsing_the_shell
    # Act
    rules = scan()
    # Assert
    assert rules


def test_no_rule_collapses_the_app_home_shell_to_zero_height():
    """THE SECOND HALF OF THE BUG, and the reason #581 changed nothing.

    Releasing the body's viewport lock in global-base.css is necessary and NOT
    sufficient. footer-collapse.css sets

        body.workspace-page:not(.landing-page) .workspace-layout { height: 0 !important }

    which overrides the shell's own calc() height and hands its size to flex
    distribution, where the non-shrinking footer wins. `:not(.landing-page)`
    was there; `:not(.app-home)` was not.

    Measured on prod 2026-08-11: disabling that one stylesheet took
    #workspace-layout from 143px to 844px.
    """
    # Arrange
    rules = _rules_collapsing_the_shell()
    # Act
    hitting_app_home = sorted(
        f"{name}: {sel}" for name, sel in rules if _targets_the_app_home(sel)
    )
    # Assert
    assert not hitting_app_home


# EOF
