"""Generic plugin URL namespace consumers; no leaf domain fixture is needed."""

from types import ModuleType, SimpleNamespace

import pytest
from django.core.exceptions import ImproperlyConfigured
from django.http import JsonResponse
from django.test import Client, RequestFactory, override_settings
from django.urls import include, path, reverse

from apps.workspace.apps_app.services import plugin_apps


@pytest.fixture
def plugin(monkeypatch):
    import sys

    module = ModuleType("namespace_fixture.urls")
    module.app_name = "current"
    module.namespace_aliases = ("previous",)
    module.urlpatterns = [
        path(
            "", lambda request: JsonResponse({"method": request.method}), name="editor"
        )
    ]
    config = SimpleNamespace(
        name="namespace_fixture",
        label="namespace_fixture",
        manifest={"slug": "namespace-fixture", "url": "/apps/namespace-fixture/"},
    )
    monkeypatch.setitem(sys.modules, module.__name__, module)
    monkeypatch.setattr(plugin_apps, "_configs", lambda: [config])
    available = plugin_apps._module_exists
    monkeypatch.setattr(
        plugin_apps,
        "_module_exists",
        lambda name: True if name == module.__name__ else available(name),
    )
    return config, module


def test_both_reverse_names_use_the_same_real_http_view(plugin):
    root = ModuleType("namespace_fixture_root")
    root.urlpatterns = plugin_apps.plugin_urlpatterns([])
    with override_settings(ROOT_URLCONF=root, ALLOWED_HOSTS=["testserver"]):
        urls = [reverse(namespace + ":editor") for namespace in ("current", "previous")]
        assert urls == ["/apps/namespace-fixture/"] * 2
        assert Client().get(urls[1]).json() == {"method": "GET"}
        assert Client().post(urls[0]).json() == {"method": "POST"}


def test_existing_route_owner_is_preserved(plugin):
    existing = [path("apps/namespace-fixture/", lambda request: None)]
    assert plugin_apps.plugin_urlpatterns(existing) == []


@pytest.mark.parametrize(
    "application,instance", [("other", "previous"), ("previous", "other")]
)
def test_existing_application_and_instance_names_cannot_hide_an_alias(
    plugin, application, instance
):
    from scitex_sdk.urls import NamespaceCollision

    existing = [path("other/", include(([], application), namespace=instance))]
    with pytest.raises(NamespaceCollision):
        plugin_apps.plugin_urlpatterns(existing)


def test_every_namespace_keeps_the_mount_login_policy(plugin):
    config, _ = plugin
    config.manifest["mount_policy"] = {"login_required": True}
    mounts = plugin_apps.plugin_urlpatterns([])
    assert [mount.namespace for mount in mounts] == ["current", "previous"]
    root = ModuleType("namespace_login_root")
    root.urlpatterns = mounts
    with override_settings(ROOT_URLCONF=root, ALLOWED_HOSTS=["testserver"]):
        request = RequestFactory().get("/apps/namespace-fixture/")
        request.user = SimpleNamespace(is_authenticated=False)
        for mount in mounts:
            response = mount.url_patterns[0].callback(request)
            assert response.status_code == 302
            assert response["Location"].startswith("/accounts/login/")


@pytest.mark.parametrize("declared", [True, False])
def test_older_sdk_is_refused_only_when_the_plugin_declares_the_new_contract(
    plugin, monkeypatch, declared
):
    _, module = plugin
    if not declared:
        del module.namespace_aliases
    available = plugin_apps._module_exists
    monkeypatch.setattr(
        plugin_apps,
        "_module_exists",
        lambda name: False if name == "scitex_sdk.urls" else available(name),
    )
    if declared:
        with pytest.raises(ImproperlyConfigured, match="supporting SciTeX SDK"):
            plugin_apps.plugin_urlpatterns([])
    else:
        mounts = plugin_apps.plugin_urlpatterns([])
        assert len(mounts) == 1 and mounts[0].namespace == "current"
