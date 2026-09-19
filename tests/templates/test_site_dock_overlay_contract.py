#!/usr/bin/env python3
"""Source contracts for the site dock's true-overlay layout.

Card hub-site-dock-overlay-no-reserved-space-20260916.
"""

import re
from pathlib import Path

from django.conf import settings


def _css(relpath: str) -> str:
    source = (Path(settings.BASE_DIR) / relpath).read_text(encoding="utf-8")
    return re.sub(r"/\*.*?\*/", "", source, flags=re.DOTALL)


def _rule(css: str, selector: str) -> str:
    match = re.search(re.escape(selector) + r"\s*\{([^}]*)\}", css)
    assert match is not None, f"missing CSS rule for {selector}"
    return match.group(1)


def test_bottom_docked_launcher_does_not_pad_the_page():
    """A fixed overlay must not shorten the document it floats above."""
    css = _css("static/shared/css/components/site-dock.css")

    body_rules = re.findall(
        r"body:has\([^{}]*\.site-dock[^{}]*\)[^{]*\{([^}]*)\}", css
    )

    assert body_rules
    assert all(
        re.search(r"(?<!scroll-)padding-bottom\s*:|(?:^|;)\s*height\s*:", rule)
        is None
        for rule in body_rules
    )


def test_leaf_shell_keeps_only_the_device_safe_area_at_its_scroll_end():
    """Standalone leaf pages must not reserve the launcher's measured height."""
    css = _css("static/shared/css/layouts/leaf-host-chrome.css")
    body_rule = _rule(css, "body:has(> .stx-leaf-site-header)")

    assert re.search(
        r"padding-bottom:\s*env\(safe-area-inset-bottom,\s*0px\)", body_rule
    )


def test_leaf_workspace_height_does_not_subtract_dock_clearance():
    """Desktop leaf workspaces retain their full host height under the overlay."""
    css = _css("static/shared/css/layouts/leaf-host-chrome.css")

    assert "--site-dock-clearance" not in css


def test_expanded_bottom_dock_uses_scroll_alignment_not_layout_padding():
    """Focused controls clear the overlay without a permanent blank band."""
    css = _css("static/shared/css/components/site-dock.css")

    assert re.search(
        r"html:has\([^)]*\.site-dock[^}]*\{[^}]*"
        r"scroll-padding-bottom:\s*var\(--site-dock-scroll-clearance\)",
        css,
    )
    assert re.search(
        r":focus-visible[^}]*\{[^}]*"
        r"scroll-margin-bottom:\s*var\(--site-dock-scroll-clearance\)",
        css,
    )


def test_dock_is_translucent_at_idle_and_opaque_during_interaction():
    """The overlay reveals content at rest and becomes solid while in use."""
    css = _css("static/shared/css/components/site-dock.css")
    dock_rule = _rule(css, ".site-dock")

    assert "background: var(--site-dock-bg-idle)" in dock_rule
    assert "backdrop-filter: blur(" in dock_rule
    assert "pointer-events: auto" in dock_rule
    assert "--site-dock-bg-idle: rgba(255, 255, 255, 0.72)" in css
    assert "--site-dock-bg-idle: rgba(28, 31, 40, 0.72)" in css
    assert ".site-dock:focus-within" not in css, (
        "a tapped mobile control keeps focus and made the dock permanently opaque"
    )
    assert ".site-dock:has(:focus-visible)" in css
    assert re.search(
        r"\.site-dock:has\(:focus-visible\)[^}]*"
        r"\.site-dock:active[^}]*\.site-dock--dragging\s*\{[^}]*"
        r"background:\s*var\(--site-dock-bg-opaque\)",
        css,
    )
