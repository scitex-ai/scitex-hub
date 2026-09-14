#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The How-to guide pages: registered after Overview, rendered, translated."""

import pytest
from django.template.loader import render_to_string
from django.test import Client
from django.utils import translation

from apps.workspace.docs_app._context_builders import build_page_context

HOWTO_SLUGS = [
    "howto-projects",
    "howto-scholar",
    "howto-writer",
    "howto-figrecipe",
    "howto-chat",
    "howto-cards-agents",
]
PROJECTS_TEMPLATE = "docs_app/howto/howto_projects.html"
PROJECTS_JAPANESE_TITLE = "プロジェクトの使い方"


@pytest.mark.django_db
@pytest.mark.parametrize("slug", HOWTO_SLUGS)
def test_howto_page_returns_200(slug):
    # Arrange
    client = Client()
    # Act
    response = client.get(f"/apps/docs/content/{slug}/")
    # Assert
    assert response.status_code == 200


def test_howto_projects_renders_japanese_title_under_ja(compiled_catalogs):
    # Arrange
    context = build_page_context("howto-projects")
    # Act
    with translation.override("ja"):
        html = render_to_string(PROJECTS_TEMPLATE, context)
    # Assert
    assert PROJECTS_JAPANESE_TITLE in html
