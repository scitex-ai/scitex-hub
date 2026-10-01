"""Scope markers consume ready SDK AppConfigs without leaf package knowledge."""

import importlib
import json
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import pytest
from django.apps import AppConfig
from django.apps.registry import Apps
from django.core.exceptions import ImproperlyConfigured
from django.http import HttpResponse, JsonResponse
from django.test import RequestFactory
from django.urls import path
from scitex_sdk.app.embed import ScitexAppConfig

from apps.infra.workspace_app import scope_meta
from apps.workspace.apps_app.services import plugin_apps

HTML = "<html><head><title>Plugin</title></head><body>content</body></html>"


@pytest.fixture
def plugin_registry(tmp_path, monkeypatch):
    monkeypatch.syspath_prepend(str(tmp_path))
    configs = []

    def add(slug, scope="project", *, sdk=True):
        package = f"scope_fixture_{tmp_path.name.replace('-', '_')}_{len(configs)}"
        directory = tmp_path / package
        directory.mkdir()
        (directory / "__init__.py").write_text("")
        manifest = {"slug": slug}
        if scope is not None:
            manifest["scope"] = scope
        (directory / "manifest.json").write_text(json.dumps(manifest))
        importlib.invalidate_caches()
        module = importlib.import_module(package)
        base = ScitexAppConfig if sdk else AppConfig
        cls = type("FixtureConfig", (base,), {})
        config = cls(package, module)
        configs.append(config)
        return config

    def install():
        registry = Apps(configs)
        return mock.patch("django.apps.apps", registry)

    return add, install


@pytest.mark.parametrize(
    "slug", ["new-synthetic-app", "writer", "figrecipe", "scholar"]
)
def test_scope_is_declared_by_installed_sdk_config(plugin_registry, slug):
    add, install = plugin_registry
    config = add(slug)
    assert config.app_slug == slug and config.app_scope == "project"
    with install():
        assert scope_meta._scope_for(slug) == "project"
        assert (
            scope_meta.inject_scope_meta(HttpResponse(HTML), slug).content.count(
                b"stx-app-scope"
            )
            == 1
        )


@pytest.mark.parametrize("scope", ["user", None])
def test_user_or_absent_scope_keeps_page_identical(plugin_registry, scope):
    add, install = plugin_registry
    add("synthetic-user-app", scope)
    with install():
        assert (
            scope_meta.inject_scope_meta(
                HttpResponse(HTML), "synthetic-user-app"
            ).content.decode()
            == HTML
        )


def test_unknown_and_non_sdk_configs_do_not_declare_scope(plugin_registry):
    add, install = plugin_registry
    config = add("ordinary-app", sdk=False)
    config.app_slug = "ordinary-app"
    config.app_scope = "project"
    with install():
        assert scope_meta._scope_for("ordinary-app") is None
        assert scope_meta._scope_for("absent-app") is None


def test_duplicate_slug_is_refused(plugin_registry):
    add, install = plugin_registry
    add("ambiguous")
    add("ambiguous", "user")
    with install(), pytest.raises(ImproperlyConfigured, match="ambiguous"):
        scope_meta._scope_for("ambiguous")


def test_invalid_leaf_scope_is_not_guessed(plugin_registry):
    add, install = plugin_registry
    add("invalid", "project-ish")
    with install(), pytest.raises(ValueError, match="scope"):
        scope_meta.inject_scope_meta(HttpResponse(HTML), "invalid")


def test_sdk_manifest_cache_owns_repeat_reads(plugin_registry, monkeypatch):
    add, install = plugin_registry
    config = add("cached")
    original = Path.read_text
    reads = []

    def record_read(path, *args, **kwargs):
        reads.append(path)
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", record_read)
    with install():
        assert scope_meta._scope_for("cached") == "project"
        assert scope_meta._scope_for("cached") == "project"
        assert reads.count(Path(config.path) / "manifest.json") == 1


def test_replaced_registry_config_is_used(plugin_registry):
    add, install = plugin_registry
    add("replacement")
    with install():
        assert scope_meta._scope_for("replacement") == "project"
    replacement = add("replacement", "user")
    # Use the new ready object, not a stale process cache for the slug.
    with mock.patch("django.apps.apps", Apps([replacement])):
        assert scope_meta._scope_for("replacement") == "user"


def test_existing_marker_and_non_html_responses_keep_bytes(plugin_registry):
    add, install = plugin_registry
    add("declared")
    stamped = HTML.replace(
        "<head>", '<head><meta name="stx-app-scope" content="project">'
    )
    with install():
        assert (
            scope_meta.inject_scope_meta(
                HttpResponse(stamped), "declared"
            ).content.decode()
            == stamped
        )
        response = JsonResponse({"ok": True})
        before = response.content
        assert scope_meta.inject_scope_meta(response, "declared") is response
        assert response.content == before


@pytest.mark.parametrize("slug", ["writer", "figrecipe", "scholar"])
def test_existing_legacy_route_is_not_activated(plugin_registry, slug):
    add, _install = plugin_registry
    config = add(slug)
    legacy = path(f"apps/{slug}/", lambda request: HttpResponse("legacy"))
    with (
        mock.patch.object(plugin_apps, "_configs", return_value=[config]),
        mock.patch.object(
            plugin_apps,
            "_module_exists",
            side_effect=AssertionError("collision must stop discovery"),
        ),
    ):
        assert plugin_apps.plugin_urlpatterns([legacy]) == []


def test_generic_login_boundary_is_unchanged():
    original = path("", lambda request: HttpResponse("synthetic authorized page"))
    protected = plugin_apps._wrap_login(original)
    request = RequestFactory().get("/synthetic/")
    request.user = SimpleNamespace(is_authenticated=False)
    response = protected.callback(request)
    assert response.status_code == 302 and "next=" in response["Location"]
    request.user = SimpleNamespace(is_authenticated=True)
    assert protected.callback(request).content == b"synthetic authorized page"


def test_unrelated_unreadable_manifest_cannot_block_a_valid_owner(
    plugin_registry, caplog
):
    add, install = plugin_registry
    broken = add("broken")
    (Path(broken.path) / "manifest.json").write_text("{invalid JSON")
    add("valid-owner")
    with install():
        assert scope_meta._scope_for("valid-owner") == "project"
    assert "metadata" in caplog.text and broken.label in caplog.text


def test_unreadable_owner_metadata_never_guesses_scope(plugin_registry, caplog):
    add, install = plugin_registry
    broken = add("broken-owner")
    (Path(broken.path) / "manifest.json").write_text("{invalid JSON")
    with install():
        response = scope_meta.inject_scope_meta(HttpResponse(HTML), "broken-owner")
        assert response.content.decode() == HTML
        assert scope_meta._scope_for("unknown-owner") is None
    assert "metadata" in caplog.text
