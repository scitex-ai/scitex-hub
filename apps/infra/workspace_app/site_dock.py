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

from dataclasses import dataclass

HOME_URL = "/apps/"
HOME_ICON = "fas fa-house"
HOME_CATEGORY = "home"

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
    from apps.workspace.apps_app.services.launcher_dock import HOME_BUTTON

    if key == HOME_BUTTON:
        return path in ("/", HOME_URL)
    return bool(url) and url != HOME_URL and path.startswith(url)


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
        active=_is_active(name, url, path),
        category=category or "other",
    )


def dock_items(path: str, user=None) -> list[DockItem]:
    """The dock's app buttons, in the user's order, for a request path."""
    from apps.workspace.apps_app.services.launcher_dock import get_dock_apps

    items = (_dock_item(name, path) for name in get_dock_apps(user))
    return [item for item in items if item is not None]


def should_render_dock(request) -> bool:
    """The dock is for signed-in top-level documents only."""
    if is_embedded_request(request):
        return False  # no recursive Hub chrome inside a frame
    user = getattr(request, "user", None)
    return bool(getattr(user, "is_authenticated", False))


# EOF
