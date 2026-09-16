#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: tests/apps/apps_app/test_floating_dock_chat.py
"""Floating dock chat: the dock's Chat opens a small panel, /chat/?embed=1 has no chrome,
and the chat's system prompt names the page under the panel."""

from pathlib import Path

from django.contrib.auth.models import AnonymousUser
from django.template.loader import render_to_string
from django.test import RequestFactory

from apps.infra.llm_app.page_context import page_context_prompt
from apps.infra.workspace_app.site_dock import DockItem, should_render_dock

_REPO_ROOT = Path(__file__).resolve().parents[3]


def test_dock_chat_item_carries_the_float_toggle_hook():
    # Arrange
    item = DockItem(key="chat", label="Chat", icon="fas fa-comment", url="/chat/")
    # Act
    html = render_to_string(
        "global_base_partials/site_dock.html",
        {"site_dock_items": [item], "site_dock_capacity": 5},
    )
    # Assert
    assert "data-dock-chat-toggle" in html


def test_embed_request_renders_no_dock():
    # Arrange
    request = RequestFactory().get("/chat/", {"embed": "1"})
    # Act
    renders = should_render_dock(request)
    # Assert
    assert renders is False


def test_any_iframe_document_renders_no_nested_dock():
    # Arrange
    request = RequestFactory().get(
        "/accounts/settings/ai-providers/", HTTP_SEC_FETCH_DEST="iframe"
    )
    request.user = type("User", (), {"is_authenticated": True})()
    # Act
    renders = should_render_dock(request)
    # Assert
    assert renders is False


def test_embed_flag_drops_site_header_and_footer():
    # Arrange
    guard = "{% if request.GET.embed != '1' %}{% include 'global_base_partials/global_footer.html' %}"
    # Act
    base = (_REPO_ROOT / "templates/global_base.html").read_text("utf-8")
    # Assert
    assert guard in base


def test_embed_follows_the_parent_page_light_theme():
    # Arrange
    request = RequestFactory().get("/chat/", {"embed": "1", "theme": "light"})
    request.user = AnonymousUser()
    request.session = {}
    # Act
    html = render_to_string("global_base.html", request=request)
    # Assert
    assert 'data-theme="light" data-color-mode="light">' in html


def test_system_prompt_names_the_page_under_the_float():
    # Arrange
    context = {"ctx_path": "/apps/writer/", "ctx_title": "Writer"}
    # Act
    prompt = page_context_prompt(context)
    # Assert
    assert "The user is on Writer (/apps/writer/), app writer" in prompt
