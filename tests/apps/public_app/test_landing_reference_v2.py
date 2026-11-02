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
GALLERY = TEMPLATE_DIR / "landing_partials/landing_app_gallery.html"
CSS = STATIC_DIR / "css/landing-reference-v2.css"
TS = STATIC_DIR / "ts/landing/reference-v2.ts"
ASSETS = STATIC_DIR / "images/landing-v2"

BUILT_IN_APPS = (
    "Scholar",
    "Stats",
    "FigRecipe",
    "Writer",
)
# NOTE: Storage, Cards, and Agents + Chat have no on-page landing presence
# yet (2026-09-28); add them here when the copy names them.


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


def test_hero_keeps_real_entry_contracts_without_stock_photography():
    source = _text(HERO)
    assert all(
        marker in source
        for marker in (
            "{% url 'auth_app:signup' %}",
            "{% url 'auth_app:signin' %}",
            "#pricing",
        )
    )
    # Keep provenance in the asset record without covering the hero photograph
    # with attribution or promotional text.
    assert "research-collaboration-" not in source
    assert "landing_app_gallery.html" in source
    assert "<figcaption>" not in source
    provenance = _text(ASSETS / "PROVENANCE.md")
    assert "Edward Jenner" in provenance
    assert "https://www.pexels.com/license/" in provenance


def test_v2_connects_app_previews_to_the_toolkit_workflow():
    source = _text(MODULES) + _text(GALLERY)
    expected = (
        "Screenshots of SciTeX® Cloud",
        "AI Agent + SciTeX®",
        *BUILT_IN_APPS,
        "MCP tools",
        "Trace claims back to their sources",
    )
    assert all(label in source for label in expected)


def test_v2_uses_real_product_captures_and_clew_dag_with_provenance():
    source = _text(MODULES) + _text(GALLERY)
    provenance = _text(ASSETS / "PROVENANCE.md")
    assert all(
        marker in source
        for marker in (
            "scholar-20261102-1200.webp",
            "figrecipe-20261102-1200.webp",
            "writer-20261102-1200.webp",
            "stats-20261102-1200.webp",
            "live-paper-20261102-1200.webp",
            "clew-dag-640.webp",
            "Forward",
            "Backward",
            "Source data → inputs–executable–outputs steps",
            "Claims → outputs–executable–inputs steps → source data",
            "https://scitex.ai/ywatanabe/paper-scitex-clew/",
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


def test_carousel_markup_keeps_manual_controls_and_quiet_automatic_updates():
    source = _text(MODULES) + _text(GALLERY)
    assert all(
        marker in source
        for marker in (
            'role="region"',
            'aria-roledescription="carousel"',
            "aria-label=\"{% trans 'Previous screenshot' %}\"",
            "aria-label=\"{% trans 'Next screenshot' %}\"",
            'role="tablist"',
            'aria-live="off"',
            "data-carousel-rotation",
            'loading="lazy"',
        )
    )
    assert "autoplay" not in source.lower()
    assert "data:image" not in source.lower()


def test_every_content_image_has_dimensions_and_nonempty_alt():
    source = _text(HERO) + (_text(MODULES) + _text(GALLERY))
    tags = re.findall(r"<img\b[^>]*>", source, flags=re.S)
    assert tags
    assert all(re.search(r'\bwidth="\d+"', tag) for tag in tags)
    assert all(re.search(r'\bheight="\d+"', tag) for tag in tags)
    assert all(re.search(r'\balt="[^\"]+"', tag) for tag in tags)


def test_no_synthetic_ui_or_large_inline_payload_returns():
    combined = "\n".join(
        (_text(HERO), (_text(MODULES) + _text(GALLERY)), _text(LANDING), _text(TS))
    )
    forbidden = (
        "Signal response over time",
        "illustrative product-design walkthrough",
        "synthetic chart",
        "data:image",
        "base64,",
    )
    assert all(term.lower() not in combined.lower() for term in forbidden)
    assert len(_text(HERO).encode()) < 20_000
    assert len((_text(MODULES) + _text(GALLERY)).encode()) < 35_000
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
    assert "linear-gradient(135deg, #d99a06 0%, #b87a02 100%)" in css
    assert "--landing-gold: #b8956a" in css
    assert "min-width: 44px" in css
    assert "min-height: 44px" in css
    assert "@media (prefers-reduced-motion: reduce)" in css
    assert ":focus-visible" in css


def test_mobile_japanese_hero_allows_the_full_heading_to_wrap():
    # Arrange
    hero = _text(HERO)
    css = re.sub(r"\s+", " ", _text(CSS))
    # Act
    contracts = {
        "headline": '<span>{% trans "Open-source Ecosystem for Scientific Research" %}</span>'
        in hero,
        "ja_size": ".landing-v2-hero h1:lang(ja)" in css,
        "narrow_fit": "font-size: clamp(1.65rem, 8vw, 4rem)" in css,
        "wrap_translation": "h1:lang(ja) span { white-space: normal;" in css,
    }
    # Assert
    assert contracts == {
        "headline": True,
        "ja_size": True,
        "narrow_fit": True,
        "wrap_translation": True,
    }


def test_carousel_keeps_manual_controls_and_respects_motion_preferences():
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
    assert "ROTATION_INTERVAL = 6000" in source
    assert "prefers-reduced-motion: reduce" in source
    assert "visibilitychange" in source


@pytest.mark.parametrize(
    ("template", "ja_needle", "en_needle"),
    [
        (
            "public_app/landing_partials/landing_hero.html",
            "科学研究のためのオープンソース・エコシステム",
            "Open-source Ecosystem for Scientific Research",
        ),
        (
            "public_app/landing_partials/landing_modules.html",
            "AIエージェント + SciTeX®",
            "AI Agent + SciTeX®",
        ),
        (
            "public_app/landing_partials/landing_app_gallery.html",
            "SciTeX® Cloudのスクリーンショット",
            "Screenshots of SciTeX® Cloud",
        ),
        (
            "public_app/landing_partials/landing_app_gallery.html",
            "11枚中11枚目",
            "11 of 11: Agentic Journal",
        ),
        (
            "public_app/landing_partials/landing_app_gallery.html",
            "サンプル2群データ",
            "Sample two-group analysis",
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


def test_carousel_has_eleven_current_application_slides():
    assert (_text(MODULES) + _text(GALLERY)).count("data-carousel-slide") == 11


def test_carousel_has_eleven_dots_ending_in_agentic_journal():
    from apps.infra.public_app.templatetags.landing_capture_tabs import (
        capture_tab_groups,
    )

    assert 'data-carousel-dot="{{ app.index }}"' in _text(GALLERY)
    assert [
        str(app["index"]) for group in capture_tab_groups() for app in group["apps"]
    ] == [
        "0",
        "1",
        "2",
        "3",
        "4",
        "5",
        "6",
        "7",
        "8",
        "9",
        "10",
    ]


def test_carousel_status_starts_at_one_of_eleven():
    assert ">1 / 11<" in (_text(MODULES) + _text(GALLERY))


def test_stats_and_live_paper_have_distinct_sample_and_mnist_captures():
    assert "7 of 11: Stats" in (_text(MODULES) + _text(GALLERY))
    assert "10 of 11: Live Paper" in (_text(MODULES) + _text(GALLERY))
    assert "not research findings" in (_text(MODULES) + _text(GALLERY))


def test_stats_slide_uses_dedicated_renditions():
    assert all(
        (ASSETS / name).exists()
        for name in (
            "stats-20261102-768.webp",
            "stats-20261102-1200.webp",
            "stats-20261102-1200.jpg",
        )
    )


def test_historical_stats_capture_hash_remains_in_provenance():
    assert "4b8a0c4a348100999d834ec962b6e23c5eacc8ad3f09d4db9eefd146616a4678" in _text(
        ASSETS / "PROVENANCE.md"
    )
