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
    # Found by this test on the day it was written: comms_app has declared
    # "accent_color": "comms" while no loaded stylesheet defines the token, so
    # its tile renders with no accent — the July storage defect, live, in a
    # second app, unnoticed because CSS resolves a missing var to nothing.
    # scitex-ui carries --app-accent-comms in its shell/theme.css, which hub
    # does not load. Removal condition: scitex-ui consolidates per-app accents
    # into the primitives layer hub imports, then delete this entry.
    "comms": "defined only in scitex-ui shell/theme.css, which hub does not load",
}


def _resolve_import(spec: str, base: Path) -> Path | None:
    """Map one @import target to a file on disk, or None if unresolvable.

    Relative specs resolve against the importing stylesheet, exactly as a
    browser resolves them. A spec that climbs out of hub's static root and into
    ``scitex_ui/`` is an installed-package asset, so it is resolved through the
    package rather than the repo — that is the same file the static pipeline
    collects and serves.
    """
    candidate = (base.parent / spec).resolve()
    try:
        candidate.relative_to(_STATIC_ROOT)
    except ValueError:
        parts = candidate.parts
        if "scitex_ui" not in parts:
            return None
        try:
            import scitex_ui
        except ImportError:
            return None
        tail = Path(*parts[parts.index("scitex_ui") :])
        pkg_static = Path(scitex_ui.__file__).parent / "static"
        candidate = pkg_static / tail
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
