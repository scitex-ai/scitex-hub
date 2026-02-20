#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Example module inline tests — demonstrates ModuleTestMixin usage.

Run: pytest apps/example_app/tests.py
Or all module tests: pytest apps/*/tests.py -k "ModuleTest"
"""

from django.test import TestCase

from apps.workspace_app.registry import ModuleTestMixin


class ExampleModuleTest(ModuleTestMixin, TestCase):
    """Self-test: verifies this module is properly registered and functional."""

    module_name = "example"

    def test_custom_context_has_features(self):
        """Module context includes the features list."""
        from django.test import RequestFactory

        from apps.example_app.views import build_example_context

        factory = RequestFactory()
        request = factory.get("/example/")
        request.user = self.user

        ctx = build_example_context(request)
        self.assertIn("features", ctx)
        self.assertTrue(len(ctx["features"]) > 0)


# EOF
