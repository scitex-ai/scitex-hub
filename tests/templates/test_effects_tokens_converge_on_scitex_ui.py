"""hub's utilities/effects.css must not redefine tokens scitex-ui's primitives own.

primitives/variables.css imports effects.css LAST, so any token both files
define resolves to hub's flat value: that is how --transition-* ran at
0.2/0.3/0.5 s while spacing.css declared 150/200/300 ms, and how a flat
--border-color beat scitex-ui's theme-aware one in dark mode. Measured by
scitex-ui 2026-08-23 / 2026-09-04; hub converged 2026-09-04.
"""

import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
EFFECTS = REPO / "static/shared/css/utilities/effects.css"

OWNED_BY_SCITEX_UI = ("--transition-fast", "--transition-normal", "--transition-slow", "--border-color")


def _declared(css: str):
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    return set(re.findall(r"(--[a-z0-9-]+)\s*:", css))


def test_effects_css_no_longer_declares_scitex_ui_tokens():
    declared = _declared(EFFECTS.read_text(encoding="utf-8"))
    assert declared, "Control: effects.css declares no token at all; the parser saw nothing"
    clashing = sorted(t for t in OWNED_BY_SCITEX_UI if t in declared)
    assert not clashing, f"effects.css redefines tokens scitex-ui owns: {clashing}"


def test_the_detector_sees_a_planted_clash():
    planted = "/* comment */\n:root {\n  --transition-fast: 0.2s;\n  --shadow-x: 0;\n}\n"
    assert "--transition-fast" in _declared(planted)
