#!/usr/bin/env python3
"""Which global dock destination a route belongs to, and how the dock shows it.

Operator ruling, 2026-09-17: after ANY route transition exactly one global dock item
is active; app leaf routes map to the global Apps destination (unless an explicit
product rule says otherwise); a leaf app's LOCAL tabs (Cards' Board/DM) stay local; and
no inactive item is coloured.

Measured BEFORE this change, signed in at 390px, per route:
    /                       active=1  ['launcher']
    /apps/my-projects/      active=1  ['my_projects']
    /apps/store/            active=1  ['store']
    /chat/                  active=1  ['chat']
    /apps/agents/           active=0  []        <- app leaves highlighted nothing
    /apps/cards/            active=0  []
    /apps/cards/board/      active=0  []
    /accounts/settings/     active=0  []
and every dock icon carried a category GRADIENT including the inactive ones, so four
coloured chips said nothing about where the user was.

The mapping is a pure function of (key, url) pairs and a path, so it is testable with
no database and no browser; the rendered states are additionally asserted end to end in
the route tests that need a database (CI).
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from apps.infra.workspace_app.site_dock import (
    APPS_PREFIX,
    APP_DESTINATION_KEY,
    HOME_BUTTON,
    active_dock_key,
)

#: The four default dock buttons, as the request always assembles them.
DOCK = [
    (HOME_BUTTON, "/apps/"),          # Home - the launcher grid
    ("my_projects", "/apps/my-projects/"),
    ("chat", "/chat/"),
    (APP_DESTINATION_KEY, "/apps/store/"),
]


@pytest.mark.parametrize(
    "path,expected",
    [
        # hub routes the dock actually owns
        ("/", HOME_BUTTON),
        ("/apps/", HOME_BUTTON),
        ("/apps/my-projects/", "my_projects"),
        ("/apps/my-projects/?project=128", "my_projects"),
        ("/chat/", "chat"),
        ("/apps/store/", APP_DESTINATION_KEY),
        # APP LEAF ROUTES -> the global Apps destination (the operator's rule)
        ("/apps/agents/", APP_DESTINATION_KEY),
        ("/apps/cards/", APP_DESTINATION_KEY),
        ("/apps/writer/", APP_DESTINATION_KEY),
        ("/apps/storage/", APP_DESTINATION_KEY),
        # a leaf app's LOCAL tabs stay local: they belong to the app, which is Apps
        ("/apps/cards/board/", APP_DESTINATION_KEY),
        ("/apps/cards/dm/7/", APP_DESTINATION_KEY),
        ("/apps/stats/?project=128", APP_DESTINATION_KEY),
        # an explicitly owned route wins over the app-leaf rule, most specific first
        ("/apps/my-projects/anything/", "my_projects"),
    ],
)
def test_each_route_maps_to_the_one_destination(path, expected):
    assert active_dock_key(DOCK, path) == expected


def test_an_app_leaf_never_maps_to_home():
    """The bug this fixes: app leaves highlighted NOTHING at all, so the dock showed
    no current destination while the user was inside an app."""
    for path in ("/apps/agents/", "/apps/cards/", "/apps/cards/board/", "/apps/writer/"):
        assert active_dock_key(DOCK, path) not in (None, HOME_BUTTON)


def test_the_more_specific_dock_url_wins():
    """/apps/my-projects/ is under /apps/ too - it must not be swallowed by the
    app-leaf rule and reported as "you are in Apps"."""
    assert active_dock_key(DOCK, "/apps/my-projects/") == "my_projects"


def test_exactly_one_key_matches_any_route():
    """The whole ruling in one assertion: 0 or 2 active items is the defect."""
    routes = [
        "/", "/apps/", "/chat/", "/apps/store/", "/apps/my-projects/",
        "/apps/agents/", "/apps/cards/board/", "/apps/writer/",
    ]
    for path in routes:
        keys = [key for key, url in DOCK if active_dock_key(DOCK, path) == key]
        assert len(keys) == 1, f"{path} -> {keys}"


def test_a_hub_route_no_dock_item_owns_stays_unhighlighted():
    """PINNED, not asserted as correct: /accounts/settings/ belongs to no dock button.

    The ruling says "exactly one"; read literally that would force Home onto a settings
    page, which would highlight a button the user is not on. This pins today's
    behaviour (None) so the answer changes in exactly one place when a rule arrives.
    """
    assert active_dock_key(DOCK, "/accounts/settings/") is None


def test_the_mirrored_home_button_constant_matches_its_owner():
    """site_dock re-declares HOME_BUTTON to dodge an import cycle; a silent drift
    would make the Home button unhighlightable on every page."""
    from apps.workspace.apps_app.services.launcher_dock import HOME_BUTTON as OWNER

    assert HOME_BUTTON == OWNER


def test_a_dock_without_the_apps_button_degrades_to_no_highlight():
    """No Apps button in the dock means no app-leaf destination - not a wrong one."""
    dock = [(HOME_BUTTON, "/apps/"), ("chat", "/chat/")]

    assert active_dock_key(dock, "/apps/agents/") is None


# ---------------------------------------------------------------------------
# the CSS contract: destination colours remain visible at rest
# ---------------------------------------------------------------------------

DOCK_CSS = (
    Path(__file__).resolve().parents[3]
    / "static/shared/css/components/site-dock.css"
)


def test_inactive_dock_icons_keep_the_shared_category_colours():
    """The dock must not override the canonical app-icon category palette."""
    css = DOCK_CSS.read_text()

    assert ".site-dock-app:not(.is-active) .site-dock-app-icon" not in css
    assert "--site-dock-icon-idle-bg" not in css
    assert "--site-dock-icon-idle-fg" not in css


def test_dock_does_not_define_a_second_category_palette():
    """Category colours belong to app-icon.css, not a dock-local duplicate."""
    css = DOCK_CSS.read_text()
    assert 'site-dock-app-icon[data-tile-category' not in css


if __name__ == "__main__":
    import sys

    sys.exit(pytest.main([__file__, "-v"]))
