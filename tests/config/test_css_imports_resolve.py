#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Every ``@import`` in hub's CSS must point at a file that exists.

WHY THIS EXISTS — it was paid for three times in one afternoon.

Removing hub's forked primitives left dangling ``@import`` targets. The failure
surfaces as ``whitenoise MissingFileError`` from
``test_collectstatic_succeeds_with_hashed_urls`` — a real guard, and the right
one, with two properties that made it expensive to work against:

1. IT REPORTS ONE MISSING FILE AT A TIME. collectstatic stops at the first
   unresolvable reference, so a change that orphans four files takes four
   round trips of ~14 minutes each to discover, and each round looks like a
   fresh, different bug. Measured: colors.css, then typography-vars.css, with
   spacing.css and z-index.css still queued behind them.
2. IT CANNOT RUN HERE. It imports Django settings; hub's settings
   ``import scitex as stx``; the scitex umbrella hard-pins ``scitex-ui==0.6.0``
   — the version PR #650 exists to move away from. So the guard is unrunnable
   in an environment carrying the version hub's own pyproject declares.
   (Card: hub-settings-import-the-umbrella-for-one-decorator-20260818.)

This test is the cheap complement, not a replacement: PURE FILE WALK, no Django,
no settings, no umbrella. It reports ALL dangling targets at once, in under a
second, in any environment. collectstatic remains the authority on what the
static pipeline actually accepts.

WHAT IT DELIBERATELY DOES NOT DO: hash, rewrite, or verify collection order.
Those are collectstatic's job and duplicating them here would create a second
opinion about the same question — the failure mode where two mechanisms mask
each other and neither can be controlled.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
_CSS_ROOT = _REPO_ROOT / "static"

#: BOTH forms. ``@import url("x.css")`` is what hub writes; ``@import "x.css"``
#: is what scitex-ui 0.16.0's colors.css barrel writes. A matcher accepting only
#: the first reads that barrel as importing nothing — which is how a sibling
#: guard reported every per-app accent as missing while the tokens sat one
#: unfollowed hop away.
_IMPORT_RE = re.compile(r"""@import\s+(?:url\(\s*)?["']([^"']+)["']\s*\)?""")


def _resolve(spec: str, base: Path) -> Path | None:
    """Where a browser would look for ``spec`` imported from ``base``."""
    candidate = (base.parent / spec).resolve()
    parts = candidate.parts
    if "scitex_ui" in parts:
        # An installed-package asset. Anchor on the LAST "scitex_ui" segment:
        # the installed layout is site-packages/scitex_ui/static/scitex_ui/...,
        # so anchoring on the first re-prefixes a path already inside the
        # package and resolves to nothing.
        try:
            import scitex_ui
        except ImportError:
            return None
        pkg_static = (Path(scitex_ui.__file__).parent / "static").resolve()
        last = len(parts) - 1 - parts[::-1].index("scitex_ui")
        candidate = pkg_static / Path(*parts[last:])
    return candidate if candidate.is_file() else None


@pytest.fixture(name="import_scan", scope="module")
def _import_scan() -> tuple[list[str], int]:
    """Return (dangling "file:line -> target" strings, count of resolved ones).

    Both halves come from ONE pass, so the control cannot describe a different
    population than the assertion.
    """
    dangling: list[str] = []
    resolved = 0
    for css in sorted(_CSS_ROOT.rglob("*.css")):
        try:
            text = css.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for lineno, line in enumerate(text.splitlines(), 1):
            for spec in _IMPORT_RE.findall(line):
                if spec.startswith(("http://", "https://", "//", "data:")):
                    continue  # remote or inline; not ours to resolve
                if _resolve(spec, css) is None:
                    rel = css.relative_to(_REPO_ROOT)
                    dangling.append(f"{rel}:{lineno} -> {spec}")
                else:
                    resolved += 1
    return dangling, resolved


def test_the_css_scan_actually_found_stylesheets_to_check(
    import_scan: tuple[list[str], int],
) -> None:
    # Arrange -- POSITIVE CONTROL, its own test rather than a second assert so a
    # red run says whether the SCAN broke or the IMPORTS did. Without it, "no
    # dangling imports" is returned identically by a clean tree and by a walk
    # that read nothing (wrong root, renamed directory, unreadable files).
    _, resolved = import_scan

    # Act
    found_working_imports = resolved > 0

    # Assert
    assert found_working_imports, (
        f"positive control failed: not one resolvable @import was found under "
        f"{_CSS_ROOT}. THE SCAN IS WRONG, NOT THE CSS -- check the root exists "
        f"and contains .css files. Do not read this as 'no dangling imports'."
    )


def test_no_css_import_points_at_a_missing_file(
    import_scan: tuple[list[str], int],
) -> None:
    # Arrange -- the defect: an @import whose target does not exist. The browser
    # silently drops it, so the page renders unstyled WITHOUT erroring; the loud
    # failure comes later and elsewhere, from collectstatic's manifest pass.
    dangling, _ = import_scan

    # Act
    # (the walk is the act; performed once in the fixture)

    # Assert
    assert dangling == [], (
        f"these @import targets do not exist: {dangling}. A missing stylesheet "
        f"is dropped silently by the browser and breaks `collectstatic` under "
        f"ManifestStaticFilesStorage. If the target moved into scitex-ui, point "
        f"at it via the package path; if it is redundant with another import, "
        f"delete the line."
    )
