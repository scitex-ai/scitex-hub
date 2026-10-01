#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Native bridge metadata follows ready leaf SDK AppConfigs.

Idempotency, unchanged user/API responses and the installed-config cache are
consumer behaviors. SDK owns manifest loading/defaults/validation; these tests
use the actual installed FigRecipe and Writer config classes, not a Hub parser.
Authenticated endpoint tests retain representative downstream HTML/JSON so
metadata wiring does not perform project I/O or compile a manuscript.
"""

import json
from functools import lru_cache
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from unittest import mock

from django.apps import apps
from django.apps.registry import Apps
from django.contrib.auth.models import User
from django.http import HttpResponse, JsonResponse
from django.test import RequestFactory, TestCase

from apps.infra.workspace_app import scope_meta

HTML = "<html><head><title>Leaf</title></head><body><div id=root></div></body></html>"
MARKER_COUNT = b"stx-app-scope"


def _leaf_config(tmp_path, slug, scope="project"):
    """A real leaf AppConfig with a synthetic, SDK-read manifest directory."""
    label = {"figrecipe": "figrecipe_editor", "writer": "writer_editor"}[slug]
    installed = apps.get_app_config(label)
    directory = tmp_path / slug
    directory.mkdir(exist_ok=True)
    manifest = {"slug": slug}
    if scope is not None:
        manifest["scope"] = scope
    (directory / "manifest.json").write_text(json.dumps(manifest))
    config = type(installed)(installed.name, installed.module)
    config.path = str(directory)
    return config


def _installed_registry(*configs):
    # A ready Django registry runs the real SDK/leaf AppConfig lifecycle.
    return mock.patch("django.apps.apps", Apps(configs))


@lru_cache(maxsize=1)
def _writer_bridge():
    """Execute the real wrapper without eagerly importing all legacy URL owners.

    The wrapper uses only absolute imports. Its source/decorators/leaf imports
    are unchanged; unrelated sibling compilation routes are outside this test.
    """
    source = (
        Path(__file__).resolve().parents[3]
        / "apps/workspace/writer_app/urls/writer_django.py"
    )
    spec = spec_from_file_location("writer_scope_bridge_consumer", source)
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_project_scope_injects_exactly_one_marker():
    assert apps.get_app_config("figrecipe_editor").app_scope == "project"
    out = scope_meta.inject_scope_meta(HttpResponse(HTML), "figrecipe")
    assert out.content.count(MARKER_COUNT) == 1


def test_leaf_that_already_stamps_is_not_duplicated():
    stamped = (
        '<html><head><meta name="stx-app-scope" content="project">'
        "<title>Leaf</title></head><body></body></html>"
    )
    out = scope_meta.inject_scope_meta(HttpResponse(stamped), "figrecipe")
    assert out.content.decode() == stamped and out.content.count(MARKER_COUNT) == 1


def test_user_scope_leaves_html_unchanged(tmp_path):
    config = _leaf_config(tmp_path, "figrecipe", "user")
    with _installed_registry(config):
        out = scope_meta.inject_scope_meta(HttpResponse(HTML), "figrecipe")
    assert out.content.decode() == HTML and out.content.count(MARKER_COUNT) == 0


def test_absent_or_unknown_scope_is_unchanged(tmp_path):
    config = _leaf_config(tmp_path, "figrecipe", None)
    with _installed_registry(config):
        assert config.app_scope == "user"
        assert (
            scope_meta.inject_scope_meta(
                HttpResponse(HTML), "figrecipe"
            ).content.decode()
            == HTML
        )
        assert (
            scope_meta.inject_scope_meta(
                HttpResponse(HTML), "not-a-leaf"
            ).content.decode()
            == HTML
        )


def test_non_html_response_is_untouched():
    response = JsonResponse({"ok": True})
    before = response.content
    assert scope_meta.inject_scope_meta(response, "figrecipe") is response
    assert response.content == before and MARKER_COUNT not in response.content


def test_scope_for_reads_leaf_manifest_project(tmp_path):
    configs = [_leaf_config(tmp_path, slug) for slug in ("figrecipe", "writer")]
    with _installed_registry(*configs):
        assert scope_meta._scope_for("figrecipe") == "project"
        assert scope_meta._scope_for("writer") == "project"


def test_scope_for_defaults_to_user_when_manifest_has_no_scope(tmp_path):
    config = _leaf_config(tmp_path, "figrecipe", None)
    with _installed_registry(config):
        assert scope_meta._scope_for("figrecipe") == "user"


def test_scope_for_none_when_leaf_not_registered():
    with _installed_registry():
        assert scope_meta._scope_for("figrecipe") is None


def test_scope_cache_holds_until_config_changes(tmp_path):
    config = _leaf_config(tmp_path, "writer")
    with _installed_registry(config):
        assert scope_meta._scope_for("writer") == "project"
        # SDK owns caching: changing disk bytes cannot mutate a ready config.
        _leaf_config(tmp_path, "writer", "user")
        scope_meta.clear_scope_cache()
        assert scope_meta._scope_for("writer") == "project"
    # A newly ready config after replacement is a different installed identity.
    replacement = _leaf_config(tmp_path, "writer", "user")
    with _installed_registry(replacement):
        assert scope_meta._scope_for("writer") == "user"
    scope_meta.clear_scope_cache()


class BridgeEndpointScopeMetaTest(TestCase):
    def setUp(self):
        self.rf = RequestFactory()
        self.user = User.objects.create_user(
            username="scopeuser", password="x", email="s@x.com"
        )
        scope_meta.clear_scope_cache()

    def _req(self, path):
        req = self.rf.get(path)
        req.user = self.user
        return req

    def test_figrecipe_editor_page_stamps_exactly_one_marker(self):
        import apps.workspace.figrecipe_app.urls.figrecipe as fr

        leaf = mock.MagicMock(return_value=HttpResponse(HTML))
        with mock.patch.object(fr, "_editor_view", leaf):
            resp = fr.editor_page(self._req("/apps/figrecipe/figrecipe/"))
        assert resp.content.count(MARKER_COUNT) == 1
        leaf.assert_called_once()

    def test_figrecipe_editor_page_idempotent_when_leaf_stamped(self):
        import apps.workspace.figrecipe_app.urls.figrecipe as fr

        stamped = HttpResponse(
            '<html><head><meta name="stx-app-scope" content="project"><title>FR</title>'
            "</head><body></body></html>"
        )
        with mock.patch.object(fr, "_editor_view", return_value=stamped):
            resp = fr.editor_page(self._req("/apps/figrecipe/figrecipe/"))
        assert resp.content.count(MARKER_COUNT) == 1

    def test_figrecipe_api_dispatch_is_unchanged(self):
        import apps.workspace.figrecipe_app.urls.figrecipe as fr

        with mock.patch.object(
            fr, "_api_view", return_value=JsonResponse({"ok": True})
        ):
            resp = fr.api_dispatch_with_context(
                self._req("/apps/figrecipe/figrecipe/api/health"), "api/health"
            )
        assert MARKER_COUNT not in resp.content
        assert "application/json" in resp.get("Content-Type", "")

    def test_writer_editor_and_viewer_pages_stamp_exactly_one_marker(self):
        wd = _writer_bridge()

        with mock.patch.object(wd, "_editor_view", return_value=HttpResponse(HTML)):
            ed = wd.editor_page(self._req("/apps/writer/editor-v2/"))
        with mock.patch.object(wd, "_viewer_view", return_value=HttpResponse(HTML)):
            vw = wd.viewer_page(self._req("/apps/writer/viewer-v2/"))
        assert ed.content.count(MARKER_COUNT) == 1
        assert vw.content.count(MARKER_COUNT) == 1

    def test_writer_api_dispatch_is_unchanged(self):
        wd = _writer_bridge()

        with mock.patch.object(
            wd, "_api_view", return_value=JsonResponse({"ok": True})
        ):
            resp = wd.api_dispatch(
                self._req("/apps/writer/v2/api/health"), "api/health"
            )
        assert MARKER_COUNT not in resp.content

    def test_user_scoped_leaf_page_is_unchanged(self):
        import tempfile
        from pathlib import Path

        import apps.workspace.figrecipe_app.urls.figrecipe as fr

        with tempfile.TemporaryDirectory() as directory:
            config = _leaf_config(Path(directory), "figrecipe", "user")
            with (
                _installed_registry(config),
                mock.patch.object(fr, "_editor_view", return_value=HttpResponse(HTML)),
            ):
                resp = fr.editor_page(self._req("/apps/figrecipe/figrecipe/"))
        assert resp.content.decode() == HTML and resp.content.count(MARKER_COUNT) == 0
