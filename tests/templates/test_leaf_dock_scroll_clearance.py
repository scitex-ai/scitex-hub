#!/usr/bin/env python3
"""Hub shell must keep the last scroll line clear of the fixed site dock on
standalone leaf pages (SDK report 2026-10-22: /apps/sdk/ Section-3 helper
text sat under the dock at full scroll). Overlay contract: no layout padding,
so the clearance is scroll-padding on the leaf scroll container."""
import re
from pathlib import Path

CSS = Path("static/shared/css/layouts/leaf-host-chrome.css")
CONTRACT = Path("tests/templates/test_site_dock_overlay_contract.py")


def _css(rel):
    src = Path(rel).read_text(encoding="utf-8")
    return re.sub(r"/\*.*?\*/", "", src, flags=re.DOTALL)


def test_leaf_scroll_container_has_dock_scroll_clearance():
    css = _css(str(CSS))
    assert "scroll-padding-bottom" in css, "no scroll-end clearance for leaf pages"
    assert "--site-dock-scroll-clearance" in css


def test_clearance_adds_no_layout_space():
    css = _css(str(CSS))
    # Pseudo-elements are real layout children, including inside a flex frame.
    rules = re.findall(
        r"body:has\([^)]*nav\.site-dock[^)]*\)([^{]*)\{([^}]*)\}", css
    )
    observation = [
        (
            "::after" in selectors or "::before" in selectors,
            "scroll-padding-bottom" in body,
            bool(re.search(r"(?<!scroll-)padding-bottom|(?:^|;)\s*height\s*:", body)),
        )
        for selectors, body in rules
    ]
    assert observation and all(row == (False, True, False) for row in observation)


def test_overlay_contract_still_holds():
    src = CONTRACT.read_text(encoding="utf-8")
    assert "does_not_pad_the_page" in src
