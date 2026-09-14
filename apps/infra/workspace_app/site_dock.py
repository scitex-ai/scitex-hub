#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The site-wide dock: which buttons it shows, where they go, which is active.

Operator, 2026-09-14 (iPhone home-screen screenshots as the reference): ONE dock
on every page, phone and desktop alike, icons only. In order: Home, My Projects,
Chat, App Store. Back and Forward sit at the far ends and are drawn by the
template.

Every icon and URL is read from the thing the button opens, never retyped here,
so a dock button can never disagree with the grid tile for the same app:
  * My Projects and App Store come from their workspace manifests (registry);
  * Chat comes from its launcher link manifest (apps_app/launcher_links/chat.json);
  * Home is the launcher grid itself, which has no tile and so no manifest, and
    it is the one constant here: fa-house, the operator's Home icon.

The dock used to live inside the launcher template only. On any other page it
disappeared, and its "Files" button went to /files/ rather than My Projects
(operator report, 2026-09-14). Rendering it from the base template, and from
SiteDockMiddleware on leaf pages that do not use the base template, is what
keeps it on every page.
"""

from __future__ import annotations

from dataclasses import dataclass

HOME_URL = "/apps/"
HOME_ICON = "fas fa-house"

#: Marker attribute on the rendered dock. SiteDockMiddleware checks for it so a
#: page that already rendered the dock is never given a second one.
DOCK_MARKER = "data-site-dock"


@dataclass(frozen=True)
class DockItem:
    key: str
    label: str
    icon: str
    url: str
    active: bool = False


def _is_active(key: str, path: str) -> bool:
    if key == "home":
        return path in ("/", HOME_URL)
    prefixes = {
        "projects": ("/apps/home/",),
        "chat": ("/chat/",),
        "store": ("/apps/store/",),
    }
    return path.startswith(prefixes.get(key, ()))


def dock_items(path: str) -> list[DockItem]:
    """The dock's app buttons, in the operator's order, for a request path."""
    from apps.infra.workspace_app.registry import get_module
    from apps.workspace.apps_app.services.launcher_links import get_launcher_link

    projects = get_module("home")
    store = get_module("store")
    chat = get_launcher_link("chat")

    items = [
        ("home", "Home", HOME_ICON, HOME_URL),
        (
            "projects",
            "My Projects",
            projects.icon_fa if projects else "fas fa-folder",
            projects.get_url() if projects else "/apps/home/",
        ),
        (
            "chat",
            "Chat",
            chat.icon if chat else "fas fa-comment",
            chat.url if chat else "/chat/",
        ),
        (
            "store",
            "App Store",
            store.icon_fa if store else "fas fa-table-cells-large",
            store.get_url() if store else "/apps/store/",
        ),
    ]
    return [
        DockItem(key=key, label=label, icon=icon, url=url, active=_is_active(key, path))
        for key, label, icon, url in items
    ]


def should_render_dock(request) -> bool:
    """The dock is for signed-in users: every target behind it requires login."""
    user = getattr(request, "user", None)
    return bool(getattr(user, "is_authenticated", False))


# EOF
