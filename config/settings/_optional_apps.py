#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: config/settings/_optional_apps.py
"""Which upstream SciTeX apps are installed, and what their AppConfig paths are.

Extracted from ``settings_shared.py`` on 2026-08-16. Four blocks shared one
shape — import the package, append an AppConfig path, skip on ImportError — and
one responsibility: reason about third-party packaging. It is also where every
upstream-rename incident lands, which is the better argument for its own file.

WHY THE AppConfig PATH IS EXPLICIT AND NEVER A BARE MODULE ENTRY. figrecipe,
writer and cards each ship an ``apps.py`` holding two AppConfig candidates (the
imported ``ScitexAppConfig`` base plus their own) with no ``default=True``. A
bare ``"<pkg>._django"`` entry falls back to the label ``_django``, and those
fallbacks collide with each other. storage is the exception — ``StorageConfig``
sets ``default=True`` and a unique label — and is spelled out anyway so all four
read the same.
"""

from __future__ import annotations

import os
from importlib import import_module
from types import ModuleType

#: scitex-cards AppConfig class names to accept, NEWEST FIRST.
#:
#: A RENAME MIGRATION WINDOW WE DID NOT OPEN. On 2026-08-16 scitex-cards'
#: ``develop`` renamed ``ScitexTodoConfig`` -> ``ScitexCardsConfig`` with NO
#: alias. An AppConfig path in ``INSTALLED_APPS`` is a published contract, so
#: that is a migration, not a rename — alias first, then remove. Upstream did
#: the second half only.
#:
#: Hub cannot wait, because hub consumes the branch: ``.scitex-apps.json`` pins
#: this sibling to ``git_ref: "develop"`` and ``scripts/apps/install_apps.sh``
#: pip-installs it — in CI, and in ``root-init.sh`` at prod container start.
#: Meanwhile every published wheel through 0.40.0 still defines the OLD name
#: (verified by reading the 0.40.0 wheel off PyPI, which disagrees with its own
#: git tag). The two install paths hub uses disagree, so hardcoding either name
#: breaks the other.
#:
#: Order matters only where a build defines both — the expected shape if
#: upstream does add the alias — and preferring the new name means hub stops
#: depending on the deprecated one the moment it can.
#:
#: DELETE THIS SHIM once upstream ships an alias, or once a release carries the
#: new name and hub's floor requires it.
#: Tracked: cards-appconfig-renamed-without-an-alias-20260816
CARDS_APPCONFIG_NAMES = ("ScitexCardsConfig", "ScitexTodoConfig")


def cards_appconfig_path(apps_module: ModuleType) -> str:
    """Return the dotted ``INSTALLED_APPS`` path for scitex-cards' AppConfig.

    :raises RuntimeError: when the module defines none of
        :data:`CARDS_APPCONFIG_NAMES`.

    Deliberately NOT an ``ImportError``: :func:`optional_upstream_apps` treats
    that type as "this app is not installed, skip it", so raising it here would
    be swallowed and would drop the board mount silently — an app vanishing
    from a running site with nothing in the log. This must reach the operator
    at ``django.setup()``.
    """
    for name in CARDS_APPCONFIG_NAMES:
        if hasattr(apps_module, name):
            return f"scitex_cards._django.apps.{name}"

    found = [n for n in dir(apps_module) if n.endswith("Config")]
    raise RuntimeError(
        "scitex_cards is installed but its _django app defines none of "
        f"{list(CARDS_APPCONFIG_NAMES)}; it defines {found}. Upstream has "
        "renamed the AppConfig again. Add the new name to the FRONT of "
        "CARDS_APPCONFIG_NAMES in config/settings/_optional_apps.py."
    )


def _installed(module_path: str) -> ModuleType | None:
    """Import ``module_path``, or None when the package is not installed.

    Gates on the SUBMODULE the AppConfig lives in, not just the distribution:
    a package installed WITHOUT its ``_django`` app (an older wheel, or a
    checkout from before that app merged) must skip cleanly here rather than
    crash Django app-loading with ``ModuleNotFoundError``.
    """
    try:
        return import_module(module_path)
    except ImportError:
        return None


def optional_upstream_apps() -> list[str]:
    """Return ``INSTALLED_APPS`` entries for whichever upstream apps are present.

    Order is stable and matches the historical ``settings_shared`` sequence, so
    app-loading order does not change with this extraction.

    NOTE — one deliberate side effect, kept HERE rather than in the caller
    because separating it from the mount is how it would get lost: mounting the
    cards board also disables its host-side lane discovery. The board's service
    layer unions per-project lanes (default glob
    ``~/proj/*/.scitex/todo/tasks.yaml``) into every load; on the hub each
    request must see ONLY the requesting user's workspace store (injected by
    ``apps.workspace.todo_app.middleware``), so an empty glob list — the
    documented opt-out seam in that module — is set alongside the mount.
    """
    entries: list[str] = []

    if _installed("figrecipe"):
        entries.append("figrecipe._django")

    if _installed("scitex_writer"):
        entries.append("scitex_writer._django.apps.WriterEditorConfig")

    if _installed("scitex_storage._django"):
        entries.append("scitex_storage._django.apps.StorageConfig")

    # CANONICAL name. `scitex_todo` is a deprecated alias of this package
    # (renamed 2026-07-16) that warns it "ships for one transition window
    # only" — importing the alias would make the whole board mount depend on a
    # module upstream has announced it will delete, and the failure is SILENT.
    cards_apps = _installed("scitex_cards._django.apps")
    if cards_apps is not None:
        entries.append(cards_appconfig_path(cards_apps))
        os.environ["SCITEX_TODO_LANE_GLOBS"] = ""

    return entries


# EOF
