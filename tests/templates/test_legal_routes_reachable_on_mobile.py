#!/usr/bin/env python3
"""On a phone the legal pages must be reachable from the hamburger menu.

Card hub-app-home-footer-legal-contact-20260810.

WHY THIS FILE EXISTS — the fix for the reported bug nearly shipped the bug.

The operator reported that the signed-in app home has no footer, so 特定商取引法
に基づく表記, the policy pages and contact details have no route:

    「フッターがないとですね。あの特商法の表示がとか法律がとか
      後は連絡先がとかってわかりにくいんで」

The obvious fix — stop hiding the footer on the app home — is correct on a
DESKTOP and wrong on a PHONE. Measured on production 2026-08-10 by rendering the
post-fix state at 390px wide:

    .site-footer            display:block, height 627px
    .launcher-dock          position:fixed, viewport y 766..830
    a[href="/cookies/"]     y 781..800   elementFromPoint -> .launcher-dock
    a[href="/tokushoho/"]   y 811..830   elementFromPoint -> .launcher-dock-item

Both links render and neither can be tapped: the fixed dock sits on top, and the
launcher's shell is 100dvh so the page cannot scroll them clear. The footer also
squeezed the icon grid from 576px to 217px.

That outcome is WORSE than the original bug. The disclosure would look present
to anyone auditing the markup while remaining unreachable, so the defect would
stop being visible to the people most likely to catch it.

So the footer stays hidden on mobile workspace pages (footer.css) and the phone
gets its own route: a Legal section in the hamburger menu. The operator
permitted relocating the footer on a small screen — 「小さいサイズモバイル版の
ときにはどこかに逃がしてもいい」 — but not deleting it, and "relocated" only
counts if something actually carries the links.

UPDATE 2026-09-14 (Home + dock redesign). The operator asked for the footer to
scroll into view above the dock on the phone Home as well. That is now safe:
the app home body scrolls, and the site dock reserves its band as body padding,
so the footer's last row clears the dock. The last tests in this file pin both
halves. The hamburger Legal section stays, because deeper workspace pages still
hide the footer on a phone.

WHAT THIS MODEL DOES AND DOES NOT DO. It reads the template SOURCE and checks
which `{% url %}` tags appear inside the mobile menu container and at what
template nesting depth. It does not render, so it cannot prove the links are
visible; the rendered check is the browser evidence recorded on the card. What
it does prove is the part a future edit is most likely to break silently: that
the links exist in the menu at all, and that they are not buried inside an
`{% if user.is_authenticated %}` branch where a visitor would never see them.

No mocks. One assertion per test (STX-TQ007).
"""

import re
from pathlib import Path

import pytest
from django.conf import settings

TEMPLATE_PATH = "templates/global_base_partials/global_header.html"
MOBILE_MENU_MARKER = 'id="mobile-header-menu"'

# The routes a Japanese paid service must keep reachable. tokushoho is the
# statutory one (特定商取引法に基づく表記); the rest are the policies and the
# contact route the operator named in the same message.
REQUIRED_LEGAL_ROUTES = (
    "public_app:tokushoho",
    "public_app:terms",
    "public_app:privacy",
    "public_app:cookies",
    "public_app:contact",
)

IF_TAG = re.compile(r"{%-?\s*if\b")
ENDIF_TAG = re.compile(r"{%-?\s*endif\b")


def _template_text() -> str:
    return (Path(settings.BASE_DIR) / TEMPLATE_PATH).read_text(encoding="utf-8")


def _mobile_menu_source(template: str) -> str:
    """Everything from the mobile menu container to the end of the header.

    Deliberately NOT trying to find the container's matching </div>: the menu is
    the last block before the header closes, and a brace-counting parse over
    HTML would be the fragile part of this guard rather than the part that
    catches regressions.
    """
    start = template.index(MOBILE_MENU_MARKER)
    return template[start:]


def _conditional_depth_at(source: str, position: int) -> int:
    """Template `{% if %}` nesting depth at a character offset."""
    head = source[:position]
    return len(IF_TAG.findall(head)) - len(ENDIF_TAG.findall(head))


def _url_tag_positions(source: str, route: str) -> list[int]:
    pattern = re.compile(r"{%-?\s*url\s+['\"]" + re.escape(route) + r"['\"]")
    return [m.start() for m in pattern.finditer(source)]


def test_the_mobile_menu_container_is_found():
    """POSITIVE CONTROL: the marker still exists.

    Without this, renaming or deleting the menu makes `_mobile_menu_source`
    raise or return nothing, and 'no legal links found' would be reported as a
    parser problem instead of the missing route it actually is. Every assertion
    below is vacuous if this one does not hold.
    """
    # Arrange
    template = _template_text()
    # Act
    found = MOBILE_MENU_MARKER in template
    # Assert
    assert found


def test_the_menu_contains_entries_other_than_the_legal_ones():
    """POSITIVE CONTROL for the nesting parse: the menu has real content.

    Guards the case where the container marker survives but the menu body is
    emptied — the legal assertions would then fail loudly, but a reader could
    not tell whether the parse or the template was at fault.
    """
    # Arrange
    menu = _mobile_menu_source(_template_text())
    # Act
    has_other_items = "mobile-theme-toggle-btn" in menu
    # Assert
    assert has_other_items


@pytest.mark.parametrize("route", REQUIRED_LEGAL_ROUTES)
def test_legal_route_is_present_in_the_mobile_menu(route):
    """Each legal page is linked from the phone menu.

    This is the whole point of the mobile half of the fix: the footer is hidden
    at this width, so if these links are not here they are nowhere.
    """
    # Arrange
    menu = _mobile_menu_source(_template_text())
    # Act
    positions = _url_tag_positions(menu, route)
    # Assert
    assert positions


@pytest.mark.parametrize("route", REQUIRED_LEGAL_ROUTES)
def test_legal_route_is_not_gated_behind_a_conditional(route):
    """The links must not sit inside `{% if %}` — depth 0 within the menu.

    A statutory disclosure obligation does not depend on whether the reader
    signed in, and a visitor session is exactly who reads it before deciding to
    pay. Putting the block inside the account branch would leave anonymous and
    visitor sessions with no route while every authenticated test still passed —
    the failure mode this asserts against.
    """
    # Arrange
    menu = _mobile_menu_source(_template_text())
    # Act
    depths = [_conditional_depth_at(menu, pos) for pos in _url_tag_positions(menu, route)]
    # Assert
    assert 0 in depths


def _css(relpath: str) -> str:
    css = (Path(settings.BASE_DIR) / relpath).read_text(encoding="utf-8")
    return re.sub(r"/\*.*?\*/", "", css, flags=re.DOTALL)


def test_the_mobile_menu_reserves_the_dock_band():
    """The menu must pad its scroll end past the fixed dock.

    The menu is `position: fixed; bottom: 0`, so it runs to the viewport edge,
    and the dock floats over its last band while sitting later in the DOM — so
    the dock paints on top and eats taps there.

    Measured on production at 390px with this branch's Legal section rendered:
    scrolled fully down, `a[href="/contact/"]` sat at y 784..828 and
    elementFromPoint at its centre returned the dock. The menu could only scroll
    21px — nowhere near enough to lift a 44px row clear of a 64px dock — so the
    last legal entry was permanently untappable.

    Without this rule the Legal section still PASSES every other test in this
    file — present in the menu, at depth 0 — while its last entry cannot be
    tapped. That is exactly the "renders but is unreachable" failure this whole
    branch exists to remove, so it gets its own guard.

    2026-09-14: the dock became the SITE dock on every page (.site-dock), so the
    reservation is keyed on it.
    """
    # Arrange
    css = _css("static/shared/css/components/header/14-responsive.css")
    # Act
    reserves_band = re.search(
        r":has\(\.site-dock\)[^{]*\.mobile-header-menu\s*\{[^}]*padding-bottom",
        css,
    )
    # Assert
    assert reserves_band is not None


def test_the_page_reserves_the_dock_band_so_the_footer_clears_it():
    """While the dock sits at the bottom, the body reserves its band.

    This is what makes it safe to show the footer on the phone app home (see
    the next test). The defect measured on 2026-08-10 was 特商法 and Cookies
    rendering UNDER the fixed dock with no way to scroll them clear. With the
    body padded by the dock's clearance, the end of the document, which is the
    footer's last row, scrolls up to sit above the dock.
    """
    # Arrange
    css = _css("static/shared/css/components/site-dock.css")
    # Act
    reserves = re.search(
        r"body:has\(>\s*\.site-dock[^{]*\{[^}]*padding-bottom:\s*var\(--site-dock-clearance\)",
        css,
    )
    # Assert
    assert reserves is not None


def test_the_phone_app_home_shows_the_footer():
    """The mobile footer hide rule now EXCLUDES `.app-home`.

    This file used to assert the opposite. That was right while the launcher
    shell was pinned to 100dvh and the dock covered the footer's last links.
    Operator, 2026-09-14: swiping down on Home must reveal the footer above the
    dock. Two things now make that safe. The app home body scrolls (global-base.css,
    "App Home Override"), and the page reserves the dock band (previous test).
    Deeper workspace pages still hide the footer on a phone.
    """
    # Arrange
    css = _css("static/shared/css/components/footer.css")
    # Act
    excludes_app_home = re.search(
        r"body\.workspace-page[^{]*:not\(\.app-home\)[^{]*\.site-footer", css
    )
    # Assert
    assert excludes_app_home is not None


