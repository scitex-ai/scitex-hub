#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The scitex-ui floor must be high enough for the apps hub MOUNTS.

Hub calls ``scitex_ui.branding.shell_context()`` ZERO times, so nothing in
hub's own source reveals which version of it hub needs. The apps hub mounts
do call it, and one of them passes ``panes``:

    scitex_storage._django.views.index      panes={"ai": "unused",
                                                   "files": "unused",
                                                   "viewer": "unused"}

``panes`` arrived in scitex-ui 0.8.0. Verified by reading ``branding.py`` at
both tags rather than trusting a changelog: ``v0.7.1``'s ``shell_context()``
has no such parameter, ``v0.8.0``'s does. Below the floor that call raises
``TypeError: unexpected keyword argument 'panes'`` AT REQUEST TIME, so
``/apps/storage/`` answers 500 -- a pin problem that presents as a broken
page, several layers away from the pin that permitted it.

WHY A TEST AND NOT JUST A PIN. pip cannot derive this constraint here. The
mounted apps are installed EDITABLE from sibling checkouts at container start
(deployment/docker/common/scripts/root-init.sh), so scitex-storage's own
``scitex-ui>=0.8.0`` never participates in hub's resolution. The declared
floor and the installed reality are therefore two independent facts, and this
file asserts BOTH:

    test_declared_floor_*   the pin in pyproject.toml  (the promise)
    test_installed_*        the package actually here  (the delivery)

``test_installed_shell_context_rejects_an_unknown_pane`` is a POSITIVE CONTROL
and is the reason this file is not two asserts. "Does ``shell_context`` accept
``panes``?" is satisfied by a signature that accepts ANYTHING -- a ``**kwargs``
that silently drops it would pass the delivery test while the panes never
reach the template, which is the failure mode the pin exists to prevent. The
control asserts the function still REJECTS a pane name it does not know. Read
the two together: one says the argument is taken, the other says it is read.
"""

from __future__ import annotations

import tomllib
from importlib.util import find_spec
from pathlib import Path

import pytest
from packaging.requirements import Requirement
from packaging.version import Version

REPO = Path(__file__).resolve().parents[2]

#: The release that introduced ``shell_context(panes=...)``.
PANES_FLOOR = Version("0.8.0")

#: The last release WITHOUT it. Used to assert the floor actually excludes the
#: broken range, rather than merely mentioning a number.
LAST_WITHOUT_PANES = Version("0.7.1")

#: A pane name scitex-ui does not know. Any value outside PANE_NAMES works;
#: this one is obviously synthetic so a reader does not mistake it for a real
#: pane that was removed.
UNKNOWN_PANE = "not-a-real-pane"


@pytest.fixture(name="scitex_ui_requirements")
def _scitex_ui_requirements() -> list[tuple[str, Requirement]]:
    """Every declared scitex-ui dependency, tagged with the group declaring it.

    Sweeps the core ``dependencies`` AND every ``optional-dependencies`` group,
    because hub declares scitex-ui in the ``all`` extra rather than in the core
    list. Checking only one location is how a second, stale declaration
    survives: whichever group resolution actually uses is the one that decides
    the installed version, so EVERY group must state a floor that holds.

    Fails loudly rather than skipping when none is found: a renamed or deleted
    dependency must break this guard, not quietly satisfy it. A skip here would
    read as "the floor is fine" precisely when the floor stopped existing.
    """
    pyproject = tomllib.loads((REPO / "pyproject.toml").read_text())
    project = pyproject["project"]

    groups: dict[str, list[str]] = {"dependencies": project.get("dependencies", [])}
    for extra, raws in project.get("optional-dependencies", {}).items():
        groups[f"optional-dependencies.{extra}"] = raws

    found = [
        (group, req)
        for group, raws in groups.items()
        for req in (Requirement(raw) for raw in raws)
        if req.name == "scitex-ui"
    ]

    assert found, (
        "no scitex-ui dependency found anywhere in pyproject.toml "
        f"(searched {sorted(groups)}). The pane-contract floor this file "
        "guards has no declaration left to guard."
    )
    return found


def test_declared_floor_excludes_every_release_without_panes(
    scitex_ui_requirements: list[tuple[str, Requirement]],
) -> None:
    # Arrange — the last release whose shell_context() has no `panes`.
    # Act
    permissive = [
        (group, str(req.specifier))
        for group, req in scitex_ui_requirements
        if req.specifier.contains(LAST_WITHOUT_PANES)
    ]

    # Assert — a floor that still admits 0.7.1 admits the 500.
    assert permissive == [], (
        f"these pyproject.toml groups declare a scitex-ui range permitting "
        f"{LAST_WITHOUT_PANES}, a release whose shell_context() has no "
        f"'panes' parameter: {permissive}. Mounted apps pass it, so that "
        f"resolution answers 500 on /apps/storage/. Raise each floor to "
        f"{PANES_FLOOR}."
    )


def test_declared_floor_still_admits_the_release_that_added_panes(
    scitex_ui_requirements: list[tuple[str, Requirement]],
) -> None:
    # Arrange — the other half: a floor raised too far is also wrong, and
    # would silently drop hub off releases that satisfy the contract.
    # Act
    over_raised = [
        (group, str(req.specifier))
        for group, req in scitex_ui_requirements
        if not req.specifier.contains(PANES_FLOOR)
    ]

    # Assert
    assert over_raised == [], (
        f"these pyproject.toml groups declare a scitex-ui range excluding "
        f"{PANES_FLOOR}, the release that introduced the pane contract: "
        f"{over_raised}."
    )


def test_installed_shell_context_accepts_the_pane_declaration() -> None:
    # Arrange — exercise the real call the request path makes, not the
    # signature. inspect.signature() would also pass on a **kwargs sink.
    from scitex_ui.branding import shell_context

    declaration = {"ai": "unused", "files": "unused", "viewer": "unused"}

    # Act
    context = shell_context("Storage", panes=declaration)

    # Assert — accepted AND carried into the template context, because
    # accepting an argument and dropping it look identical from the caller.
    assert context["panes"] == declaration


def test_installed_shell_context_rejects_an_unknown_pane() -> None:
    # Arrange — POSITIVE CONTROL. See this module's docstring: without it,
    # a **kwargs signature that discards `panes` satisfies the test above.
    from scitex_ui.branding import shell_context

    # Act / Assert — an unknown pane must fail loudly at the call site.
    with pytest.raises(ValueError):
        shell_context("Storage", panes={UNKNOWN_PANE: "unused"})


@pytest.mark.skipif(
    find_spec("scitex_storage") is None,
    reason="scitex-storage not installed (optional mount)",
)
def test_installed_scitex_ui_honours_the_mounted_apps_declaration() -> None:
    # Arrange — end to end, with the declaration the mounted app actually
    # ships rather than a copy of it restated here. A copy would assert that
    # this file agrees with itself while storage was free to change.
    from scitex_storage._django import views
    from scitex_ui.branding import shell_context

    declaration = views.SHELL_PANES

    # Act
    context = shell_context("Storage", panes=declaration)

    # Assert
    assert context["panes"] == declaration
