#!/usr/bin/env python3
"""Per-module registry overrides that cannot be expressed in manifest JSON."""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Clew SVG icons (custom — not in JSON, defined here)
# ---------------------------------------------------------------------------
_CLEW_SVG_NAV = (
    '<svg class="nav-icon-svg" viewBox="0 0 100 100" fill="none" '
    'xmlns="http://www.w3.org/2000/svg" width="20" height="20">'
    '<circle cx="50" cy="50" r="40" stroke="currentColor" stroke-width="5"/>'
    '<line x1="10" y1="50" x2="90" y2="50" stroke="currentColor" stroke-width="4.5"/>'
    '<line x1="13" y1="35" x2="87" y2="35" stroke="currentColor" stroke-width="4"/>'
    '<line x1="13" y1="65" x2="87" y2="65" stroke="currentColor" stroke-width="4"/>'
    '<path d="M30 12 Q70 30 70 50 Q70 70 30 88" stroke="currentColor" stroke-width="4" fill="none"/>'
    '<path d="M70 12 Q30 30 30 50 Q30 70 70 88" stroke="currentColor" stroke-width="4" fill="none"/>'
    '<line x1="85" y1="82" x2="95" y2="95" stroke="currentColor" stroke-width="4.5" stroke-linecap="round"/>'
    "</svg>"
)

_CLEW_SVG_TAB = (
    '<svg class="tab-icon-svg" viewBox="0 0 100 100" fill="none" '
    'xmlns="http://www.w3.org/2000/svg" width="16" height="16" style="flex-shrink:0">'
    '<circle cx="50" cy="50" r="40" stroke="currentColor" stroke-width="5"/>'
    '<line x1="10" y1="50" x2="90" y2="50" stroke="currentColor" stroke-width="4.5"/>'
    '<line x1="13" y1="35" x2="87" y2="35" stroke="currentColor" stroke-width="4"/>'
    '<line x1="13" y1="65" x2="87" y2="65" stroke="currentColor" stroke-width="4"/>'
    '<path d="M30 12 Q70 30 70 50 Q70 70 30 88" stroke="currentColor" stroke-width="4" fill="none"/>'
    '<path d="M70 12 Q30 30 30 50 Q30 70 70 88" stroke="currentColor" stroke-width="4" fill="none"/>'
    '<line x1="85" y1="82" x2="95" y2="95" stroke="currentColor" stroke-width="4.5" stroke-linecap="round"/>'
    "</svg>"
)

MANIFEST_OVERRIDES: dict[str, dict] = {
    "clew": {"icon_svg_tab": _CLEW_SVG_TAB, "icon_svg_nav": _CLEW_SVG_NAV},
    # The installed Stats release mounts successfully but does not yet render
    # the Hub project/version/provider contract and its project-default writes
    # have not passed authorization/filesystem review.  Keep the tile truthful
    # and non-launchable until the leaf publishes the complete contract; no
    # Stats business logic lives in Hub.
    "stats": {"scope": "project", "availability": "coming_soon"},
}
