#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for the mobile Docs two-dropdown cascade nav.

Spec: at 390px the docs sidebar is replaced by two cascading labeled
selects ONLY (level 1 = documentation section, level 2 = page within
it), reusing the DOCS_PAGES source. No drawer markup; content floor
~330px+ preserved; no char-by-char token wrap.
"""

from __future__ import annotations

import re
from pathlib import Path

from django.template.loader import render_to_string

from apps.workspace.docs_app.views import (
    DOCS_PAGES,
    DOCS_SECTIONS,
    build_docs_context,
    get_docs_sections,
)

PROJECT_ROOT = Path(__file__).resolve().parents[3]
CSS_PATH = (
    PROJECT_ROOT
    / "apps"
    / "workspace"
    / "docs_app"
    / "static"
    / "docs_app"
    / "css"
    / "docs-workspace.css"
)


def test_every_page_has_a_known_section():
    # Arrange
    known = {key for key, _label in DOCS_SECTIONS}
    # Act + Assert
    for page in DOCS_PAGES:
        assert page.get("section") in known, f"page {page['slug']} has no section"


def test_sections_cover_all_pages_in_taxonomy_order():
    # Arrange
    order = [key for key, _label in DOCS_SECTIONS]
    # Act
    sections = get_docs_sections()
    # Assert
    assert [s["key"] for s in sections] == [
        k for k in order if any(p.get("section") == k for p in DOCS_PAGES)
    ]
    assert all(s["pages"] for s in sections)
    flat = [p["slug"] for s in sections for p in s["pages"]]
    assert sorted(flat) == sorted(p["slug"] for p in DOCS_PAGES)


def test_context_exposes_sections_and_active_section():
    # Act
    context = build_docs_context(None)
    # Assert
    assert context["active_doc"] == "overview"
    assert context["active_section"] == "getting-started"
    assert context["docs_sections"][0]["key"] == "getting-started"
    assert context["docs_sections"][0]["pages"][0]["slug"] == "overview"


def test_partial_renders_two_labeled_selects_and_no_drawer():
    # Arrange — render the real partial with the real context (docs pages
    # are registry-driven and need no DB, so this exercises the exact
    # markup the browser receives at /apps/docs/).
    # Act
    html = render_to_string("docs_app/docs_partial.html", build_docs_context(None))
    # Assert
    assert 'id="docs-mobile-section"' in html
    assert 'id="docs-mobile-page"' in html
    assert '<label for="docs-mobile-section"' in html
    assert '<label for="docs-mobile-page"' in html
    # Exactly two cascading selects — no drawer markup anywhere
    assert len(re.findall(r"<select", html)) == 2
    assert "drawer" not in html.lower()
    # Level 2 carries every page exactly once, grouped by section
    match = re.search(r'<select id="docs-mobile-page".*?</select>', html, re.DOTALL)
    assert match is not None
    page_select = match.group(0)
    options = re.findall(r'<option value="([^"]+)"', page_select)
    assert sorted(options) == sorted(p["slug"] for p in DOCS_PAGES)
    assert len(re.findall(r"<optgroup", page_select)) == len(
        re.findall(r"<optgroup", html)
    )


def test_mobile_css_hides_sidebar_keeps_content_floor():
    # Arrange
    css = CSS_PATH.read_text()
    mobile = css[css.index("@media (max-width: 767px)") :]
    # Act + Assert
    assert ".docs-sidebar" in mobile and "display: none" in mobile
    assert ".docs-mobile-nav" in mobile
    assert "min-height: 330px" in mobile
    # No char-by-char token shredding anywhere in the docs CSS
    assert "break-all" not in css
