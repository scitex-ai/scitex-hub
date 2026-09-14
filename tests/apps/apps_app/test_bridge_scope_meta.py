#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for the shared hub bridge scope-meta injection (#801).

Covers the two independent-review findings on the first cut plus the endpoint
wiring:
  * IDEMPOTENCY — a page that already carries stx-app-scope is not duplicated
    (scitex-app's _inject_scope_meta always inserts, so the hub guards first).
  * NO PER-REQUEST FILE I/O — the resolved scope is cached at process level,
    invalidated deterministically on the installed leaf package identity.
  * MANIFEST RESOLUTION — _scope_for reads the LEAF package's _django
    manifest (not the hub wrapper manifest) — deterministic fixtures for both
    leaves (figrecipe + writer), non-skipping.
  * ENDPOINT INTEGRATION — authenticated FigRecipe editor + Writer
    editor/viewer return EXACTLY ONE marker; the API dispatch path is
    unchanged (no marker, JSON).

Pure resolver/idempotency/cache tests use unittest.mock (no DB). Endpoint
integration uses a Django TestCase (a real logged-in user) and patches the
bridge's downstream view to return representative leaf HTML, isolating the
hub's marker wiring from the leaf's own rendering/project requirements.
"""
from unittest import mock

from django.contrib.auth.models import User
from django.http import HttpResponse, JsonResponse
from django.test import RequestFactory, TestCase

from apps.infra.workspace_app import scope_meta

HTML = "<html><head><title>Leaf</title></head><body><div id=root></div></body></html>"
MARKER_COUNT = b'stx-app-scope'


# ---------------------------------------------------------------------------
# Pure logic: idempotency (the #801 regression the review required)
# ---------------------------------------------------------------------------
def test_project_scope_injects_exactly_one_marker():
    with mock.patch.object(scope_meta, "_scope_for", return_value="project"):
        resp = HttpResponse(HTML)
        out = scope_meta.inject_scope_meta(resp, "figrecipe")
    assert out.content.count(MARKER_COUNT) == 1, "a project page must carry exactly one marker"


def test_leaf_that_already_stamps_is_not_duplicated():
    """If a leaf later emits stx-app-scope itself, the hub must NOT add a second."""
    stamped = (
        "<html><head><meta name=\"stx-app-scope\" content=\"project\">"
        "<title>Leaf</title></head><body></body></html>"
    )
    with mock.patch.object(scope_meta, "_scope_for", return_value="project"):
        out = scope_meta.inject_scope_meta(HttpResponse(stamped), "figrecipe")
    assert out.content.count(MARKER_COUNT) == 1, "pre-stamped page must not gain a second marker"


def test_user_scope_leaves_html_unchanged():
    with mock.patch.object(scope_meta, "_scope_for", return_value="user"):
        out = scope_meta.inject_scope_meta(HttpResponse(HTML), "figrecipe")
    assert out.content.decode() == HTML and out.content.count(MARKER_COUNT) == 0


def test_absent_or_unknown_scope_is_unchanged():
    with mock.patch.object(scope_meta, "_scope_for", return_value=None):
        assert scope_meta.inject_scope_meta(HttpResponse(HTML), "figrecipe").content.decode() == HTML
    assert scope_meta.inject_scope_meta(HttpResponse(HTML), "not-a-leaf").content.decode() == HTML


def test_non_html_response_is_untouched():
    with mock.patch.object(scope_meta, "_scope_for", return_value="project"):
        out = scope_meta.inject_scope_meta(JsonResponse({"ok": True}), "figrecipe")
    assert out is not None and b"stx-app-scope" not in out.content


# ---------------------------------------------------------------------------
# Manifest resolution (deterministic fixtures, both leaves, non-skipping) + cache
# ---------------------------------------------------------------------------
def _fixture_manifest(tmp_path, scope):
    import json
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps({"name": "x", "scope": scope}) if scope is not None else '{"name":"x"}')
    return tmp_path


def test_scope_for_reads_leaf_manifest_project(tmp_path):
    _fixture_manifest(tmp_path, "project")
    with mock.patch.object(scope_meta, "_leaf_spec_identity", return_value=str(tmp_path)):
        scope_meta.clear_scope_cache()
        assert scope_meta._scope_for("figrecipe") == "project"
        assert scope_meta._scope_for("writer") == "project"


def test_scope_for_absent_when_manifest_has_no_scope(tmp_path):
    _fixture_manifest(tmp_path, None)
    with mock.patch.object(scope_meta, "_leaf_spec_identity", return_value=str(tmp_path)):
        scope_meta.clear_scope_cache()
        assert scope_meta._scope_for("figrecipe") is None


def test_scope_for_none_when_leaf_not_importable():
    with mock.patch.object(scope_meta, "_leaf_spec_identity", return_value=None):
        scope_meta.clear_scope_cache()
        assert scope_meta._scope_for("figrecipe") is None


def test_scope_cache_holds_until_identity_changes(tmp_path):
    _fixture_manifest(tmp_path, "project")
    with mock.patch.object(scope_meta, "_leaf_spec_identity", return_value=str(tmp_path)):
        scope_meta.clear_scope_cache()
        assert scope_meta._scope_for("writer") == "project"
        # identity unchanged, manifest edited -> cache still returns 'project' (no re-read)
        _fixture_manifest(tmp_path, "user")
        assert scope_meta._scope_for("writer") == "project"
    # identity changes (new install) -> re-read returns the new scope
    with mock.patch.object(scope_meta, "_leaf_spec_identity", return_value=str(tmp_path)):
        # simulate a different install identity by clearing the cache
        scope_meta.clear_scope_cache()
        _fixture_manifest(tmp_path, "user")
        assert scope_meta._scope_for("writer") == "user"
    scope_meta.clear_scope_cache()


# ---------------------------------------------------------------------------
# Endpoint integration (authenticated) — exactly one marker; API unchanged
# ---------------------------------------------------------------------------
class BridgeEndpointScopeMetaTest(TestCase):
    def setUp(self):
        self.rf = RequestFactory()
        self.user = User.objects.create_user(username="scopeuser", password="x", email="s@x.com")
        scope_meta.clear_scope_cache()

    def _req(self, path):
        req = self.rf.get(path)
        req.user = self.user
        return req

    def test_figrecipe_editor_page_stamps_exactly_one_marker(self):
        import apps.workspace.figrecipe_app.urls.figrecipe as fr

        leaf = mock.MagicMock(return_value=HttpResponse(HTML))
        with mock.patch.object(fr, "_editor_view", leaf), mock.patch.object(
            scope_meta, "_scope_for", return_value="project"
        ):
            resp = fr.editor_page(self._req("/apps/figrecipe/figrecipe/"))
        assert resp.content.count(MARKER_COUNT) == 1
        leaf.assert_called_once()

    def test_figrecipe_editor_page_idempotent_when_leaf_stamped(self):
        import apps.workspace.figrecipe_app.urls.figrecipe as fr

        stamped = HttpResponse(
            "<html><head><meta name=\"stx-app-scope\" content=\"project\"><title>FR</title>"
            "</head><body></body></html>"
        )
        with mock.patch.object(fr, "_editor_view", return_value=stamped), mock.patch.object(
            scope_meta, "_scope_for", return_value="project"
        ):
            resp = fr.editor_page(self._req("/apps/figrecipe/figrecipe/"))
        assert resp.content.count(MARKER_COUNT) == 1

    def test_figrecipe_api_dispatch_is_unchanged(self):
        import apps.workspace.figrecipe_app.urls.figrecipe as fr

        with mock.patch.object(fr, "_api_view", return_value=JsonResponse({"ok": True})), mock.patch.object(
            scope_meta, "_scope_for", return_value="project"
        ):
            resp = fr.api_dispatch_with_context(self._req("/apps/figrecipe/figrecipe/api/health"), "api/health")
        assert b"stx-app-scope" not in resp.content
        assert "application/json" in resp.get("Content-Type", "")

    def test_writer_editor_and_viewer_pages_stamp_exactly_one_marker(self):
        import apps.workspace.writer_app.urls.writer_django as wd

        with mock.patch.object(wd, "_editor_view", return_value=HttpResponse(HTML)), mock.patch.object(
            scope_meta, "_scope_for", return_value="project"
        ):
            ed = wd.editor_page(self._req("/apps/writer/editor-v2/"))
        with mock.patch.object(wd, "_viewer_view", return_value=HttpResponse(HTML)), mock.patch.object(
            scope_meta, "_scope_for", return_value="project"
        ):
            vw = wd.viewer_page(self._req("/apps/writer/viewer-v2/"))
        assert ed.content.count(MARKER_COUNT) == 1
        assert vw.content.count(MARKER_COUNT) == 1

    def test_writer_api_dispatch_is_unchanged(self):
        import apps.workspace.writer_app.urls.writer_django as wd

        with mock.patch.object(wd, "_api_view", return_value=JsonResponse({"ok": True})), mock.patch.object(
            scope_meta, "_scope_for", return_value="project"
        ):
            resp = wd.api_dispatch(self._req("/apps/writer/v2/api/health"), "api/health")
        assert b"stx-app-scope" not in resp.content

    def test_user_scoped_leaf_page_is_unchanged(self):
        import apps.workspace.figrecipe_app.urls.figrecipe as fr

        with mock.patch.object(fr, "_editor_view", return_value=HttpResponse(HTML)), mock.patch.object(
            scope_meta, "_scope_for", return_value="user"
        ):
            resp = fr.editor_page(self._req("/apps/figrecipe/figrecipe/"))
        assert resp.content.decode() == HTML and resp.content.count(MARKER_COUNT) == 0
