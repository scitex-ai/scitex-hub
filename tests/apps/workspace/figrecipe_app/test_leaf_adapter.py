#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""FigRecipe leaf-move pilot adapter: leaf-first, hub-parity fallback.

Card hub-figrecipe-leaf-move-20261009. ``build_figrecipe_context`` prefers
the leaf-owned ``figrecipe._django.workspace.build_workspace_context``
(>=0.36) and falls back to the hub-local keys when the installed leaf
predates the surface or the SDK project authority is unavailable. These
tests pin both halves: the fallback is byte-identical to the pre-move hub
context, and a serving leaf wins without losing the hub shell keys.
"""

from __future__ import annotations

import pytest
from django.test import RequestFactory

import apps.workspace.figrecipe_app.views as views

_HUB_KEYS_NO_PROJECT = {
    "app_slug": "figrecipe",
    "app_label": "FigRecipe",
    "app_mount_css": "figrecipe_app/css/figrecipe-mount.css",
    "bridge_entry_name": "figrecipe_app/figrecipe-bridge-init",
    "current_project": None,
    "needs_project_creation": True,
}


@pytest.fixture
def freq():
    return RequestFactory().get("/apps/figrecipe/")


def test_fallback_parity_on_stale_leaf(freq, monkeypatch):
    """No leaf surface (e.g. installed 0.35.0) -> exact pre-move hub keys."""
    monkeypatch.setattr(views, "_leaf_build_context", lambda *a, **k: None)
    assert views.build_figrecipe_context(freq, None) == _HUB_KEYS_NO_PROJECT


def test_fallback_keeps_project_and_drops_flag(freq, monkeypatch):
    monkeypatch.setattr(views, "_leaf_build_context", lambda *a, **k: None)
    sentinel = object()
    ctx = views.build_figrecipe_context(freq, sentinel)
    assert ctx["current_project"] is sentinel
    assert "needs_project_creation" not in ctx
    assert ctx["app_mount_css"] == "figrecipe_app/css/figrecipe-mount.css"
    assert ctx["bridge_entry_name"] == "figrecipe_app/figrecipe-bridge-init"


def test_leaf_preferred_without_losing_hub_shell_keys(freq, monkeypatch):
    """A serving leaf wins; hub scoping + shell keys survive the merge."""
    sentinel = object()
    monkeypatch.setattr(
        views,
        "_leaf_build_context",
        lambda *a, **k: {
            "app_slug": "figrecipe",
            "app_label": "FigRecipe",
            "app_version": "0.36.0",
            "hosted": True,
            "recipe": "demo.yaml",
        },
    )
    ctx = views.build_figrecipe_context(freq, sentinel)
    assert ctx["app_version"] == "0.36.0"
    assert ctx["hosted"] is True
    assert ctx["recipe"] == "demo.yaml"
    assert ctx["app_mount_css"] == "figrecipe_app/css/figrecipe-mount.css"
    assert ctx["bridge_entry_name"] == "figrecipe_app/figrecipe-bridge-init"
    assert ctx["current_project"] is sentinel
    assert "needs_project_creation" not in ctx


def test_leaf_failure_never_raises(freq, monkeypatch):
    """Any leaf blow-up degrades to hub parity instead of 500ing the page."""

    def _boom(*a, **k):
        raise RuntimeError("SDK provider exploded")

    monkeypatch.setattr(views, "import_string", _boom)
    assert views._leaf_build_context(freq, None) is None
    assert views.build_figrecipe_context(freq, None) == _HUB_KEYS_NO_PROJECT


def test_real_leaf_attempt_falls_back_without_provider(freq):
    """End to end in this env: no SDK provider -> hub parity, no raise.

    Holds on BOTH sides of the skew: a stale leaf (<0.36, no workspace
    module) fails the import, a current leaf fails project authority.
    """
    assert views.build_figrecipe_context(freq, None) == _HUB_KEYS_NO_PROJECT


def test_figure_editor_shares_single_builder(freq, monkeypatch):
    """Page and partial build from one builder (dedupe), hub shell intact."""
    from django.contrib.auth.models import AnonymousUser

    freq.user = AnonymousUser()
    resp = views.figure_editor(freq)
    assert resp.status_code == 302
    assert resp.headers["Location"] == "/auth/signup/"

    seen = {}

    def _spy(request, current_project=None):
        seen["project"] = current_project
        return dict(_HUB_KEYS_NO_PROJECT)

    monkeypatch.setattr(views, "build_figrecipe_context", _spy)
    monkeypatch.setattr(views, "project_for_scope_app", lambda request: None)

    captured = {}
    monkeypatch.setattr(
        views,
        "render",
        lambda request, template, context: captured.setdefault(
            "all", (template, context)
        ),
    )

    class _User:
        is_authenticated = True

    freq.user = _User()
    views.figure_editor(freq)
    template, context = captured["all"]
    # Hub shell template unchanged by the pilot (leaf template flip pending).
    assert template == "figrecipe_app/editor.html"
    # Single builder fed the page; page-only keys layered on top.
    assert seen["project"] is None
    for key in (
        "app_slug",
        "app_label",
        "app_mount_css",
        "bridge_entry_name",
        "current_project",
        "needs_project_creation",
        "module_name",
        "is_workspace_page",
    ):
        assert key in context, key
