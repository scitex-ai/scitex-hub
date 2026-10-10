#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Regression gate for the writer ``core:index`` NoReverseMatch (card
hub-writer-core-index-20261010).

``/apps/writer/`` 500'd for an authenticated user with no project: the
``needs_project_creation`` branch of ``writer_app/index.html`` (and the
``writer_partial.html`` / ``figrecipe_partial.html`` equivalents) reversed
``{% url 'core:index' %}``, but no ``core`` namespace is registered anywhere
(no ``core`` include in ``config/urls.py``, no ``app_name = "core"``). The
buttons now point at the canonical project-creation route
``project_create`` (``/new/``).
"""

from pathlib import Path

import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import NoReverseMatch, reverse

User = get_user_model()

REPO_ROOT = Path(__file__).resolve().parents[2]
NO_PROJECT_TEMPLATES = [
    "apps/workspace/writer_app/templates/writer_app/index.html",
    "apps/workspace/writer_app/templates/writer_app/writer_partial.html",
    "apps/workspace/figrecipe_app/templates/figrecipe_app/figrecipe_partial.html",
]


def test_project_create_route_exists():
    # Arrange / Act
    url = reverse("project_create")

    # Assert — the retarget of the Create-a-Project buttons resolves
    assert url == "/new/"


def test_no_core_namespace_is_referenced_by_no_project_templates():
    # Arrange — source-text gate: runs without a database
    missing = [
        rel
        for rel in NO_PROJECT_TEMPLATES
        if "core:index" in (REPO_ROOT / rel).read_text()
    ]

    # Assert — 'core' is not a registered namespace, so no template may
    # reverse it (a stale ref 500s the whole page at render time)
    assert missing == []


def test_core_namespace_stays_unregistered():
    # Arrange / Act — documents the "retarget, don't register" decision:
    # there is no core app to mount, so this must keep failing
    with pytest.raises(NoReverseMatch):
        reverse("core:index")


@pytest.mark.django_db
class TestWriterIndexWithoutProject:
    """Authed user with no project renders /apps/writer/ (no 500)."""

    def test_writer_index_renders_create_project_prompt(self):
        # Arrange — a user that owns zero projects
        user = User.objects.create_user("writer-no-project-user")
        http = Client()
        http.force_login(user)

        # Act — the test client re-raises view exceptions, so a stale
        # {% url %} fails here with NoReverseMatch instead of a bare 500
        response = http.get("/apps/writer/")

        # Assert
        assert response.status_code == 200
        assert response.context["needs_project_creation"] is True
        assert b"No Project Found" in response.content
        assert reverse("project_create").encode() in response.content
