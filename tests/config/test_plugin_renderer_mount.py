"""A leaf renderer needs an actual mount, without a native domain context."""

import importlib
import sys
from types import ModuleType

import pytest
from django.test import RequestFactory, override_settings
from django.urls import (
    clear_url_caches,
    get_script_prefix,
    get_urlconf,
    include,
    path,
    set_script_prefix,
    set_urlconf,
)

from apps.infra.workspace_app.registry import ModuleConfig
from apps.workspace.apps_app.services.plugin_apps import _bind_plugin_renderer


@pytest.fixture
def mounted_leaf(tmp_path):
    """Real importable views/URLconf and entry-point distribution in a temp root."""
    name = "mounted_leaf_" + tmp_path.name.replace("-", "_")
    package = tmp_path / name
    package.mkdir()
    (package / "__init__.py").write_text("")
    (package / "views.py").write_text(
        "from django.http import HttpResponse\n"
        "def index(request): return HttpResponse('leaf root')\n"
        "def render_content(request, project=None, *, stx_mount):\n"
        "    return HttpResponse(f'leaf:{stx_mount}:{project}')\n"
        "def native_context(request, project=None):\n"
        "    return {'current_project': project}\n"
        "def forbidden_native_context(request, project=None):\n"
        "    raise RuntimeError('native domain context must not run')\n"
    )
    (package / "urls.py").write_text(
        "from django.urls import path\nfrom .views import index\n"
        "urlpatterns = [path('', index, name='index')]\n"
    )
    (package / "apps.py").write_text(
        "from django.apps import AppConfig\n"
        "class FixtureConfig(AppConfig):\n"
        f"    name = {name!r}\n"
        "    label = 'mounted_fixture'\n"
        "    manifest = {'slug': 'fixture'}\n"
    )
    dist = tmp_path / "fixture_leaf-1.0.dist-info"
    dist.mkdir()
    (dist / "METADATA").write_text("Name: fixture-leaf\nVersion: 1.0\n")
    (dist / "entry_points.txt").write_text(
        f"[scitex.apps]\nfixture = {name}.apps:FixtureConfig\n"
    )
    sys.path.insert(0, str(tmp_path))
    importlib.invalidate_caches()
    root = ModuleType(name + "_root")
    sys.modules[root.__name__] = root
    try:
        leaf = importlib.import_module(name + ".views")
        config_type = importlib.import_module(name + ".apps").FixtureConfig
        config = config_type(name, importlib.import_module(name))
        root.urlpatterns = [path("apps/fixture/", include(name + ".urls"))]
        templates = [
            {
                "BACKEND": "django.template.backends.django.DjangoTemplates",
                "OPTIONS": {
                    "loaders": [
                        (
                            "django.template.loaders.locmem.Loader",
                            {
                                "native.html": "native:{{ current_project }}",
                            },
                        )
                    ]
                },
            }
        ]
        with override_settings(ROOT_URLCONF=root, TEMPLATES=templates):
            yield name, leaf, root, config
    finally:
        clear_url_caches()
        sys.path.remove(str(tmp_path))
        for key in tuple(sys.modules):
            if key == name or key.startswith(name + ".") or key == root.__name__:
                del sys.modules[key]
        importlib.invalidate_caches()


def _native(name):
    return ModuleConfig(
        name="fixture",
        label="Fixture",
        app_name="native_fixture",
        pip_package="fixture-leaf",
        partial_template="native.html",
        context_builder=name + ".views.native_context",
        url="/native/",
    )


def _bound(name):
    module = _native(name)
    module.content_renderer = name + ".views.render_content"
    module.renderer_mount_route = "apps/fixture/"
    module.renderer_leaf_urlconf = name + ".urls"
    return module


def test_actual_leaf_mount_renders_without_native_domain_context(mounted_leaf):
    # Arrange
    name, leaf, root, config = mounted_leaf
    module = _bound(name)
    module.context_builder = name + ".views.forbidden_native_context"
    request = RequestFactory().get("/content/?mount=/untrusted/")
    # Act
    response = module.render_content(request, 41)
    # Assert
    assert response.status_code == 200 and response.content == b"leaf:/apps/fixture/:41"


def test_nested_registered_mount_uses_actual_prefix(mounted_leaf):
    # Arrange
    name, leaf, root, config = mounted_leaf
    root.urlpatterns = [
        path("apps/", include([path("fixture/", include(name + ".urls"))]))
    ]
    clear_url_caches()
    # Act
    response = _bound(name).render_content(RequestFactory().get("/content/"), 41)
    # Assert
    assert response.content == b"leaf:/apps/fixture/:41"


def test_script_prefix_is_retained_on_actual_leaf_mount(mounted_leaf):
    # Arrange
    name, leaf, root, config = mounted_leaf
    original = get_script_prefix()
    set_script_prefix("/research/")
    try:
        # Act
        response = _bound(name).render_content(RequestFactory().get("/content/"), 41)
        # Assert
        assert response.content == b"leaf:/research/apps/fixture/:41"
    finally:
        set_script_prefix(original)


def test_a_shadowed_leaf_mount_keeps_native_fallback(mounted_leaf):
    # Arrange
    name, leaf, root, config = mounted_leaf
    root.urlpatterns.insert(0, path("apps/fixture/", leaf.index))
    clear_url_caches()
    # Act
    response = _bound(name).render_content(RequestFactory().get("/content/"), 41)
    # Assert
    assert response.content == b"native:41"


@pytest.mark.parametrize("thread_shadowed", [False, True])
def test_thread_urlconf_controls_the_actual_leaf_mount(mounted_leaf, thread_shadowed):
    # Arrange
    name, leaf, root, config = mounted_leaf
    alternate = ModuleType(name + "_alternate")
    alternate.urlpatterns = [
        path("apps/fixture/", leaf.index)
        if thread_shadowed
        else path("apps/fixture/", include(name + ".urls"))
    ]
    root.urlpatterns = [
        path("apps/fixture/", include(name + ".urls"))
        if thread_shadowed
        else path("apps/fixture/", leaf.index)
    ]
    original = get_urlconf()
    set_urlconf(alternate)
    try:
        # Act
        response = _bound(name).render_content(RequestFactory().get("/content/"), 41)
        # Assert
        expected = b"native:41" if thread_shadowed else b"leaf:/apps/fixture/:41"
        assert response.content == expected
    finally:
        set_urlconf(original)


@pytest.mark.parametrize("request_shadowed", [False, True])
def test_request_urlconf_takes_precedence_over_thread_urlconf(
    mounted_leaf, request_shadowed
):
    # Arrange
    name, leaf, root, config = mounted_leaf
    alternate = ModuleType(name + "_alternate")
    alternate.urlpatterns = [
        path("apps/fixture/", leaf.index)
        if request_shadowed
        else path("apps/fixture/", include(name + ".urls"))
    ]
    root.urlpatterns = [
        path("apps/fixture/", include(name + ".urls"))
        if request_shadowed
        else path("apps/fixture/", leaf.index)
    ]
    request = RequestFactory().get("/content/")
    request.urlconf = alternate
    original = get_urlconf()
    set_urlconf(root)
    try:
        # Act
        response = _bound(name).render_content(request, 41)
        # Assert
        expected = b"native:41" if request_shadowed else b"leaf:/apps/fixture/:41"
        assert response.content == expected
    finally:
        set_urlconf(original)


def test_an_absent_leaf_mount_keeps_native_fallback(mounted_leaf):
    # Arrange
    name, leaf, root, config = mounted_leaf
    root.urlpatterns = []
    clear_url_caches()
    # Act
    response = _bound(name).render_content(RequestFactory().get("/content/"), 41)
    # Assert
    assert response.content == b"native:41"


def test_a_different_urlconf_at_the_same_path_is_not_leaf_provenance(mounted_leaf):
    # Arrange
    name, leaf, root, config = mounted_leaf
    root.urlpatterns = [path("apps/fixture/", include([path("", leaf.index)]))]
    clear_url_caches()
    # Act
    response = _bound(name).render_content(RequestFactory().get("/content/"), 41)
    # Assert
    assert response.content == b"native:41"


@pytest.mark.parametrize(
    "route",
    [
        "/apps/fixture/",
        "apps/../fixture/",
        "apps//fixture/",
        "apps/fixture/?q=1",
        "apps/fixture/#part",
        "apps/fixture",
    ],
)
def test_invalid_mount_declarations_keep_native_fallback(mounted_leaf, route):
    # Arrange
    name, leaf, root, config = mounted_leaf
    module = _bound(name)
    module.renderer_mount_route = route
    # Act
    response = module.render_content(RequestFactory().get("/content/"), 41)
    # Assert
    assert response.content == b"native:41"


def test_discovered_backing_distribution_binds_only_leaf_mount_capability(mounted_leaf):
    # Arrange
    name, leaf, root, config = mounted_leaf
    native = _native(name)
    plugin = _bound(name)
    before = (native.name, native.url, native.context_builder, native.partial_template)
    # Act
    _bind_plugin_renderer(native, plugin, config)
    # Assert
    assert (
        native.name,
        native.url,
        native.context_builder,
        native.partial_template,
    ) == before
    assert native.renderer_leaf_urlconf == name + ".urls"
    assert (
        native.render_content(RequestFactory().get("/content/"), 41).content
        == b"leaf:/apps/fixture/:41"
    )


def test_a_slug_collision_from_a_different_distribution_cannot_bind(mounted_leaf):
    # Arrange
    name, leaf, root, config = mounted_leaf
    native = _native(name)
    native.pip_package = "other-distribution"
    # Act
    _bind_plugin_renderer(native, _bound(name), config)
    # Assert
    assert native.content_renderer == "" and native.renderer_leaf_urlconf == ""


def test_leaf_mount_does_not_require_a_native_domain_context_builder(mounted_leaf):
    # Arrange
    name, leaf, root, config = mounted_leaf
    native = _native(name)
    native.context_builder = ""
    # Act
    _bind_plugin_renderer(native, _bound(name), config)
    # Assert
    assert (
        native.render_content(RequestFactory().get("/content/"), 41).content
        == b"leaf:/apps/fixture/:41"
    )
