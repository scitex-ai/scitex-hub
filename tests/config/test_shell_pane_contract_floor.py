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

A SECOND CONTRACT NOW RIDES ON THE SAME FLOOR, added 2026-08-18. Hub stopped
forking scitex-ui's design primitives and ``@import``s them instead
(static/shared/css/primitives/variables.css), which makes the floor a claim
about FILE CONTENT as well as about a call signature. That contract fails
differently, and worse:

    file absent                 -> @import 404s, page visibly unstyled   LOUD
    file present, token absent  -> var() resolves to nothing             SILENT
    file present, value stale   -> renders wrong, passes every check     SILENT

Only the first is visible. ``--text-link`` is absent from the primitives layer
in 0.8.0 / 0.12.0 / 0.13.0 / 0.14.0 and lands in 0.14.1 -- so four releases at
or above the ORIGINAL >=0.8.0 floor would import cleanly, render a page that
looks correct, and put hub back at 2.36:1 link contrast. The floor is the only
instrument that catches it, which is why it is asserted here and not left to a
comment.

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

import re
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

#: The release that first DEFINES ``--text-link`` in the primitives layer.
#:
#: Hub stopped forking scitex-ui's primitives and now ``@import``s them
#: (static/shared/css/primitives/variables.css), so the floor became a claim
#: about FILE CONTENT as well as about a call signature. Measured 2026-08-18 by
#: reading the token out of the PUBLISHED WHEELS -- ``pip download
#: --no-cache-dir`` then read the zip, never the git tree -- with
#: ``--text-primary`` as a positive control returning 2 declarations at every
#: version, so the absences are measured rather than a broken read:
#:
#:     0.8.0 / 0.12.0 / 0.13.0 / 0.14.0   ABSENT
#:     0.14.1 onwards                     #2c5d8f (light) / #58a6ff (dark)
#:
#: OFF BY ONE FROM WHAT YOU MAY HAVE BEEN TOLD. Two other agents independently
#: reported "first appears in 0.15.0" on the same day, because both sampled
#: (0.14.0, then 0.15.0) and neither pulled 0.14.1. scitex-ui has published 31
#: versions; a hand-picked subset yields a confident wrong boundary. If you
#: revise this constant, enumerate every release from the PyPI index.
TEXT_LINK_FLOOR = Version("0.14.1")

#: The last release WITHOUT ``--text-link``. Same role as LAST_WITHOUT_PANES:
#: it makes the exclusion test assert a real boundary instead of naming a
#: number nothing checks.
LAST_WITHOUT_TEXT_LINK = Version("0.14.0")

#: What the pin must actually be, and it is deliberately ABOVE both contracts.
#:
#: 0.14.1 is all hub strictly needs. We declare 0.16.0 because a floor is read
#: by people who will not know hub does not link ``shell/theme.css``: in 0.15.0
#: ``--accent`` is present in the primitives layer but MISSING from
#: ``shell/theme.css``, so one token needs two different floors depending on
#: which file a consumer links. 0.16.0 is the first release good on every token
#: in both layers. A version that needs no caveat beats the justifiable minimum.
DECLARED_FLOOR = Version("0.16.0")

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


def test_declared_floor_excludes_every_release_without_the_link_token(
    scitex_ui_requirements: list[tuple[str, Requirement]],
) -> None:
    # Arrange — the SECOND contract on this floor, and the one with no visible
    # symptom. Hub @imports scitex-ui's primitives rather than forking them, so
    # a release that lacks `--text-link` does not 404 and does not raise: the
    # import succeeds, `var(--text-link)` resolves to nothing, and hub renders
    # link colour at 2.36:1 against a 4.5:1 AA requirement. A green build.
    # Act
    permissive = [
        (group, str(req.specifier))
        for group, req in scitex_ui_requirements
        if req.specifier.contains(LAST_WITHOUT_TEXT_LINK)
    ]

    # Assert
    assert permissive == [], (
        f"these pyproject.toml groups declare a scitex-ui range permitting "
        f"{LAST_WITHOUT_TEXT_LINK}, a release whose primitives do not define "
        f"'--text-link': {permissive}. Hub imports that layer, so the token "
        f"resolves to nothing and the WCAG link-contrast fix silently does not "
        f"arrive -- with no 404, no exception and no failing check. Raise each "
        f"floor to {DECLARED_FLOOR}."
    )


def test_declared_floor_still_admits_the_version_it_declares(
    scitex_ui_requirements: list[tuple[str, Requirement]],
) -> None:
    # Arrange — the other half: a floor raised too far is also wrong, and would
    # silently drop hub off releases that satisfy both contracts.
    #
    # This asserts against DECLARED_FLOOR rather than PANES_FLOOR because the
    # floor now answers to two contracts and must sit at or above the higher of
    # them. Asserting it still admits 0.8.0 would forbid ever satisfying the
    # token contract at all -- the two halves of this file would contradict
    # each other, and the pane half would win by being older.
    # Act
    over_raised = [
        (group, str(req.specifier))
        for group, req in scitex_ui_requirements
        if not req.specifier.contains(DECLARED_FLOOR)
    ]

    # Assert
    assert over_raised == [], (
        f"these pyproject.toml groups declare a scitex-ui range excluding "
        f"{DECLARED_FLOOR}, the version hub declares as its floor: "
        f"{over_raised}. Both contracts are satisfied there -- panes since "
        f"{PANES_FLOOR}, '--text-link' since {TEXT_LINK_FLOOR} -- so excluding "
        f"it is over-raising, not caution."
    )


def _resolve_css(path: Path, _seen: frozenset[Path] = frozenset()) -> str:
    """Read a stylesheet with its ``@import``s inlined, as a browser would.

    Necessary rather than convenient. scitex-ui 0.16.0 split
    ``primitives/colors.css`` into a 22-line BARREL that ``@import``s
    ``colors/_light.css`` and ``colors/_dark.css``; a single-file read of that
    path therefore finds no tokens at all and looks identical to a release that
    lost them. That false alarm was raised for real on 2026-08-18 before the
    barrel was noticed, which is why this walks the graph instead.

    Cycles are guarded because a self-referential import would otherwise recurse
    until the interpreter stops us, turning a stylesheet typo into a crash in
    the test suite rather than a finding.
    """
    if path in _seen or not path.is_file():
        return ""
    text = path.read_text(encoding="utf-8", errors="replace")
    seen = _seen | {path}
    for ref in re.findall(r"""@import\s+(?:url\()?["']([^"']+)["']\)?""", text):
        text += _resolve_css((path.parent / ref).resolve(), seen)
    return text


@pytest.fixture(name="installed_primitives")
def _installed_primitives() -> tuple[Path, str]:
    """The installed scitex-ui's primitives layer, ``@import``s inlined.

    Shared by the two tests below so they read the SAME bytes: one asserts the
    read happened, the other asserts what it contains. Splitting them is what
    makes a red run say which of those two things went wrong.
    """
    if find_spec("scitex_ui") is None:
        pytest.skip("scitex-ui not installed")
    import scitex_ui

    colors = (
        Path(scitex_ui.__file__).parent
        / "static"
        / "scitex_ui"
        / "css"
        / "primitives"
        / "colors.css"
    )
    return colors, _resolve_css(colors)


def test_installed_primitives_read_reaches_a_populated_stylesheet(
    installed_primitives: tuple[Path, str],
) -> None:
    # Arrange — the POSITIVE CONTROL for the test below, and it is separate
    # rather than a second assert precisely so a failure names which half broke.
    # An empty read -- wrong path, moved file, or a barrel whose tokens live in
    # children -- is indistinguishable from a genuine missing token, and all
    # THREE of those produced a wrong zero against this exact package on
    # 2026-08-18. Without this control, that ambiguity lands on whoever reads CI.
    colors, css = installed_primitives

    # Act
    control = re.findall(r"--text-primary\s*:", css)

    # Assert
    assert control, (
        f"positive control failed: '--text-primary' is not defined anywhere "
        f"reachable from {colors}. THE READ IS WRONG, NOT THE PACKAGE -- check "
        f"the path exists and that @imports were followed. Do not interpret "
        f"this as a missing token."
    )


def test_installed_primitives_actually_define_the_link_token(
    installed_primitives: tuple[Path, str],
) -> None:
    # Arrange — the DELIVERY half of the token contract, and the half this file
    # was missing entirely. The floor tests above assert the PROMISE in
    # pyproject.toml; nothing asserted that the scitex-ui actually present here
    # defines the token. Two independent facts, for the reason the module
    # docstring already gives for panes: the mounted apps are installed editable,
    # so the declared floor never participates in resolution.
    colors, css = installed_primitives

    # Act
    declarations = re.findall(r"--text-link\s*:\s*([^;]+);", css)

    # Assert
    assert declarations, (
        f"the installed scitex-ui does not define '--text-link' in its "
        f"primitives layer (read from {colors}, @imports followed; the control "
        f"test above passing means the read is sound). Hub @imports this layer, "
        f"so var(--text-link) resolves to nothing and link colour sits at "
        f"2.36:1 against a 4.5:1 AA requirement -- silently, with no 404 and no "
        f"exception. Install scitex-ui>={DECLARED_FLOOR}."
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

    # Act — an unknown pane must fail loudly at the call site, so the call
    # itself is the thing under test and is made inside the expectation.
    def call_with_unknown_pane() -> None:
        shell_context("Storage", panes={UNKNOWN_PANE: "unused"})

    # Assert
    with pytest.raises(ValueError):
        call_with_unknown_pane()


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
