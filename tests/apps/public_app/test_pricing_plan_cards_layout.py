#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""/pricing/ plan cards lay out and read correctly (regression from #811).

Live audit 2026-09-14 (compute-03 dev):
- headings and subtitles ran together ("SciTeX CloudHosted at scitex.ai",
  "$19/moFor eligible…") because the only ``.plan-sub`` rule lived in
  landing/11-pricing.css, which /pricing/ does not load;
- the 3 SSOT v1.0 tier cards were squeezed into the left of a
  ``repeat(5, 1fr)`` grid (pricing-alpha.css);
- the JA FAQ closed a full-width "（詳しくは" with an ASCII ")." that lived
  as a literal in the template, outside any msgid.
"""

import re
import subprocess
import sys
from pathlib import Path

import pytest
from django.urls import reverse
from django.utils import translation

PROJECT_ROOT = Path(__file__).resolve().parents[3]
PUBLIC_APP = PROJECT_ROOT / "apps" / "infra" / "public_app"
PRICING_TEMPLATE = PUBLIC_APP / "templates" / "public_app" / "pages" / "pricing.html"
STATIC_ROOT = PUBLIC_APP / "static"


def _loaded_stylesheets_css() -> str:
    """Comment-stripped text of every public_app stylesheet pricing.html links."""
    template = PRICING_TEMPLATE.read_text(encoding="utf-8")
    paths = re.findall(r"""\{%\s*static\s+'(public_app/css/[^']+\.css)'\s*%\}""", template)
    css = "\n".join(
        (STATIC_ROOT / p).read_text(encoding="utf-8") for p in paths if (STATIC_ROOT / p).is_file()
    )
    return re.sub(r"/\*.*?\*/", "", css, flags=re.S)


def _rule_bodies(css: str, selector_pattern: str) -> list[str]:
    return re.findall(r"(?:^|[}\s,])" + selector_pattern + r"\s*\{([^{}]*)\}", css)


def _visible(html: str) -> str:
    html = re.sub(r"<!--.*?-->|<(script|style)\b.*?</\1>", " ", html, flags=re.S | re.I)
    html = re.sub(r"<[^>]+>", " ", html)
    return re.sub(r"\s+", " ", html)


@pytest.fixture(scope="module")
def compiled_catalogs():
    """Compile locale/**/*.po -> .mo so the JA assertion reads a real catalog."""
    script = PROJECT_ROOT / "scripts" / "i18n" / "compile_catalogs.py"
    result = subprocess.run(
        [sys.executable, str(script)], cwd=PROJECT_ROOT, capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr
    translation.trans_real._translations.clear()
    yield


def test_pricing_page_loads_a_stylesheet_that_blocks_the_plan_subtitle():
    # Arrange
    css = _loaded_stylesheets_css()
    # Act
    bodies = _rule_bodies(css, r"(?:\.pricing-tier-card\s+)?\.plan-sub")
    # Assert
    assert any(re.search(r"display\s*:\s*block", body) for body in bodies)


def test_pricing_page_loads_a_stylesheet_that_styles_the_price_details_list():
    # Arrange
    css = _loaded_stylesheets_css()
    # Act
    dd_bodies = _rule_bodies(css, r"\.pricing-tier-prices\s+dd")
    # Assert
    assert dd_bodies != []


def test_pricing_cards_wrapper_grid_is_not_a_five_column_template():
    # Arrange
    css = _loaded_stylesheets_css()
    # Act
    columns = [
        m.group(1).strip()
        for body in _rule_bodies(css, r"\.pricing-cards-wrapper")
        for m in re.finditer(r"grid-template-columns\s*:\s*([^;]+);", body)
    ]
    # Assert
    assert (columns != [], [c for c in columns if re.search(r"repeat\(\s*5\b", c)]) == (True, [])


@pytest.mark.django_db
def test_japanese_pricing_faq_closes_the_full_width_bracket_it_opens(client, compiled_catalogs):
    # Arrange
    cookie = {"HTTP_COOKIE": "django_language=ja"}
    # Act
    visible = _visible(client.get(reverse("public_app:pricing"), **cookie).content.decode("utf-8"))
    closer = re.search(r"（詳しくは[^（）()]*([)）])", visible)
    # Assert
    assert (closer.group(1) if closer else None) == "）"
