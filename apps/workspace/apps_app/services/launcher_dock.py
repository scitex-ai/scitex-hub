#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Which apps a user keeps in the dock, stored server-side like the grid order.

The dock works like an iPhone's: every app sits EITHER in the dock OR in the
Home grid, never both. The user drags apps between the two, and the list below
is what syncs that choice across their phone and desktop.

The list holds launcher tile names (``home`` is My Projects, ``chat``, ...)
plus ``HOME_BUTTON`` for the Home button, which is the grid itself and has no
tile. It lives beside the link-tile order, on the App Store installation row's
``config`` (see ``launcher_links``), so no migration is needed.
"""

from __future__ import annotations

HOME_BUTTON = "launcher"
DEFAULT_DOCK_APPS = (HOME_BUTTON, "home", "chat", "store")

# Five 42px slots still fit a 360px phone beside the grip and both arrows.
DOCK_CAPACITY = 5

DOCK_APPS_KEY = "launcher_dock"


class DockRejected(ValueError):
    """A posted dock list that cannot be saved; the message says why."""


def get_dock_apps(user) -> list[str]:
    """The user's dock, in order: the saved list, or the defaults if none."""
    from .launcher_links import _owner_installation

    saved = None
    if getattr(user, "is_authenticated", False):
        installation = _owner_installation(user, create=False)
        if installation is not None:
            saved = (installation.config or {}).get(DOCK_APPS_KEY)
    if not isinstance(saved, list):
        return list(DEFAULT_DOCK_APPS)
    return _without_duplicates([name for name in saved if isinstance(name, str)])[
        :DOCK_CAPACITY
    ]


def validate_dock_apps(dock_apps, known_apps: set[str]) -> list[str]:
    """The posted dock as a clean list, or DockRejected naming the problem."""
    if not isinstance(dock_apps, list) or not all(
        isinstance(name, str) for name in dock_apps
    ):
        raise DockRejected("dock must be a list of app names.")
    if len(set(dock_apps)) != len(dock_apps):
        raise DockRejected("an app can appear in the dock only once.")
    unknown = [name for name in dock_apps if name not in known_apps]
    if unknown:
        raise DockRejected(f"unknown apps: {', '.join(unknown)}.")
    if HOME_BUTTON not in dock_apps:
        raise DockRejected("the Home button stays in the dock.")
    if len(dock_apps) > DOCK_CAPACITY:
        raise DockRejected(f"the dock holds at most {DOCK_CAPACITY} apps.")
    return list(dock_apps)


def save_dock_apps(user, dock_apps: list[str]) -> None:
    """Persist an already validated dock list for ``user``."""
    from .launcher_links import _owner_installation

    installation = _owner_installation(user, create=True)
    if installation is None:
        raise DockRejected("the App Store module is not installed yet.")
    config = installation.config or {}
    config[DOCK_APPS_KEY] = list(dock_apps)
    installation.config = config
    installation.save(update_fields=["config"])


def _without_duplicates(names: list[str]) -> list[str]:
    return list(dict.fromkeys(names))


# EOF
