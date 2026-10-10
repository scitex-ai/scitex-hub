#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""FigRecipe leaf flip: hub page serves the leaf-owned workspace surface.

Card hub-figrecipe-leaf-move-20261009 (flip). ``build_figrecipe_context``
calls the leaf ``figrecipe._django.workspace.build_workspace_context``
(>=0.36) and stamps only what the host owns: the guarded API mount
(``stx_mount``), the SDK shell mount marker, and the hub project object.
The pilot's hub-local fallback keys (``app_mount_css``,
``bridge_entry_name``) and hub shell keys are retired — the leaf bundle
serves the frontend and the leaf template extends the SDK shell.

Fail loud: a missing/failing leaf raises instead of rendering stale hub
keys. The guarded API base is derived from the hub URLconf
(``figrecipe_app:figrecipe_editor``), never from ``request.path``, so the
workspace content endpoint (``/apps/workspace/content/figrecipe/``)
stamps the same mount the page does.

Mount dedupe: the bespoke ``apps/figrecipe/`` include stays the single
serving mount (jail guard + auth gate); the generic plugin mount skips the
leaf's route via ``_route_taken`` (pinned below), so the leaf urlconf is
never double-mounted raw.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from django.test import RequestFactory

import apps.workspace.figrecipe_app.views as views

REPO_ROOT = Path(__file__).resolve().parents[4]

_LEAF_CONTEXT = {
    "app_slug": "figrecipe",
    "app_label": "FigRecipe",
    "app_version": "0.36.0",
    "hosted": True,
    "project_id": "proj-1",
    "project_name": "demo",
    "working_dir": "/data/users/demo/demo",
    "working_dir_name": "demo",
    "recipe": "",
    "stx_mount": None,
}

_GUARDED_MOUNT = "/apps/figrecipe/figrecipe"


@pytest.fixture
def freq():
    return RequestFactory().get("/apps/figrecipe/")


@pytest.fixture
def leaf_serving(monkeypatch):
    """Stub the leaf builder + guarded-mount reverse (no leaf/SDK/DB needed)."""
    sentinel = object()

    def _builder(request, current_project=None):
        assert current_project is sentinel
        return dict(_LEAF_CONTEXT)

    monkeypatch.setattr(
        views, "import_string", lambda path: _builder if path == views._LEAF_BUILDER_PATH else None
    )
    monkeypatch.setattr(
        views, "reverse", lambda name: f"{_GUARDED_MOUNT}/" if name == "figrecipe_app:figrecipe_editor" else None
    )
    return sentinel


def test_leaf_context_wins_and_hub_stamps_guarded_mount(freq, leaf_serving):
    # Arrange — leaf serving, hub project in scope (arranged by the fixture)
    # Act
    ctx = views.build_figrecipe_context(freq, leaf_serving)
    # Assert — leaf keys survive untouched
    for key, value in _LEAF_CONTEXT.items():
        if key == "stx_mount":
            continue
        assert ctx[key] == value, key
    # Assert — host stamps the guarded API base (leaf test pins this legacy
    # mount), the SDK shell marker, and the hub project object
    assert ctx["stx_mount"] == _GUARDED_MOUNT
    assert ctx["stx_mount_prefix"] == "/apps/figrecipe"
    assert ctx["stx_mount_declared"] is True
    assert ctx["current_project"] is leaf_serving
    assert "needs_project_creation" not in ctx
    # Assert — retired hub-local keys are gone where the leaf serves
    for key in (
        "app_mount_css",
        "bridge_entry_name",
        "module_name",
        "module_icon",
        "is_workspace_page",
        "figrecipe_embedded",
    ):
        assert key not in ctx, key


def test_no_project_sets_flag_and_keeps_leaf_surface(freq, leaf_serving, monkeypatch):
    # Arrange — leaf serving but no project in scope
    monkeypatch.setattr(
        views, "import_string", lambda path: (lambda request, current_project=None: dict(_LEAF_CONTEXT))
    )
    # Act
    ctx = views.build_figrecipe_context(freq, None)
    # Assert
    assert ctx["needs_project_creation"] is True
    assert ctx["current_project"] is None
    assert ctx["stx_mount"] == _GUARDED_MOUNT


def test_stx_mount_derives_from_guarded_route_not_request_path(freq, leaf_serving, monkeypatch):
    # Arrange — content-endpoint path must not leak into the SPA's API base
    seen = {}
    content_request = RequestFactory().get("/apps/workspace/content/figrecipe/")

    def _reverse(name):
        seen["name"] = name
        return f"{_GUARDED_MOUNT}/"

    monkeypatch.setattr(views, "reverse", _reverse)
    # Act
    ctx = views.build_figrecipe_context(content_request, leaf_serving)
    # Assert
    assert seen["name"] == "figrecipe_app:figrecipe_editor"
    assert ctx["stx_mount"] == _GUARDED_MOUNT
    assert not ctx["stx_mount"].endswith("/")


def test_missing_leaf_raises_loud_instead_of_silent_parity(freq, monkeypatch):
    # Arrange — installed leaf predates the workspace surface (no fallback anymore)
    def _no_leaf(path):
        raise ImportError("No module named 'figrecipe._django.workspace'")

    monkeypatch.setattr(views, "import_string", _no_leaf)
    # Act / Assert — fail loud, never a wrong-answer-that-looks-right page
    with pytest.raises(ImportError):
        views.build_figrecipe_context(freq, None)


def test_leaf_authority_failure_propagates(freq, monkeypatch):
    # Arrange — leaf present but SDK project authority unavailable
    def _boom(request, current_project=None):
        raise RuntimeError("SDK provider exploded")

    monkeypatch.setattr(views, "import_string", lambda path: _boom)
    # Act / Assert
    with pytest.raises(RuntimeError):
        views.build_figrecipe_context(freq, None)


def test_figure_editor_shares_single_builder_and_renders_leaf(freq, leaf_serving, monkeypatch):
    # Arrange — anonymous still goes to signup first
    from django.contrib.auth.models import AnonymousUser

    freq.user = AnonymousUser()
    resp = views.figure_editor(freq)
    assert resp.status_code == 302
    assert resp.headers["Location"] == "/auth/signup/"

    # Arrange — authed page renders the leaf template from the one builder
    seen = {}

    def _spy(request, current_project=None):
        seen["project"] = current_project
        return {"stx_mount": _GUARDED_MOUNT, "current_project": current_project}

    monkeypatch.setattr(views, "build_figrecipe_context", _spy)
    monkeypatch.setattr(views, "project_for_scope_app", lambda request: None)

    captured = {}
    monkeypatch.setattr(
        views,
        "render",
        lambda request, template, context: captured.setdefault("all", (template, context)),
    )

    class _User:
        is_authenticated = True

    freq.user = _User()
    # Act
    views.figure_editor(freq)
    # Assert — leaf template, hub scoping intact, no hub shell keys
    template, context = captured["all"]
    assert template == "figrecipe/workspace.html"
    assert seen["project"] is None
    assert context["stx_mount"] == _GUARDED_MOUNT
    assert context["needs_project_creation"] is True
    for key in ("app_mount_css", "bridge_entry_name", "module_name", "is_workspace_page"):
        assert key not in context, key


def test_bespoke_mount_blocks_plugin_remount():
    # Arrange — the bespoke apps/figrecipe/ include already serves the leaf route
    from django.urls import path

    from apps.workspace.apps_app.services.plugin_apps import _route_taken

    def _view(request):
        return None

    existing = [path("apps/figrecipe/", _view)]
    # Act / Assert — generic plugin mount yields no duplicate raw mount
    assert _route_taken("apps/figrecipe/", existing) is True
    assert _route_taken("apps/hello-world/", existing) is False


def test_manifest_points_at_leaf_surface():
    # Arrange — source-text gate: runs without a database
    manifest = json.loads(
        (REPO_ROOT / "apps/workspace/figrecipe_app/manifest.json").read_text()
    )
    # Act / Assert — workspace shell renders the leaf partial with the hub
    # builder (hub stamps stx_mount + project around the leaf context)
    assert manifest["partial_template"] == "figrecipe/workspace_partial.html"
    assert (
        manifest["context_builder"]
        == "apps.workspace.figrecipe_app.views.build_figrecipe_context"
    )


def test_hub_templates_are_retired():
    # Arrange — source-text gate: the flip deletes both hub-owned templates
    templates_dir = REPO_ROOT / "apps/workspace/figrecipe_app/templates"
    # Act / Assert
    assert not (templates_dir / "figrecipe_app/editor.html").exists()
    assert not (templates_dir / "figrecipe_app/figrecipe_partial.html").exists()
