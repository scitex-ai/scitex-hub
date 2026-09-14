#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for apps/workspace/docs_app/views.py — the Overview landing page.

Site audit (card hub-site-audit-2-defect-backlog-20260914): /apps/docs/ opened
on "MCP Tools (Local)", a power-user page. A first-time visitor must land on an
overview instead.

The .mo catalogs are gitignored, so the Japanese render test compiles them with
the project's babel-based script first (the compiled_catalogs fixture in
conftest.py).
"""

from __future__ import annotations

import pytest
from django.template.loader import render_to_string
from django.test import Client
from django.utils import translation

from apps.workspace.docs_app._context_builders import build_page_context
from apps.workspace.docs_app.views import DOCS_PAGES, build_docs_context

OVERVIEW_TEMPLATE = "docs_app/docs_overview.html"
JAPANESE_HEADING = "SciTeX Hub へようこそ"


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
