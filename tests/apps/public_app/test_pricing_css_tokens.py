"""The landing pricing CSS must only reference tokens that exist in the bundle.

The 2026-09-11 pricing-card redesign is token-based on purpose: the operator
ruled against arbitrary colours, and the previous revision of this file
referenced ``--primary-color`` / ``--secondary-color`` / ``--text-light`` /
``--light-gray`` / ``--border-radius`` — none of which is defined anywhere in
the loaded scitex-ui primitives or hub overrides — so those declarations
silently resolved to invalid and the cards rendered square with full-black
"muted" text. A CSS file that spells a token name correctly but references a
token that does not exist fails in the browser with no error at all, which is
exactly why this guard lives in the suite.

Scope: ``apps/.../css/landing/11-pricing.css`` — the file this test was written
for. A var is "defined" if it appears as ``--name:`` in the scitex-ui
primitives (installed package), in the hub variables.css / bootstrap-override
layer, or in any of the landing CSS files (cross-references within the bundle).
Fallbacks (``var(--x, fallback)``) are allowed — the first argument still must
resolve.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[3]

PRICING_CSS = PROJECT_ROOT / "apps" / "infra" / "public_app" / "static" / "public_app" / "css" / "landing" / "11-pricing.css"
LANDING_CSS_DIR = PRICING_CSS.parent
PRIMITIVES = PROJECT_ROOT / "static" / "shared" / "css" / "primitives" / "variables.css"
# The scitex-ui package ships the actual token definitions; the hub repo's
# variables.css only @import's them. Read the installed package directly so the
# test works on a fresh checkout (where the .mo/.css of scitex-ui is present
# as an installed dependency but not vendored into the repo).
import importlib.util


def _scitex_ui_primitives_dir() -> Path | None:
    spec = importlib.util.find_spec("scitex_ui")
    if spec is None or not spec.origin:
        return None
    root = Path(spec.origin).resolve().parent
    candidate = root / "static" / "scitex_ui" / "css" / "primitives"
    return candidate if candidate.is_dir() else None


# Tokens the landing files may reference that are defined in a sibling file
# that variables.css does not import (effects.css) or in the bootstrap
# override layer.
KNOWN_EXTRA = {
    "--container-max-width",
    "--transition-fast",
    "--transition-normal",
    "--transition-slow",
}


def _defined_tokens() -> set[str]:
    tokens: set[str] = set()

    def scan(path: Path) -> None:
        if not path.is_file():
            return
        for m in re.finditer(r"(?m)^\s*(--[A-Za-z0-9_-]+)\s*:", path.read_text(encoding="utf-8", errors="replace")):
            tokens.add(m.group(1))

    for css in LANDING_CSS_DIR.glob("*.css"):
        scan(css)
    scan(PRIMITIVES)
    # bootstrap-override layout/typography can define layout tokens
    override_dir = PROJECT_ROOT / "static" / "shared" / "css" / "base" / "bootstrap-override"
    for css in override_dir.rglob("*.css"):
        scan(css)

    scitex_ui_dir = _scitex_ui_primitives_dir()
    if scitex_ui_dir is not None:
        for css in scitex_ui_dir.rglob("*.css"):
            scan(css)
        # scitex_ui's variables.css also @import's per-layer files
        scan(scitex_ui_dir / "variables.css")

    tokens |= KNOWN_EXTRA
    return tokens


def _referenced_tokens() -> list[tuple[Path, str]]:
    refs: list[tuple[Path, str]] = []
    for css in [PRICING_CSS]:
        text = css.read_text(encoding="utf-8", errors="replace")
        # strip /* ... */ comments so we don't flag doc prose
        text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
        for m in re.finditer(r"var\(\s*(--[A-Za-z0-9_-]+)", text):
            refs.append((css, m.group(1)))
    return refs


def test_landing_css_references_only_defined_tokens() -> None:
    defined = _defined_tokens()
    refs = _referenced_tokens()
    assert refs, "guard is vacuous: no var() references found in the landing CSS"
    undefined = sorted({token for _, token in refs if token not in defined})
    assert not undefined, (
        "Landing CSS references tokens with no definition in the loaded bundle "
        f"(they resolve to invalid and the rule silently drops): {undefined}. "
        "Either use an existing scitex-ui/hub token or add the definition — "
        "see static/shared/css/primitives/variables.css for the import list."
    )


def test_pricing_grid_anchors_cta_and_equalizes_rows() -> None:
    """The two layout guarantees the operator asked for:

    - ``grid-auto-rows: 1fr`` (or an equivalent) on ``.pricing-grid`` so cards
      in the same row are the same height;
    - ``margin-top: auto`` (or an equivalent) on ``.pricing-action`` so the
      CTA sits at the bottom of its card regardless of feature-list length.

    Assert on the actual rule so a future "cleanup" that drops one of them
    fails here rather than in a screenshot review.
    """
    css = (LANDING_CSS_DIR / "11-pricing.css").read_text(encoding="utf-8")
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)

    def rule(selector: str) -> str:
        m = re.search(re.escape(selector) + r"\s*\{([^{}]*)\}", css)
        assert m, f"{selector} not found in 11-pricing.css"
        return m.group(1)

    grid = rule(".pricing-grid")
    assert "grid-auto-rows" in grid, ".pricing-grid must set grid-auto-rows for equal row heights"

    action = rule(".pricing-action")
    assert re.search(r"margin-top\s*:\s*auto", action), (
        ".pricing-action must anchor the CTA to the bottom (margin-top:auto)"
    )

    card = rule(".pricing-card")
    assert "display: flex" in card and "flex-direction: column" in card, (
        ".pricing-card must be a flex column for the CTA anchor to work"
    )
