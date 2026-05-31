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
        """Every module must declare a partial template."""
        for mod in get_all_modules():
            self.assertTrue(
                mod.partial_template,
                f"Module '{mod.name}' has no partial_template",
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
        self.assertTrue(is_workspace_path("/writer/"))
        self.assertTrue(is_workspace_path("/apps/home/"))
        self.assertTrue(is_workspace_path("/tools/"))
        self.assertFalse(is_workspace_path("/admin/"))
        self.assertFalse(is_workspace_path("/"))

    def test_get_module_names(self):
        """get_module_names() returns all registered names."""
        names = get_module_names()
        self.assertIn("writer", names)
        self.assertIn("home", names)
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
