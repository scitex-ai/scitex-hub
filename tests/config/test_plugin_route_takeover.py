"""An admitted leaf uses the normal resolver; unqualified native routes stay."""

import importlib
import sys

import pytest
from django.apps import apps
from django.conf import settings
from django.contrib.auth.models import AnonymousUser, User
from django.shortcuts import resolve_url
from django.test import RequestFactory, override_settings
from django.urls import clear_url_caches, get_resolver, include, path

from apps.infra.workspace_app import registry
from apps.workspace.apps_app.services import plugin_apps, plugin_guards
from scitex_sdk.app.plugins import loaded_plugin_configs, mount_route


@pytest.fixture
def route_case(tmp_path, request):
    """Physical apps, real ready Django registry and real entry-point metadata."""
    mode = getattr(request, "param", "ready")
    name = "route_leaf_" + tmp_path.name.replace("-", "_")
    slug = "route-fixture-" + tmp_path.name.replace("_", "-")
    package = tmp_path / name
    package.mkdir()
    declaration = (
        f"partial_template = {name + '/partial.html'!r}\n"
        f"content_renderer = {name + '.views.render_content'!r}\n"
    )
    (package / "__init__.py").write_text("" if mode == "old" else declaration)
    (package / "apps.py").write_text(
        "from django.apps import AppConfig\n"
        "class LeafConfig(AppConfig):\n"
        f"    name = {name!r}\n"
        f"    label = {name!r}\n"
        f"    manifest = {{'slug': {slug!r}, 'label': 'Owned leaf', "
        "'pip_package': 'fixture-leaf', 'mount_policy': {'login_required': True}}\n"
    )
    (package / "views.py").write_text(
        "from django.http import HttpResponse\n"
        "from django.views.decorators.csrf import csrf_protect\n"
        "@csrf_protect\n"
        "def index(request): return HttpResponse('owned leaf')\n"
        "def render_content(request, project=None, *, stx_mount):\n"
        "    return HttpResponse('owned content:' + stx_mount)\n"
    )
    if mode != "missing_urls":
        (package / "urls.py").write_text(
            "from django.urls import path\nfrom .views import index\n"
            "app_name = 'owned_leaf'\n"
            "urlpatterns = [path('', index, name='index')]\n"
        )
    native_name = name + "_native"
    native_package = tmp_path / native_name
    native_package.mkdir()
    (native_package / "__init__.py").write_text("")
    (native_package / "urls.py").write_text(
        "from django.http import HttpResponse\nfrom django.urls import path\n"
        "def index(request): return HttpResponse('original native')\n"
        "def shadow(request): return HttpResponse('original shadow')\n"
        "app_name = 'native_fixture'\n"
        "urlpatterns = [path('', index, name='index')]\n"
    )
    dist = tmp_path / "fixture_leaf-1.0.dist-info"
    dist.mkdir()
    distribution = "foreign-leaf" if mode == "foreign" else "fixture-leaf"
    (dist / "METADATA").write_text(f"Name: {distribution}\nVersion: 1.0\n")
    entry = f"[scitex.apps]\nfixture = {name}.apps:LeafConfig\n"
    if mode != "absent":
        (dist / "entry_points.txt").write_text(entry)
    if mode == "ambiguous":
        second = tmp_path / "second_owner-1.0.dist-info"
        second.mkdir()
        (second / "METADATA").write_text("Name: second-owner\nVersion: 1.0\n")
        (second / "entry_points.txt").write_text(entry.replace("fixture =", "second ="))
    installed = ["django.contrib.auth", "django.contrib.contenttypes", name + ".apps.LeafConfig"]
    if mode == "foreign_collision":
        foreign_name = name + "_foreign"
        foreign_package = tmp_path / foreign_name
        foreign_package.mkdir()
        (foreign_package / "__init__.py").write_text("")
        (foreign_package / "apps.py").write_text(
            "from django.apps import AppConfig\nclass ForeignConfig(AppConfig):\n"
            f"    name = {foreign_name!r}\n    label = {foreign_name!r}\n"
            f"    manifest = {{'slug': {slug!r}}}\n"
        )
        (foreign_package / "urls.py").write_text(
            "from django.http import HttpResponse\nfrom django.urls import path\n"
            "def index(request): return HttpResponse('foreign leaf')\n"
            "app_name = 'foreign_leaf'\nurlpatterns = [path('', index)]\n"
        )
        foreign_dist = tmp_path / "foreign_leaf-1.0.dist-info"
        foreign_dist.mkdir()
        (foreign_dist / "METADATA").write_text("Name: foreign-leaf\nVersion: 1.0\n")
        (foreign_dist / "entry_points.txt").write_text(
            f"[scitex.apps]\nforeign = {foreign_name}.apps:ForeignConfig\n"
        )
        installed.insert(2, foreign_name + ".apps.ForeignConfig")
    sys.path.insert(0, str(tmp_path))
    importlib.invalidate_caches()
    old_registry, old_by_name = list(registry._registry), dict(registry._registry_by_name)
    plugin_guards._cached_mount_table.cache_clear()
    try:
        with override_settings(INSTALLED_APPS=installed):
            config = apps.get_app_config(name)
            route = mount_route(config)
            native = registry.ModuleConfig(
                name=slug, label="Native", app_name="native_fixture",
                pip_package="fixture-leaf", partial_template="native.html",
            )
            registry.register_module(native)
            for ready in loaded_plugin_configs():
                if ready is config:
                    plugin_apps._bind_plugin_renderer(
                        native, plugin_apps.plugin_module_config(ready), ready,
                    )
            original = [
                path(route, include(native_name + ".urls")),
                path("unchanged/", include(native_name + ".urls", namespace="unchanged_native")),
            ]
            if mode == "shadow":
                shadow = importlib.import_module(native_name + ".urls").shadow
                original.insert(0, path(route, shadow))
            yield original, native, config, route
    finally:
        registry._registry[:] = old_registry
        registry._registry_by_name.clear()
        registry._registry_by_name.update(old_by_name)
        plugin_guards._cached_mount_table.cache_clear()
        clear_url_caches()
        sys.path.remove(str(tmp_path))
        for key in tuple(sys.modules):
            if key.startswith(name):
                del sys.modules[key]
        importlib.invalidate_caches()


def _request(route, *, anonymous=False, method="get"):
    request = getattr(RequestFactory(), method)("/" + route)
    request.user = AnonymousUser() if anonymous else User(username="owned-route-user")
    return request


def test_ready_leaf_owns_resolver_and_content_mount(route_case):
    # Arrange
    original, native, config, route = route_case
    request = _request(route)
    composed = plugin_apps.compose_plugin_urlpatterns(original)
    request.urlconf = tuple(composed)
    # Act
    selected = get_resolver(request.urlconf).resolve("/" + route)
    page = selected.func(request, *selected.args, **selected.kwargs)
    content = native.render_content(request)
    unchanged = get_resolver(request.urlconf).resolve("/unchanged/")
    native_page = unchanged.func(request, *unchanged.args, **unchanged.kwargs)
    # Assert
    assert (selected.app_name, page.content, content.content, native_page.content) == (
        "owned_leaf", b"owned leaf", ("owned content:/" + route).encode(), b"original native",
    )


@pytest.mark.parametrize(
    "route_case", ["old", "absent", "foreign", "ambiguous", "missing_urls"], indirect=True,
)
def test_unqualified_leaf_keeps_real_native_resolution(route_case):
    # Arrange
    original, native, config, route = route_case
    request = _request(route)
    # Act
    selected = get_resolver(tuple(plugin_apps.compose_plugin_urlpatterns(original))).resolve("/" + route)
    response = selected.func(request, *selected.args, **selected.kwargs)
    # Assert
    assert (selected.app_name, response.content) == ("native_fixture", b"original native")


@pytest.mark.parametrize("route_case", ["shadow"], indirect=True)
def test_an_existing_shadow_is_not_displaced(route_case):
    # Arrange
    original, native, config, route = route_case
    request = _request(route)
    # Act
    selected = get_resolver(tuple(plugin_apps.compose_plugin_urlpatterns(original))).resolve("/" + route)
    response = selected.func(request, *selected.args, **selected.kwargs)
    # Assert
    assert response.content == b"original shadow"


@pytest.mark.parametrize("route_case", ["foreign_collision"], indirect=True)
def test_foreign_same_route_cannot_borrow_an_owned_takeover(route_case):
    # Arrange
    original, native, config, route = route_case
    request = _request(route)
    # Act
    selected = get_resolver(tuple(plugin_apps.compose_plugin_urlpatterns(original))).resolve("/" + route)
    response = selected.func(request, *selected.args, **selected.kwargs)
    # Assert
    assert (selected.app_name, response.content) == ("owned_leaf", b"owned leaf")


def test_taken_over_leaf_keeps_normal_login_boundary(route_case):
    # Arrange
    original, native, config, route = route_case
    request = _request(route, anonymous=True)
    # Act
    selected = get_resolver(tuple(plugin_apps.compose_plugin_urlpatterns(original))).resolve("/" + route)
    response = selected.func(request, *selected.args, **selected.kwargs)
    # Assert
    assert response.status_code == 302 and response.url.startswith(resolve_url(settings.LOGIN_URL))


def test_taken_over_leaf_keeps_real_csrf_refusal(route_case):
    # Arrange
    original, native, config, route = route_case
    request = _request(route, method="post")
    # Act
    selected = get_resolver(tuple(plugin_apps.compose_plugin_urlpatterns(original))).resolve("/" + route)
    response = selected.func(request, *selected.args, **selected.kwargs)
    # Assert
    assert response.status_code == 403
