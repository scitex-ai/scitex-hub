#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for apps/workspace/docs_app/views.py — the Overview landing page.

Site audit (card hub-site-audit-2-defect-backlog-20260914): /apps/docs/ opened
on "MCP Tools (Local)", a power-user page. A first-time visitor must land on an
overview instead.

The .mo catalogs are gitignored, so the Japanese render test compiles them with
the project's babel-based script first (same approach as
tests/config/test_i18n_settings_services_landing.py).
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest
from django.template.loader import render_to_string
from django.test import Client
from django.utils import translation

from apps.workspace.docs_app._context_builders import build_page_context
from apps.workspace.docs_app.views import DOCS_PAGES, build_docs_context

PROJECT_ROOT = Path(__file__).resolve().parents[3]
OVERVIEW_TEMPLATE = "docs_app/docs_overview.html"
JAPANESE_HEADING = "SciTeX Hub へようこそ"


@pytest.fixture
def compiled_catalogs():
    """Compile locale/**/*.po -> .mo so the ja render reads the real catalog."""
    script = PROJECT_ROOT / "scripts" / "i18n" / "compile_catalogs.py"
    result = subprocess.run(
        [sys.executable, str(script)], cwd=PROJECT_ROOT, capture_output=True, text=True
    )
    assert result.returncode == 0, result.stdout + result.stderr
    translation.trans_real._translations.clear()
    yield


def test_first_docs_page_is_overview():
    # Arrange
    first_page = DOCS_PAGES[0]
    # Act
    slug = first_page["slug"]
    # Assert
    assert slug == "overview"


def test_docs_index_context_defaults_to_overview():
    # Arrange
    request = None
    # Act
    context = build_docs_context(request)
    # Assert
    assert context["active_doc"] == "overview"


@pytest.mark.django_db
def test_overview_content_returns_200():
    # Arrange
    client = Client()
    # Act
    response = client.get("/apps/docs/content/overview/")
    # Assert
    assert response.status_code == 200


def test_overview_renders_japanese_heading_under_ja(compiled_catalogs):
    # Arrange
    context = build_page_context("overview")
    # Act
    with translation.override("ja"):
        html = render_to_string(OVERVIEW_TEMPLATE, context)
    # Assert
    assert JAPANESE_HEADING in html
