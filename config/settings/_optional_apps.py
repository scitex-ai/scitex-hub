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


#: OPERATOR-FACING name for the cards store, in the hub's own
#: ``SCITEX_HUB_<X>`` namespace (ADR-0001, ``config/_env.py``). Exactly the
#: shape ``SCITEX_HUB_CROSSREF_DB_PATH`` -> ``CROSSREF_DB_PATH`` already has
#: for the citation-graph service: the deployment states the value once, in
#: ``deployment/docker/envs/.env.<env>``, under the prefix every other hub
#: setting uses, and the hub hands it to the package under the name that
#: package reads. A hub deployment should not have to know a sibling's
#: private variable spelling to be configured.
CARDS_STORE_HUB_ENV = "SCITEX_HUB_CARDS_STORE"

#: The name scitex-cards ITSELF reads (``scitex_cards._db.ENV_DB``). The hub
#: does not get to choose it, which is exactly why the hub-prefixed name above
#: exists — and why this one is still honoured first below.
CARDS_STORE_UPSTREAM_ENV = "SCITEX_CARDS_DB"


def publish_cards_store_target(environ: dict | None = None) -> str | None:
    """Hand scitex-cards the store target THIS DEPLOYMENT chose. Or nothing.

    THE HUB NEVER CONFIGURED ONE AND THAT IS THE WHOLE DEFECT. The board's card
    DATA comes from the store ``scitex_cards`` resolves with no argument, and
    since the 2026-08-13 zero-config abolition that resolver REFUSES to invent a
    filename — it raises ``StoreTargetNotConfigured``. Measured on this branch
    against the real URLconf with a signed-in user: ``/apps/cards/graph`` 500s,
    which is what the operator saw as 「cards が読み込めていない。」 Nothing in
    ``config/``, ``deployment/`` or ``scripts/`` set ``$SCITEX_CARDS_DB`` or the
    ``store.target`` config key, on any environment, so every hub deployment was
    in that state.

    Precedence, and each tier is deliberate:

    1. ``$SCITEX_CARDS_DB`` already set -> LEFT ALONE. A developer or a test
       that exports the package's own variable has said something more specific
       than the deployment did, and a settings module that overwrites it would
       silently move them to a different store. Returned so the caller can log
       what won.
    2. ``$SCITEX_HUB_CARDS_STORE`` set -> published as ``$SCITEX_CARDS_DB``.
       This is the tier that fixes the defect: it gives a deployment a
       conventional place to state the target.
    3. NEITHER -> ``None``, and NOTHING IS SET. No literal DSN is written here,
       not even the fleet's per-host ``postgresql://…:55432/scitex_cards``
       convention. A hardcoded default is precisely the silent fallback
       upstream abolished after it served a store frozen eight days earlier
       while the fleet wrote elsewhere, and it would look healthy the whole
       time. The unconfigured state is instead REPORTED, as an actionable 404
       naming this variable — see
       ``apps.workspace.todo_app.cards_store_provisioning``.

    An EMPTY value counts as unset at every tier, matching the resolver's own
    ``if value:`` test; otherwise ``SCITEX_HUB_CARDS_STORE=`` in a ``.env`` file
    would publish an empty ``$SCITEX_CARDS_DB`` and mean something different
    here than it does one call downstream.

    :param environ: mapping to read and write; defaults to ``os.environ``.
        Present so a test can prove the precedence without mutating the
        process, not as a general seam.
    :returns: the target now in effect, or ``None`` when nobody chose one.
    """
    env = os.environ if environ is None else environ

    already = env.get(CARDS_STORE_UPSTREAM_ENV)
    if already:
        return already

    chosen = env.get(CARDS_STORE_HUB_ENV)
    if chosen:
        env[CARDS_STORE_UPSTREAM_ENV] = chosen
        return chosen

    return None


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

    SECOND SIDE EFFECT, SAME REASON: mounting the board also publishes the
    deployment's chosen card store (:func:`publish_cards_store_target`). It
    belongs next to the mount because a mounted board with no store is the
    defect this fixes — the two are one decision, and splitting them is how
    the second half gets forgotten on the next environment.
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
        publish_cards_store_target()

    return entries


# EOF
