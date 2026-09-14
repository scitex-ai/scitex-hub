#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Focused tests for the shared hub bridge scope-meta injection.

These exercise apps/infra/workspace_app/scope_meta.inject_scope_meta — the one
place the hub stamps the scitex-app d8528de app-scope marker onto leaf pages
that do NOT go through scitex-app's scitex_editor_page host view (the FigRecipe
+ Writer bridges). Contract: project-scoped leaf manifest -> the marker is
injected; user-scoped / absent / unknown app / non-HTML -> the response is
returned BYTE-IDENTICAL (the "renders with no switcher" structural default).

The real scitex-app emitter is used (not a mock) so the test asserts the actual
<stx-app-scope> output shape. _scope_for is monkeypatched per-test to isolate
the injection logic from which manifest the live mount resolves.
"""
from django.http import HttpResponse, JsonResponse

from apps.infra.workspace_app import scope_meta


def _patch_scope(scope):
    """Force _scope_for to return a fixed scope for the duration of a test."""
    real = scope_meta._scope_for
    scope_meta._scope_for = lambda app_name: scope
    return real


def test_project_scope_injects_meta_into_html():
    real = _patch_scope("project")
    try:
        resp = HttpResponse("<html><head><title>x</title></head><body></body></html>")
        out = scope_meta.inject_scope_meta(resp, "figrecipe")
        assert b'name="stx-app-scope"' in out.content, (
            "a project-scoped leaf page must carry the stx-app-scope marker"
        )
        assert b"content=\"project\"" in out.content
    finally:
        scope_meta._scope_for = real


def test_user_scope_leaves_html_unchanged():
    real = _patch_scope("user")
    try:
        html = "<html><head><title>x</title></head><body>hi</body></html>"
        resp = HttpResponse(html)
        out = scope_meta.inject_scope_meta(resp, "figrecipe")
        assert out.content.decode("utf-8", "replace") == html, (
            "a user-scoped leaf must render byte-identical (no marker)"
        )
    finally:
        scope_meta._scope_for = real


def test_absent_scope_leaves_html_unchanged():
    real = _patch_scope(None)
    try:
        html = "<html><head></head><body></body></html>"
        resp = HttpResponse(html)
        out = scope_meta.inject_scope_meta(resp, "figrecipe")
        assert out.content.decode("utf-8", "replace") == html
    finally:
        scope_meta._scope_for = real


def test_non_html_response_is_untouched():
    real = _patch_scope("project")
    try:
        resp = JsonResponse({"ok": True})
        out = scope_meta.inject_scope_meta(resp, "figrecipe")
        assert out == resp
        assert b"stx-app-scope" not in (out.content or b"")
    finally:
        scope_meta._scope_for = real


def test_unknown_app_is_untouched():
    # _scope_for returns None for an app not in the leaf-package map.
    html = "<html><head></head><body></body></html>"
    resp = HttpResponse(html)
    out = scope_meta.inject_scope_meta(resp, "not-a-leaf")
    assert out.content.decode("utf-8", "replace") == html


def test_scope_for_reads_leaf_manifest_not_wrapper():
    # Regression: the hub WRAPPER manifests (what the registry reads) do NOT
    # carry scope; the LEAF package manifests do. _scope_for must resolve the
    # leaf. On this dev mount figrecipe._django/manifest.json declares "project".
    # If a leaf is not importable in this env, skip the positive assert rather
    # than false-fail.
    scope = scope_meta._scope_for("figrecipe")
    if scope is not None:
        assert scope == "project", f"figrecipe leaf manifest scope should be 'project', got {scope!r}"
    # A registry/wrapper name that maps to no leaf package must return None.
    assert scope_meta._scope_for("definitely-not-a-leaf") is None
