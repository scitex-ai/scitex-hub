"""Landing V2 contract: real assets, concise product story, a11y, and budgets.

Card: hub-landing-reference-integration-20260918.
These tests intentionally inspect production templates and static assets. They guard
against the reference prototype's two dangerous shortcuts: invented product UI and a
670 KB inline/base64 monolith.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

import pytest
from django.template.loader import render_to_string
from django.utils import translation

ROOT = Path(__file__).resolve().parents[3]
TEMPLATE_DIR = ROOT / "apps/infra/public_app/templates/public_app"
STATIC_DIR = ROOT / "apps/infra/public_app/static/public_app"
LANDING = TEMPLATE_DIR / "landing.html"
HERO = TEMPLATE_DIR / "landing_partials/landing_hero.html"
MODULES = TEMPLATE_DIR / "landing_partials/landing_modules.html"
CSS = STATIC_DIR / "css/landing-reference-v2.css"
TS = STATIC_DIR / "ts/landing/reference-v2.ts"
ASSETS = STATIC_DIR / "images/landing-v2"

BUILT_IN_APPS = (
    "Scholar",
    "Storage",
    "Stats",
    "FigRecipe",
    "Writer",
    "Agents + Chat",
    "Cards",
)


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_landing_uses_the_v2_partial_assets_and_keeps_pricing():
    source = _text(LANDING)
    assert all(
        marker in source
        for marker in (
            "landing-reference-v2.css",
            "landing_hero.html",
            "landing_modules.html",
            "landing_pricing.html",
            "public_app/landing/reference-v2",
        )
    )


def test_landing_uses_the_minimal_shell_without_workspace_js():
    """Anonymous visitors skip workspace-only JS (tree, viewer, sidebar).

    The landing renders no workspace panes, so the base template drops
    those bundles when the view sets minimal_shell — the page stays light
    while the app shell is untouched.
    """
    from django.test import Client

    response = Client().get("/landing/")
    assert response.status_code == 200
    assert response.context["minimal_shell"] is True
    html = response.content.decode()
    assert "Connect literature, files, analysis" in html
    # Keyboard users get a skip link whose target exists on the page.
    assert 'href="#main-content"' in html
    assert 'id="main-content"' in html
    for dropped in (
        "workspace-tree-init",
        "workspace-viewer-init",
        "workspace-panel-resizer",
        "workspace-sidebar",
        "module-tab-switcher",
        "module-reorder",
        "module-tab-context-menu",
        "nav-prefetch",
        "dev-install",
    ):
        assert dropped not in html, dropped
    for kept in (
        "theme-switcher",
        "global-ai-chat",
        "reference-v2",
    ):
        assert kept in html, kept


def test_hero_keeps_real_entry_contracts_and_research_photography():
    source = _text(HERO)
    assert all(
        marker in source
        for marker in (
            "{% url 'auth_app:signup' %}",
            "{% url 'auth_app:signin' %}",
            "#pricing",
            "research-collaboration-640.webp",
            "research-collaboration-1280.webp",
            'fetchpriority="high"',
            "Edward Jenner",
            "https://www.pexels.com/license/",
            "not SciTeX customers, employees, or endorsers",
        )
    )


def test_v2_explains_one_context_builtins_and_extension_contract():
    source = _text(MODULES)
    expected = (
        "SciTeX Hub",
        "one project context",
        *BUILT_IN_APPS,
        "Custom Apps",
        "same contract",
        "Phone",
        "Laptop",
        "HPC + SSH",
    )
    assert all(label in source for label in expected)


def test_v2_uses_real_product_captures_and_clew_dag_with_provenance():
    source = _text(MODULES)
    provenance = _text(ASSETS / "PROVENANCE.md")
    assert all(
        marker in source
        for marker in (
            "hub-1200.webp",
            "scholar-1200.webp",
            "figrecipe-1200.webp",
            "writer-1200.webp",
            "clew-dag.png",
            "Claim",
            "Output",
            "Processing",
            "Raw data",
            "https://github.com/scitex-ai/scitex-clew",
        )
    )
    assert all(
        marker in provenance
        for marker in (
            "hub-demo.mp4",
            "scholar-demo.mp4",
            "visualizer-demo.mp4",
            "writer-demo.mp4",
            "d0bc3e398f9214e0b1423afe0d467c520b588be656f8b3ced37cea7608393508",
            "Pexels License",
            "no endorsement",
        )
    )
    assert _sha256(ASSETS / "clew-dag.png") == (
        "d0bc3e398f9214e0b1423afe0d467c520b588be656f8b3ced37cea7608393508"
    )


def test_carousel_markup_is_semantic_manual_and_lazy():
    source = _text(MODULES)
    assert all(
        marker in source
        for marker in (
            'role="region"',
            'aria-roledescription="carousel"',
            "aria-label=\"{% trans 'Previous product screen' %}\"",
            "aria-label=\"{% trans 'Next product screen' %}\"",
            'role="tablist"',
            'aria-live="polite"',
            'loading="lazy"',
        )
    )
    assert "autoplay" not in source.lower()
    assert "data:image" not in source.lower()


def test_every_content_image_has_dimensions_and_nonempty_alt():
    source = _text(HERO) + _text(MODULES)
    tags = re.findall(r"<img\b[^>]*>", source, flags=re.S)
    assert tags
    assert all(re.search(r'\bwidth="\d+"', tag) for tag in tags)
    assert all(re.search(r'\bheight="\d+"', tag) for tag in tags)
    assert all(re.search(r'\balt="[^\"]+"', tag) for tag in tags)


def test_no_synthetic_ui_or_large_inline_payload_returns():
    combined = "\n".join((_text(HERO), _text(MODULES), _text(LANDING), _text(TS)))
    forbidden = (
        "Signal response over time",
        "illustrative product-design walkthrough",
        "synthetic chart",
        "data:image",
        "base64,",
    )
    assert all(term.lower() not in combined.lower() for term in forbidden)
    assert len(_text(HERO).encode()) < 20_000
    assert len(_text(MODULES).encode()) < 35_000
    assert len(_text(CSS).encode()) < 45_000
    assert len(_text(TS).encode()) < 12_000


def test_landing_assets_stay_inside_the_page_budget():
    files = [path for path in ASSETS.iterdir() if path.is_file()]
    media = [path for path in files if path.suffix.lower() in {".jpg", ".webp", ".png"}]
    assert media
    assert max(path.stat().st_size for path in media) <= 350_000
    assert sum(path.stat().st_size for path in media) <= 2_500_000


def test_styles_keep_brand_contrast_touch_targets_and_reduced_motion():
    css = re.sub(r"\s+", " ", _text(CSS))
    assert "linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%)" in css
    assert "--landing-gold: #b8956a" in css
    assert "min-width: 44px" in css
    assert "min-height: 44px" in css
    assert "@media (prefers-reduced-motion: reduce)" in css
    assert ":focus-visible" in css


def test_mobile_japanese_hero_keeps_words_on_semantic_lines():
    # Arrange
    hero = _text(HERO)
    css = re.sub(r"\s+", " ", _text(CSS))
    # Act
    contracts = {
        "line_one": '<span>{% trans "A platform" %}</span>' in hero,
        "line_two": '<span>{% trans "for science." %}</span>' in hero,
        "ja_size": ".landing-v2-hero h1:lang(ja)" in css,
        "narrow_fit": "font-size: clamp(1.65rem, 8vw, 4rem)" in css,
        "no_word_split": "h1:lang(ja) span { white-space: nowrap;" in css,
    }
    # Assert
    assert contracts == {
        "line_one": True,
        "line_two": True,
        "ja_size": True,
        "narrow_fit": True,
        "no_word_split": True,
    }


def test_carousel_script_is_manual_keyboard_and_swipe_only():
    source = _text(TS)
    assert all(
        marker in source
        for marker in (
            '"ArrowLeft"',
            '"ArrowRight"',
            '"pointerdown"',
            '"pointerup"',
            "aria-selected",
        )
    )
    assert "setInterval" not in source
    assert "autoplay" not in source.lower()


@pytest.mark.parametrize(
    ("template", "ja_needle", "en_needle"),
    [
        (
            "public_app/landing_partials/landing_hero.html",
            "科学のための",
            "A platform",
        ),
        (
            "public_app/landing_partials/landing_modules.html",
            "ひとつのプロジェクト文脈",
            "one project context",
        ),
        (
            "public_app/landing_partials/landing_modules.html",
            "実際の SciTeX Cloud 画面",
            "Actual SciTeX Cloud screens",
        ),
    ],
)
def test_v2_copy_switches_cleanly_between_english_and_japanese(
    template, ja_needle, en_needle, compiled_catalogs
):
    del compiled_catalogs
    with translation.override("ja"):
        ja_html = render_to_string(template, {})
    with translation.override("en"):
        en_html = render_to_string(template, {})
    assert ja_needle in ja_html and en_needle not in ja_html
    assert en_needle in en_html and ja_needle not in en_html
