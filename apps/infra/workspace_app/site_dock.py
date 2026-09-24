#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The site-wide dock: which buttons it shows, where they go, which is active.

Operator, 2026-09-14 (iPhone home-screen screenshots as the reference): ONE dock
on every page, phone and desktop alike. Each app shows its icon with a short
caption under it; the grip and Back / Forward are drawn by the template.

Which apps sit between the arrows is the user's own choice, stored server-side
(apps_app/services/launcher_dock.py): Home, My Projects, Chat and App Store
until they drag something else in. An app in the dock is not on the Home grid.

Every icon and URL is read from the thing the button opens, never retyped here,
so a dock button can never disagree with the grid tile for the same app:
  * workspace apps come from their manifests (registry);
  * Chat and Settings come from their launcher link manifests;
  * store apps outside the registry come from their catalogue row;
  * Home is the launcher grid itself, which has no tile and so no manifest, and
    it is the one constant here: fa-house, the operator's Home icon.

Each button draws the SAME coloured app icon as its Home tile: the ``category``
picks the gradient from shared/css/components/app-icon.css. Home has no tile,
so it gets its own ``home`` swatch (the hub accent).
"""

from __future__ import annotations

from dataclasses import dataclass, replace

HOME_URL = "/apps/"
HOME_ICON = "fas fa-house"
HOME_CATEGORY = "home"

#: Mirrors launcher_dock.HOME_BUTTON. Imported lazily there to dodge a cycle, so the
#: value is repeated here and a test pins the two together: a silent drift would make
#: the Home button unhighlightable.
HOME_BUTTON = "launcher"

#: Every app leaf route lives under here. Used by :func:`active_dock_key` to decide
#: that a route inside an app belongs to the global Apps destination.
APPS_PREFIX = "/apps/"

#: Dock captions sit under a narrow icon, so the long app names get a short
#: form there (operator, 2026-09-14: Home / Projects / Chat / Apps).
DOCK_SHORT_LABELS = {"my_projects": "Projects", "store": "Apps"}

#: Marker attribute on the rendered dock. SiteDockMiddleware checks for it so a
#: page that already rendered the dock is never given a second one.
DOCK_MARKER = "data-site-dock"
_FRAME_DESTINATIONS = frozenset({"iframe", "frame", "embed", "object"})


def is_embedded_request(request) -> bool:
    """Whether this document is explicitly or browser-declared as framed."""
    return request.GET.get("embed") == "1" or request.headers.get(
        "Sec-Fetch-Dest", ""
    ) in _FRAME_DESTINATIONS


@dataclass(frozen=True)
class DockItem:
    #: The app's launcher tile name, or ``launcher`` for the Home button.
    key: str
    label: str
    icon: str
    url: str
    active: bool = False
    #: Icon gradient key (shared/css/components/app-icon.css), as on the tile.
    category: str = "other"

    @property
    def caption(self) -> str:
        """The visible name under the icon (translated in the template)."""
        return DOCK_SHORT_LABELS.get(self.key, self.label)


def _is_active(key: str, url: str, path: str) -> bool:
    """Kept for callers that ask about ONE item; the dock itself uses
    :func:`active_dock_key`, because "exactly one destination is current" is a
    property of the SET, not of an item in isolation."""
    return key == active_dock_key([(key, url)], path)


#: The dock button that represents "you are inside an app". Operator ruling
#: 2026-09-17: an app leaf route (/apps/<name>/) belongs to the global Apps
#: destination, because the user reached it from there and no other dock button
#: owns it. Kept as an explicit product rule rather than inferred, so the mapping
#: is one line to change and impossible to "discover" by accident.
APP_DESTINATION_KEY = "store"


def active_dock_key(pairs, path: str) -> str | None:
    """THE one dock destination a path belongs to, or None.

    Operator ruling (2026-09-17): exactly one global dock item is active after any
    route transition, app leaf routes map to Apps, and a leaf app's LOCAL tabs
    (Cards' Board/DM, and the like) stay local - they are navigation inside the app,
    never a second global destination.

    Precedence, most specific first:

    1. a dock item whose URL is a prefix of the path (longest URL wins, so
       /apps/my-projects/ beats a broader /apps/);
    2. the Home button, for "/" and for the grid URL itself;
    3. otherwise, for an app leaf route under /apps/ (but not /apps/ itself), the
       Apps destination - see :data:`APP_DESTINATION_KEY`.

    A hub route that no dock item owns (a settings page, say) intentionally returns
    None rather than being forced onto Home: the dock has no destination for it, and
    inventing one would highlight a button the user is not on. That case is pinned by
    a test so the day a rule arrives it changes in one place.
    """
    by_key = {key: url for key, url in pairs}
    candidates = [
        (len(url), key)
        for key, url in pairs
        if url and url != HOME_URL and path.startswith(url)
    ]
    if candidates:
        return max(candidates)[1]

    if path in ("/", HOME_URL):
        return HOME_BUTTON if HOME_BUTTON in by_key else None

    if path.startswith(APPS_PREFIX) and path.rstrip("/") != APPS_PREFIX.rstrip("/"):
        return APP_DESTINATION_KEY if APP_DESTINATION_KEY in by_key else None

    return None


def _dock_item(name: str, path: str) -> DockItem | None:
    """The dock button for one app name, or None when no such app exists."""
    from apps.infra.workspace_app.registry import get_module
    from apps.workspace.apps_app.models import AppsModule
    from apps.workspace.apps_app.services.launcher_dock import HOME_BUTTON
    from apps.workspace.apps_app.services.launcher_links import get_launcher_link
    from apps.workspace.apps_app.services.manifest_display import (
        prettify_module_name,
    )

    def catalogue_row():
        return AppsModule.objects.filter(module_name=name).first()

    if name == HOME_BUTTON:
        fields = ("Home", HOME_ICON, HOME_URL, HOME_CATEGORY)
    elif module := get_module(name):
        # Same precedence as the grid tile: manifest category, then the catalogue row.
        row = None if module.category else catalogue_row()
        fields = (
            module.label,
            module.icon_fa or "fas fa-puzzle-piece",
            module.get_url(),
            module.category or (row.category if row else ""),
        )
    elif link := get_launcher_link(name):
        fields = (link.label, link.icon, link.url, link.category)
    elif row := catalogue_row():
        fields = (
            row.label or prettify_module_name(name),
            row.icon or "fas fa-puzzle-piece",
            f"/apps/store/{name}/",
            row.category,
        )
    else:
        return None
    label, icon, url, category = fields
    return DockItem(
        key=name,
        label=label,
        icon=icon,
        url=url,
        # Decided across the whole set in dock_items(): an item cannot know whether
        # another, more specific one also matches this path.
        active=False,
        category=category or "other",
    )


def dock_items(path: str, user=None) -> list[DockItem]:
    """The dock's app buttons, in the user's order, with EXACTLY ONE active.

    Operator ruling (2026-09-17): after any route transition exactly one global dock
    item is the current destination. The choice is made here, over the assembled set,
    because "most specific match wins" is not a property any single item can decide -
    /apps/my-projects/ must beat the broader app-leaf rule that would otherwise put the
    user "inside Apps" while they are looking at their own projects.
    """
    from apps.workspace.apps_app.services.launcher_dock import get_dock_apps

    items = [
        item
        for item in (_dock_item(name, path) for name in get_dock_apps(user))
        if item is not None
    ]
    active = active_dock_key([(item.key, item.url) for item in items], path)
    return [replace(item, active=(item.key == active)) for item in items]


_NO_DOCK_PATHS = ("/landing/",)

def should_render_dock(request) -> bool:
    """The dock is for signed-in top-level documents only."""
    if is_embedded_request(request):
        return False  # no recursive Hub chrome inside a frame
    if request is not None and getattr(request, "path", "").rstrip("/") + "/" in _NO_DOCK_PATHS:
        return False  # marketing page: no app access before sign-in
    user = getattr(request, "user", None)
    return bool(getattr(user, "is_authenticated", False))


# EOF
