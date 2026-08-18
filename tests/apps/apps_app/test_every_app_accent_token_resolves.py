#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Every app that declares an accent must have a token that actually resolves.

WHY THIS EXISTS, and why it is not the storage test with a loop around it.

``test_storage_store_chrome.py`` guards ONE app, because in July a human
noticed one tile rendering without its accent bar. That test caught a real
regression again on 2026-08-18 — a PR deleted ``--app-accent-storage`` after
its author measured "zero consumers" by searching for ``var(--app-accent-...)``.
The consumer is not a ``var()`` call. It is a MANIFEST STRING::

    apps/workspace/storage_app/manifest.json   "accent_color": "storage"

The app names its accent, and ``data-app-accent="<name>"`` resolves
``--app-accent-<name>`` at render time. No stylesheet mentions the token, so a
usage-shaped search cannot find the dependency. A positive control proved the
search RAN; it could not prove it asked the right question.

Twelve manifests declare an accent. Exactly one had a guard. This closes that
gap, and running it immediately found a SECOND app already broken in the same
way — see the ``comms`` note below.

TWO DESIGN CHOICES WORTH KEEPING:

1. IT FOLLOWS THE IMPORT GRAPH RATHER THAN NAMING A FILE. The storage test
   hardcodes ``primitives/colors.css``. That file is being retired in favour of
   importing scitex-ui's copy, which would leave the test either failing for the
   wrong reason or, worse, reading a file that no longer participates in what
   the browser loads. Resolving ``variables.css``'s own ``@import`` chain means
   this test keeps asserting the real question — "does the token reach a page?"
   — across that migration and any future one.

2. IT REFUSES TO PASS VACUOUSLY. If the import graph resolves to nothing, or no
   manifest declares an accent, the population under test is empty and every
   per-app assertion would pass by finding nothing. That is the failure mode
   this fleet has hit repeatedly today, so it is its own named test rather than
   a comment.
"""

import json
import re
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[3]
_STATIC_ROOT = _REPO_ROOT / "static"
_MANIFEST_ROOT = _REPO_ROOT / "apps"
_ENTRY = _STATIC_ROOT / "shared" / "css" / "primitives" / "variables.css"

# BOTH @import forms, and the second one is not hypothetical.
#
#     @import url("./x.css");     <- what hub writes
#     @import "./x.css";          <- what scitex-ui 0.16.0 writes
#
# CSS allows either. This pattern matched only the first until 2026-08-18, and
# the cost was concrete: scitex-ui 0.16.0 split `primitives/colors.css` into a
# 22-line BARREL whose entire content is two bare-string imports of
# `colors/_light.css` and `colors/_dark.css`, where all 19 per-app accents now
# live. Measured against that file:
#
#     url()-only pattern  -> []                                    <- saw nothing
#     both-forms pattern  -> ['./colors/_light.css', './colors/_dark.css']
#
# So this test resolved the chain as far as the barrel, read a file that is
# present and readable and contains no tokens, and reported every app's accent
# as defined 0 times. The failure was indistinguishable from the real defect it
# exists to catch -- it would have been read as "the accents are gone" when they
# were one unfollowed hop away.
#
# That barrel has now defeated three separate instruments in this fleet on one
# day (a version-comparison script, a token-presence scan, and this test), every
# time by being a file that is exactly what you asked for and empty of what you
# wanted. When a search over a stylesheet returns nothing, check whether it can
# see BOTH import forms before concluding the tokens are absent.
_IMPORT_RE = re.compile(r"""@import\s+(?:url\(\s*)?["']([^"']+)["']\s*\)?""")

# Apps whose accent is knowingly absent, each with a reason and a removal
# condition. An entry here is a DECLARED debt, not a silenced test.
_KNOWN_MISSING: dict[str, str] = {
    # EMPTY as of 2026-08-18, and the one entry that was here is worth recording
    # because it left under its own stated condition rather than by decision.
    #
    # It read:
    #     "comms": "defined only in scitex-ui shell/theme.css, which hub does
    #               not load"
    # with the removal condition: "scitex-ui consolidates per-app accents into
    # the primitives layer hub imports, then delete this entry."
    #
    # That condition is now met. scitex-ui 0.16.0 declares --app-accent-comms in
    # primitives/colors/_{light,dark}.css, and this release makes hub import
    # that layer. comms_app's tile renders with its accent.
    #
    # HOW WE FOUND OUT is the part worth keeping: nobody checked. The entry was
    # xfail(strict), so when the token appeared the test reported
    # XPASS(strict) — a FAILURE — and named the exemption as the thing that had
    # gone stale. A non-strict xfail would have gone quietly green and this
    # entry would still be sitting here, describing a defect that no longer
    # exists, indefinitely.
    #
    # So: keep future entries xfail(strict), and give each a removal CONDITION
    # rather than only a reason. A reason explains why the debt exists; a
    # condition tells the test when to stop believing it.
}


def _resolve_import(spec: str, base: Path) -> Path | None:
    """Map one @import target to a file on disk, or None if unresolvable.

    Relative specs resolve against the importing stylesheet, exactly as a
    browser resolves them. Anything landing under a ``scitex_ui/`` path segment
    is an installed-package asset and is resolved THROUGH THE PACKAGE — that is
    the same file the static pipeline collects and serves.

    THE ``scitex_ui`` CHECK COMES FIRST, AND THAT ORDERING IS THE WHOLE FUNCTION.

    This used to redirect to the package only when the path climbed OUT of
    ``_STATIC_ROOT``, on the reasoning that an in-repo path must be an in-repo
    file. That reasoning is wrong for the path hub actually writes. From
    ``static/shared/css/primitives/variables.css``:

        ../../../scitex_ui/css/primitives/colors.css
          -> <repo>/static/scitex_ui/css/primitives/colors.css

    Three levels up from ``primitives/`` is ``static/``, not above it. So the
    resolved path sits INSIDE ``_STATIC_ROOT``, ``relative_to`` succeeds, the
    package branch is skipped, and the file is looked up in the repo — where it
    does not exist, because ``static/scitex_ui/`` is a COLLECTSTATIC ARTEFACT
    that only exists after the static pipeline runs.

    Measured 2026-08-18 with the old ordering, scitex-ui 0.16.0 installed:

        ../../../scitex_ui/css/primitives/colors.css           -> None
        ../../../scitex_ui/css/primitives/typography-vars.css  -> None
        ../../../scitex_ui/css/primitives/spacing.css          -> None
        ../../../scitex_ui/css/primitives/z-index.css          -> None
        ../utilities/effects.css                               -> resolved (hub's own)

        loaded bytes 4465, --app-accent-storage 0, CONTROL --text-primary 0

    Every upstream import silently unresolved. The control reading 0 is the tell
    and the reason this was findable: a guard reporting "accent missing" while
    ALSO unable to see ``--text-primary`` is not reporting a missing accent, it
    is reporting that it loaded almost nothing. A test asserting only the accent
    would have shown a plausible, specific, entirely wrong failure.
    """
    candidate = (base.parent / spec).resolve()
    parts = candidate.parts
    if "scitex_ui" in parts:
        try:
            import scitex_ui
        except ImportError:
            return None
        pkg_static = (Path(scitex_ui.__file__).parent / "static").resolve()

        # Map from the LAST "scitex_ui" segment, never the first.
        #
        # The installed layout contains that segment TWICE --
        # ``site-packages/scitex_ui/static/scitex_ui/css/...`` -- so taking the
        # first one re-prefixes a path that is already inside the package and
        # yields ``<pkg>/static/scitex_ui/static/scitex_ui/css/...``, which
        # resolves to nothing.
        #
        # Not hypothetical: it is exactly what a NESTED import hits. 0.16.0's
        # colors.css is a barrel importing "./colors/_light.css" relative to
        # ITSELF, i.e. relative to a file already in the package. Measured with
        # the first-segment mapping and the regex fix already in place:
        #
        #     colors.css                      1069 bytes, resolved
        #       UNRESOLVED: ./colors/_light.css
        #       UNRESOLVED: ./colors/_dark.css
        #
        # Taking the last segment handles BOTH cases with one rule: a repo-side
        # spec has one "scitex_ui" (first == last), and a package-side spec has
        # two (last is the one inside ``static/``).
        #
        # ONE MECHANISM ON PURPOSE. This first shipped alongside an
        # ``if candidate is already under pkg_static: use it as-is`` early
        # return, which handles the nested case too. Both worked, so each hid
        # the other: reverting either one alone left all 14 tests GREEN, and
        # neither could be controlled. A mechanism whose removal changes nothing
        # is untestable by construction, and two of them make the whole function
        # untestable. The early return is gone; this line is now load-bearing
        # and a control on it goes red.
        last = len(parts) - 1 - parts[::-1].index("scitex_ui")
        candidate = pkg_static / Path(*parts[last:])
        return candidate if candidate.is_file() else None
    try:
        candidate.relative_to(_STATIC_ROOT)
    except ValueError:
        return None
    return candidate if candidate.is_file() else None


def _loaded_css(entry: Path = _ENTRY, _depth: int = 0) -> str:
    """Concatenate the stylesheet at ``entry`` and everything it imports."""
    if _depth > 8 or not entry.is_file():
        return ""
    text = entry.read_text()
    for spec in _IMPORT_RE.findall(text):
        target = _resolve_import(spec, entry)
        if target is not None:
            text += "\n" + _loaded_css(target, _depth + 1)
    return text


def _declared_accents() -> list[tuple[str, str]]:
    """(manifest path relative to repo, accent name) for every declared accent."""
    found = []
    for manifest in sorted(_MANIFEST_ROOT.glob("**/manifest.json")):
        try:
            accent = (json.loads(manifest.read_text()).get("accent_color") or "").strip()
        except (json.JSONDecodeError, OSError):
            continue
        if accent:
            found.append((str(manifest.relative_to(_REPO_ROOT)), accent))
    return found


_ACCENTS = _declared_accents()


def test_the_import_graph_resolves_to_actual_css():
    """Anti-vacuity: an empty stylesheet would make every accent test pass."""
    # Arrange
    entry = _ENTRY

    # Act
    css = _loaded_css(entry)

    # Assert
    assert len(css) > 1000, (
        f"{entry} and its @import chain resolved to almost nothing; every "
        "per-app accent assertion below would pass by finding nothing"
    )


def test_some_app_declares_an_accent():
    """Anti-vacuity: an empty manifest set would parametrise to zero cases."""
    # Arrange
    root = _MANIFEST_ROOT

    # Act
    declared = _declared_accents()

    # Assert
    assert declared, (
        f"no manifest under {root} declares a non-empty accent_color; "
        "the parametrised test below would silently assert nothing"
    )


def _case(manifest: str, accent: str):
    """One parametrised case, xfail-marked when the gap is a declared debt."""
    reason = _KNOWN_MISSING.get(accent)
    marks = (pytest.mark.xfail(reason=reason, strict=True),) if reason else ()
    return pytest.param(manifest, accent, id=accent, marks=marks)


@pytest.mark.parametrize(
    "manifest, accent", [_case(m, a) for m, a in _ACCENTS]
)
def test_declared_accent_has_a_token_in_both_themes(manifest, accent):
    """A manifest accent must resolve to a token defined for light AND dark."""
    # Arrange
    css = _loaded_css()

    # Act
    definitions = re.findall(rf"--app-accent-{re.escape(accent)}:", css)

    # Assert
    assert len(definitions) == 2, (
        f"{manifest} declares accent_color='{accent}' but the stylesheets hub "
        f"actually loads define --app-accent-{accent} {len(definitions)} times "
        "(expected 2: one light, one dark). The tile will render with no accent "
        "and no error — CSS resolves a missing custom property to nothing."
    )
