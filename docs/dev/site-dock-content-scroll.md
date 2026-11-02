# Phone dock visibility while reading

The shared site dock remains a true fixed overlay. It does not reserve page
height or add leaf-specific padding. On viewports up to 768 pixels wide, an
expanded bottom dock temporarily becomes its existing grip pill when the user
scrolls content outside it. Capture-phase scroll handling includes nested
workspace scrollers, not only document scrolling.

Wheel, touch and scrolling-key intent arm this behavior; a measured change in
scroll position is required. Startup restoration and a scroll event without
movement do not collapse it. Scrolling the dock or its chat panel, a floating
dock, and an already minimized dock are unchanged. Desktop behavior is unchanged.

Tapping the grip or pressing Enter/Space restores the transiently collapsed
dock. Widening to desktop restores it too. Neither automatic collapse nor this
restoration changes localStorage or the saved minimized preference. Explicit
manual minimization continues to use the existing per-device preference.
The existing keyboard-focus avoidance remains in place.

Source: `static/shared/ts/components/site-dock.ts` and
`_site-dock/content-scroll.ts` and `_site-dock/minimize.ts`. DOM regressions are in
`tests/ts/shared/components/site-dock-content-scroll.test.ts`; the existing
`tests/templates/test_site_dock_overlay_contract.py` remains the layout contract.
