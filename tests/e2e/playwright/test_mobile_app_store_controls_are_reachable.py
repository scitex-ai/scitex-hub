#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""No app-store control may sit past a clipping ancestor at 390x844.

This is the RENDERING guard for the grid-track fix in
`apps/workspace/apps_app/static/apps_app/css/apps/layout.css`. Its companion,
`tests/apps/apps_app/test_app_store_grid_track_cannot_blow_out.py`, asserts the
CSS declaration survives; this one asserts the property the declaration exists
to produce — that a visitor can actually reach the controls.

Both are wanted. The source test fails fast and explains itself; this one is the
only thing that can catch a regression arriving from somewhere else entirely (a
new rule in another stylesheet, a template change, a scitex-ui shell upgrade).
A declaration surviving is a proxy; being able to tap the button is the thing.

MEASURED on prod before the fix, /apps/store/ at 390x844:

    visible controls              90
    fully on screen               50
    UNREACHABLE past a clip edge  25

`.apps-grid`'s single track resolved to 796.95px inside a correctly-capped
362px grid, so every `.ap-card` was 797px wide. `.apps-container` clips at
`overflow-x: hidden`, which makes the excess unreachable rather than merely
ugly: each card's star button sat 292px beyond the clip boundary and its status
trigger 326px beyond. No gesture reveals them.

WHY `checkVisibility()` AND NOT `getComputedStyle(el).display`: the latter tests
the ELEMENT and ignores ANCESTORS, so every item inside a CLOSED menu reads as
visible. Measured on /landing/ during this work: the naive predicate admitted 59
controls and reported 22 "visible 0x0" defects; `checkVisibility` admitted 37
and reported 0. All 22 were false. The naive check fails silently and in the
direction of inventing findings.

SCOPE, DECLARED RATHER THAN IMPLIED. This asserts only over `.apps-container`.
At the time of writing exactly one control elsewhere on the page is unreachable
— the mobile hamburger, 43px beyond `.workspace-page`'s edge, from an
independent header overflow (`.global-header-inner` clientW 380 vs scrollW 438).
That is tracked as its own defect and deliberately NOT asserted here: folding it
in would make this test red for a reason it does not diagnose. When the header
is fixed, tighten this to the whole page rather than leaving the narrower scope
in place by inertia.
"""

import pytest

STORE_PATH = "/apps/store/"

# Anti-vacuity floor. A page that failed to render, or a selector that matched
# nothing, yields an empty `unreachable` list and would otherwise READ AS A
# PASS. Prod served 90 visible controls here; 20 is well under that and well
# over anything a broken render would produce.
MIN_EXPECTED_VISIBLE_CONTROLS = 20

# Returns every visible control whose left edge is at or past the right edge of
# its nearest clipping ancestor — i.e. laid out, but scrolled/clipped out of any
# possible reach.
_REACHABILITY_PROBE = """
() => {
  const container = document.querySelector('.apps-container');
  if (!container) return {error: 'no .apps-container on the page'};

  const truly = el => el.checkVisibility(
    {checkOpacity: true, checkVisibilityCSS: true}
  );
  const clipper = el => {
    let n = el.parentElement;
    while (n && n !== document.documentElement) {
      const ox = getComputedStyle(n).overflowX;
      if (ox === 'hidden' || ox === 'clip') return n;
      n = n.parentElement;
    }
    return null;
  };

  const controls = [...container.querySelectorAll('a,button,input,select,textarea')]
    .filter(truly);

  const unreachable = controls.map(el => {
    const c = clipper(el);
    if (!c) return null;
    const r = el.getBoundingClientRect();
    const cr = c.getBoundingClientRect();
    const beyond = Math.round(r.left - cr.right);
    if (beyond < 0) return null;
    return {
      cls: (el.className || '').toString().slice(0, 40) || el.tagName,
      text: (el.innerText || '').trim().slice(0, 24),
      px_beyond_clip: beyond,
      clipped_by: (c.className || '').toString().slice(0, 30) || c.tagName,
    };
  }).filter(Boolean);

  return {
    visible_controls: controls.length,
    unreachable: unreachable,
    grid_track: (g => g ? getComputedStyle(g).gridTemplateColumns : null)(
      document.querySelector('.apps-grid')
    ),
    card_width: (c => c ? Math.round(c.getBoundingClientRect().width) : null)(
      document.querySelector('.ap-card')
    ),
    viewport_width: window.innerWidth,
  };
}
"""


@pytest.fixture
def store_reachability(visitor_mobile_page):
    visitor_mobile_page.goto(STORE_PATH)
    visitor_mobile_page.wait_for_load_state("networkidle")
    return visitor_mobile_page.evaluate(_REACHABILITY_PROBE)


class TestMobileAppStoreControlsAreReachable:
    """The app store on an iPhone 14 viewport (390x844)."""

    def test_probe_found_the_store(self, store_reachability):
        """Anti-vacuity: without controls, every assertion below is trivial."""
        # Arrange
        expected_minimum = MIN_EXPECTED_VISIBLE_CONTROLS

        # Act
        found = store_reachability.get("visible_controls", 0)

        # Assert
        assert found >= expected_minimum, (
            f"the probe found {found} visible controls inside .apps-container "
            f"on {STORE_PATH}, expected at least {expected_minimum}. "
            f"Probe returned: {store_reachability!r}. Either the store did not "
            "render, or its markup changed — do NOT relax this floor to make "
            "the suite green, because an empty result makes the reachability "
            "assertion below pass on nothing."
        )

    def test_no_store_control_is_clipped_out_of_reach(
        self, store_reachability, screenshot, visitor_mobile_page
    ):
        """The property the grid-track fix exists to produce."""
        # Arrange
        expected_unreachable = []

        # Act
        unreachable = store_reachability.get("unreachable", [])

        # Assert
        screenshot(visitor_mobile_page, "app_store_mobile_reachability")
        assert unreachable == expected_unreachable, (
            f"{len(unreachable)} control(s) inside .apps-container sit past a "
            f"clipping ancestor's right edge at 390px and cannot be reached by "
            f"any gesture: {unreachable!r}\n"
            f"grid track = {store_reachability.get('grid_track')!r}, "
            f"first card = {store_reachability.get('card_width')}px, "
            f"viewport = {store_reachability.get('viewport_width')}px.\n"
            "If the track is wider than the viewport, the likely cause is a "
            "bare `1fr` in .apps-grid's grid-template-columns — that is "
            "`minmax(auto, 1fr)`, whose automatic minimum is the widest card's "
            "min-content width. Use `minmax(0, 1fr)`."
        )


# EOF
