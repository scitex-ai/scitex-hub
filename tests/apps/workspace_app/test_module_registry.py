#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for the workspace module registry.

Ensures all registered modules are properly configured and functional.
"""

from django.test import TestCase

from apps.infra.workspace_app.registry import (
    _import_builder,
    get_all_modules,
    get_module,
    get_module_names,
    is_workspace_path,
)


class TestModuleRegistry(TestCase):
    """Ensure all registered modules are properly configured."""

    def test_registry_has_modules(self):
        """At least the 7 built-in modules should be registered."""
        modules = get_all_modules()
        self.assertGreaterEqual(len(modules), 7)

    def test_module_names_unique(self):
        """All module names must be unique."""
        names = [m.name for m in get_all_modules()]
        self.assertEqual(len(names), len(set(names)))

    def test_all_modules_have_partial_templates(self):
        """Every module that renders a workspace surface must declare a partial.

        `renders_ui` defaults to True, so a module that merely FORGOT its
        partial_template still fails here. Only a module that explicitly
        declares ``"renders_ui": false`` is exempt — the exemption is a
        stated fact in that module's manifest, greppable and individually
        revisitable, rather than an empty string that means both "no UI by
        design" and "not filled in yet".
        """
        # Arrange: only modules that claim a workspace surface are in scope.
        ui_modules = [mod for mod in get_all_modules() if mod.renders_ui]

        # Act
        missing = [mod.name for mod in ui_modules if not mod.partial_template]

        # Assert
        assert not missing, (
            f"Modules declaring renders_ui but no partial_template: {missing}. "
            "Either add the partial, or declare \"renders_ui\": false in the "
            "module's manifest.json with the reason it has no surface."
        )

    def test_all_partial_templates_exist(self):
        """All declared partial templates must exist on disk."""
        from django.template.loader import get_template

        for mod in get_all_modules():
            if mod.partial_template:
                try:
                    get_template(mod.partial_template)
                except Exception as e:
                    self.fail(
                        f"Template '{mod.partial_template}' for module "
                        f"'{mod.name}' not found: {e}"
                    )

    def test_all_context_builders_importable(self):
        """All declared context builders must be importable and callable."""
        for mod in get_all_modules():
            if mod.context_builder:
                builder = _import_builder(mod.context_builder)
                self.assertIsNotNone(
                    builder,
                    f"Cannot import context builder: {mod.context_builder}",
                )
                self.assertTrue(
                    callable(builder),
                    f"Context builder not callable: {mod.context_builder}",
                )

    def test_all_modules_have_icon(self):
        """Every module must have either an FA icon or custom SVG."""
        for mod in get_all_modules():
            has_icon = mod.icon_fa or mod.icon_svg_tab
            self.assertTrue(
                has_icon,
                f"Module '{mod.name}' has no icon (icon_fa or icon_svg_tab)",
            )

    def test_get_module_returns_correct_module(self):
        """get_module() returns the right module config."""
        writer = get_module("writer")
        self.assertIsNotNone(writer)
        self.assertEqual(writer.name, "writer")
        self.assertEqual(writer.label, "Writer")

    def test_get_module_returns_none_for_unknown(self):
        """get_module() returns None for unregistered names."""
        self.assertIsNone(get_module("nonexistent"))

    def test_is_workspace_path(self):
        """is_workspace_path() correctly identifies module paths."""
        # Modules now live under the /apps/ prefix (apps standardization);
        # the old top-level /writer/ and /tools/ are legacy redirects.
        self.assertTrue(is_workspace_path("/apps/writer/"))
        self.assertTrue(is_workspace_path("/apps/my-projects/"))
        self.assertTrue(is_workspace_path("/apps/tools/"))
        self.assertFalse(is_workspace_path("/admin/"))
        # "/" is the workspace root (maps to the home module).
        self.assertTrue(is_workspace_path("/"))

    def test_get_module_names(self):
        """get_module_names() returns all registered names."""
        names = get_module_names()
        self.assertIn("writer", names)
        # The dashboard module is registered as "my_projects" (my_projects_app/manifest.json);
        # it was previously called "hub".
        self.assertIn("my_projects", names)
        self.assertIn("tools", names)

    def test_modules_ordered(self):
        """get_all_modules() returns modules sorted by order."""
        modules = get_all_modules()
        orders = [m.order for m in modules]
        self.assertEqual(orders, sorted(orders))

    def test_build_context_with_no_builder(self):
        """Modules without context_builder return default context."""
        mod = get_module("console")
        if mod and not mod.context_builder:
            from django.test import RequestFactory

            factory = RequestFactory()
            request = factory.get("/console/")
            ctx = mod.build_context(request)
            self.assertIn("current_project", ctx)


# EOF


import importlib
import sys
from pathlib import Path

import pytest
from django.test import RequestFactory, override_settings

from apps.infra.workspace_app.registry import ModuleConfig
from apps.workspace.apps_app.services.plugin_apps import _bind_plugin_renderer


@pytest.fixture
def renderer_package(tmp_path):
    """Actual importable renderer/context and template files, without a DB."""
    name = "host_renderer_" + tmp_path.name.replace("-", "_")
    package = tmp_path / name
    package.mkdir()
    (package / "__init__.py").write_text("")
    (package / "surface.py").write_text(
        "from django.apps import AppConfig\n"
        "from django.http import JsonResponse\n"
        "class RendererConfig(AppConfig):\n"
        "    name = " + repr(name) + "\n"
        "calls = []\n"
        "def host_context(request, project):\n"
        "    calls.append('host-context')\n"
        "    return {'current_project': project, 'value': 'native', "
        "'stx_mount_prefix': '/apps/sample/guarded'}\n"
        "def no_mount_context(request, project):\n"
        "    return {'current_project': project, 'value': 'native'}\n"
        "def renderer(request, project, *, stx_mount):\n"
        "    calls.append('leaf-renderer')\n"
        "    return JsonResponse({'mount': stx_mount, 'project': project})\n"
        "def refusal(request, project, *, stx_mount):\n"
        "    raise PermissionError('leaf access refused')\n"
    )
    distribution = tmp_path / "sample_dist-1.0.dist-info"
    distribution.mkdir()
    (distribution / "METADATA").write_text(
        "Metadata-Version: 2.1\nName: sample_dist\nVersion: 1.0\n"
    )
    (distribution / "entry_points.txt").write_text(
        "[scitex.apps]\nrenderer_fixture = " + name + ".surface:RendererConfig\n"
    )
    templates = tmp_path / "templates"
    templates.mkdir()
    (templates / "native.html").write_text("{{ value }}:{{ current_project }}")
    sys.path.insert(0, str(tmp_path))
    try:
        with override_settings(
            TEMPLATES=[{
                "BACKEND": "django.template.backends.django.DjangoTemplates",
                "DIRS": [str(templates)], "APP_DIRS": False,
            }]
        ):
            yield name + ".surface"
    finally:
        sys.path.remove(str(tmp_path))
        for module in tuple(sys.modules):
            if module == name or module.startswith(name + "."):
                del sys.modules[module]


@pytest.fixture
def renderer_config(renderer_package):
    """Genuine AppConfig matched through real temporary entry-point metadata."""
    surface = importlib.import_module(renderer_package)
    package_name = renderer_package.rsplit(".", 1)[0]
    return surface.RendererConfig(package_name, importlib.import_module(package_name))


def _distribution_file(config, filename):
    return Path(config.path).parent / "sample_dist-1.0.dist-info" / filename


def _native_module(package, context="host_context"):
    return ModuleConfig(
        name="sample", label="Native", app_name="host_sample",
        partial_template="native.html", context_builder=package + "." + context,
        pip_package="sample-dist", url="/apps/sample/", order=7,
    )


def _leaf_module(package, distribution="sample_dist", renderer="renderer"):
    return ModuleConfig(
        name="sample", label="Leaf", app_name="leaf_sample",
        partial_template="leaf.html", context_builder=package + ".no_mount_context",
        pip_package=distribution, url="/unrelated/navigation/",
        content_renderer=package + "." + renderer,
    )


def test_bound_leaf_receives_server_api_mount_and_current_presentation(renderer_package, renderer_config):
    # Arrange
    native = _native_module(renderer_package)
    leaf = _leaf_module(renderer_package)
    request = RequestFactory().get("/workspace/content/sample/?stx_mount=/evil")
    _bind_plugin_renderer(native, leaf, renderer_config)
    # Act
    response = native.render_content(request, "selected-presentation")
    # Assert
    assert response.content == (
        b'{"mount": "/apps/sample/guarded", "project": "selected-presentation"}'
    )


def test_renderer_binding_preserves_every_native_identity_and_route_field(renderer_package, renderer_config):
    # Arrange
    native = _native_module(renderer_package)
    before = vars(native).copy()
    leaf = _leaf_module(renderer_package)
    # Act
    _bind_plugin_renderer(native, leaf, renderer_config)
    after = vars(native).copy()
    # Assert
    assert after == {
        **before, "content_renderer": leaf.content_renderer,
        "renderer_mount_context_builder": before["context_builder"],
    }


def test_different_distribution_cannot_take_native_renderer(renderer_package, renderer_config):
    # Arrange
    native = _native_module(renderer_package)
    before = vars(native).copy()
    leaf = _leaf_module(renderer_package, distribution="foreign-dist")
    _distribution_file(renderer_config, "METADATA").write_text(
        "Metadata-Version: 2.1\nName: foreign-dist\nVersion: 1.0\n"
    )
    # Act
    _bind_plugin_renderer(native, leaf, renderer_config)
    # Assert
    assert vars(native) == before


def test_native_without_host_builder_keeps_previous_fallback(renderer_package, renderer_config):
    # Arrange
    native = _native_module(renderer_package)
    native.context_builder = ""
    before = vars(native).copy()
    leaf = _leaf_module(renderer_package)
    # Act
    _bind_plugin_renderer(native, leaf, renderer_config)
    # Assert
    assert vars(native) == before


def test_native_context_without_api_mount_keeps_exact_partial_fallback(renderer_package, renderer_config):
    # Arrange
    native = _native_module(renderer_package, context="no_mount_context")
    leaf = _leaf_module(renderer_package, renderer="refusal")
    _bind_plugin_renderer(native, leaf, renderer_config)
    # Act
    response = native.render_content(RequestFactory().get("/workspace/content/"), "A")
    # Assert
    assert response.content == b"native:A"


def test_unbound_leaf_navigation_never_becomes_api_authority(renderer_package):
    # Arrange
    leaf = _leaf_module(renderer_package)
    request = RequestFactory().get("/unrelated/navigation/?stx_mount=/evil")
    # Act
    response = leaf.render_content(request, "A")
    # Assert
    assert (response.status_code, response.content) == (
        404, b"Hosted API mount is not declared"
    )


def test_declared_leaf_access_refusal_is_not_hidden_by_native_fallback(renderer_package, renderer_config):
    # Arrange
    native = _native_module(renderer_package)
    _bind_plugin_renderer(native, _leaf_module(renderer_package, renderer="refusal"), renderer_config)
    request = RequestFactory().get("/workspace/content/")
    # Act / Assert
    with pytest.raises(PermissionError, match="leaf access refused"):
        native.render_content(request, "A")


def test_renderer_target_is_lazy_and_missing_target_is_not_silently_rendered(renderer_package, renderer_config):
    # Arrange
    native = _native_module(renderer_package)
    _bind_plugin_renderer(native, _leaf_module(renderer_package, renderer="absent"), renderer_config)
    request = RequestFactory().get("/workspace/content/")
    # Act / Assert
    with pytest.raises(ImportError, match="absent"):
        native.render_content(request, "A")


def test_host_context_is_evaluated_once_before_leaf_renderer(renderer_package, renderer_config):
    # Arrange
    native = _native_module(renderer_package)
    _bind_plugin_renderer(native, _leaf_module(renderer_package), renderer_config)
    module = importlib.import_module(renderer_package)
    # Act
    native.render_content(RequestFactory().get("/workspace/content/"), "A")
    # Assert
    assert module.calls == ["host-context", "leaf-renderer"]


def test_old_plugin_retains_manifest_context_metadata_and_page_fallback(renderer_package):
    from types import SimpleNamespace
    from apps.workspace.apps_app.services.plugin_apps import plugin_module_config

    # Arrange
    builder = renderer_package + ".host_context"
    config = SimpleNamespace(
        name=renderer_package, label="sample_label",
        manifest={"slug": "sample", "context_builder": builder},
    )
    # Act
    module = plugin_module_config(config)
    # Assert
    assert (
        module.context_builder, module.partial_template,
        module.renders_ui, module.get_url(),
    ) == (builder, "", False, "/apps/sample/")


def test_manifest_backing_claim_cannot_override_actual_foreign_distribution(
    renderer_package, renderer_config,
):
    # Arrange: the leaf claims the native package, but its entry point belongs
    # to a different real distribution.
    native = _native_module(renderer_package)
    before = vars(native).copy()
    leaf = _leaf_module(renderer_package)
    _distribution_file(renderer_config, "METADATA").write_text(
        "Metadata-Version: 2.1\nName: foreign-dist\nVersion: 1.0\n"
    )
    # Act
    _bind_plugin_renderer(native, leaf, renderer_config)
    # Assert
    assert vars(native) == before


def test_missing_entry_point_cannot_bind_native_renderer(renderer_package, renderer_config):
    # Arrange
    native = _native_module(renderer_package)
    before = vars(native).copy()
    leaf = _leaf_module(renderer_package)
    _distribution_file(renderer_config, "entry_points.txt").unlink()
    # Act
    _bind_plugin_renderer(native, leaf, renderer_config)
    # Assert
    assert vars(native) == before


def test_entry_point_for_different_config_class_cannot_bind_native_renderer(
    renderer_package, renderer_config,
):
    # Arrange: distribution and package match, while the ready class does not.
    native = _native_module(renderer_package)
    before = vars(native).copy()
    leaf = _leaf_module(renderer_package)
    _distribution_file(renderer_config, "entry_points.txt").write_text(
        "[scitex.apps]\nrenderer_fixture = " + renderer_package + ":OtherConfig\n"
    )
    # Act
    _bind_plugin_renderer(native, leaf, renderer_config)
    # Assert
    assert vars(native) == before


def test_ambiguous_discovered_owners_cannot_bind_native_renderer(
    renderer_package, renderer_config,
):
    # Arrange: two genuine metadata records name the same ready class.
    native = _native_module(renderer_package)
    before = vars(native).copy()
    leaf = _leaf_module(renderer_package)
    second = Path(renderer_config.path).parent / "second_dist-1.0.dist-info"
    second.mkdir()
    (second / "METADATA").write_text(
        "Metadata-Version: 2.1\nName: second-dist\nVersion: 1.0\n"
    )
    (second / "entry_points.txt").write_text(
        "[scitex.apps]\nsecond_renderer = " + renderer_package + ":RendererConfig\n"
    )
    # Act
    _bind_plugin_renderer(native, leaf, renderer_config)
    # Assert
    assert vars(native) == before
