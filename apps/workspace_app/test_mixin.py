"""
ModuleTestMixin — reusable test base for module registration validation.

Validates that a workspace module has all required registry fields,
skill registration, CSS accent colors, and apps-ready metadata.

Usage:
    from django.test import TestCase
    from apps.workspace_app.test_mixin import ModuleTestMixin

    class WriterModuleTest(ModuleTestMixin, TestCase):
        module_name = "writer"
"""

from __future__ import annotations

from apps.workspace_app.registry import _import_builder, get_module


class ModuleTestMixin:
    """Include in any module's tests.py to get automatic registration validation."""

    module_name: str = ""  # Must be set by subclass

    @classmethod
    def setUpTestData(cls):
        from django.contrib.auth import get_user_model

        User = get_user_model()
        cls.user = User.objects.create_user(
            username="test-module-user",
            password="TestPass123!",  # pragma: allowlist secret
        )

    # --- Registry checks ---

    def test_module_registered(self):
        """Module exists in the registry."""
        mod = get_module(self.module_name)
        self.assertIsNotNone(mod, f"Module '{self.module_name}' not in registry")

    def test_partial_template_exists(self):
        """Partial template file exists on disk."""
        from django.template.loader import get_template

        mod = get_module(self.module_name)
        if mod and mod.partial_template:
            try:
                get_template(mod.partial_template)
            except Exception as e:
                self.fail(f"Template '{mod.partial_template}' not found: {e}")

    def test_icon_registered(self):
        """Module has an icon (FA or SVG)."""
        mod = get_module(self.module_name)
        self.assertTrue(
            mod.icon_fa or mod.icon_svg_tab,
            f"Module '{self.module_name}' has no icon",
        )

    def test_icon_fa_format(self):
        """icon_fa must include FA style prefix (fas/far/fab)."""
        mod = get_module(self.module_name)
        if not mod or not mod.icon_fa:
            return  # SVG-only modules are OK
        self.assertTrue(
            mod.icon_fa.startswith(("fas ", "far ", "fab ")),
            f"icon_fa '{mod.icon_fa}' must start with 'fas ', 'far ', or 'fab '",
        )

    def test_context_builder_importable(self):
        """If a context builder is set, it must be importable."""
        mod = get_module(self.module_name)
        if mod and mod.context_builder:
            builder = _import_builder(mod.context_builder)
            self.assertIsNotNone(
                builder,
                f"Cannot import context builder: {mod.context_builder}",
            )

    def test_keyboard_shortcut_defined(self):
        """Module has a keyboard shortcut for quick access."""
        mod = get_module(self.module_name)
        self.assertTrue(
            mod.keyboard_shortcut,
            f"Module '{self.module_name}' has no keyboard_shortcut",
        )

    def test_license_defined(self):
        """Module has a license identifier."""
        mod = get_module(self.module_name)
        self.assertTrue(
            mod.license,
            f"Module '{self.module_name}' has no license",
        )

    # --- LLM integration checks ---

    def test_ai_hint_defined(self):
        """Module has an ai_hint for LLM context."""
        mod = get_module(self.module_name)
        self.assertTrue(
            mod.ai_hint,
            f"Module '{self.module_name}' has no ai_hint for LLM context",
        )

    def test_accent_color_css_exists(self):
        """If accent_color is set, corresponding CSS variable must exist."""
        import os

        mod = get_module(self.module_name)
        if not mod or not mod.accent_color:
            return  # Infrastructure modules without accent are OK
        css_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "static",
            "shared",
            "css",
            "primitives",
            "colors.css",
        )
        css_path = os.path.normpath(css_path)
        if os.path.exists(css_path):
            with open(css_path) as f:
                css = f.read()
            var_name = f"--module-accent-{mod.accent_color}:"
            self.assertIn(
                var_name,
                css,
                f"CSS variable '{var_name}' not found in colors.css",
            )

    # --- Skill checks (apps-ready) ---

    def test_skill_registered(self):
        """Module has a Skill registration for LLM integration."""
        try:
            from apps.llm_app.skills import get_skill

            skill = get_skill(self.module_name)
            self.assertIsNotNone(
                skill,
                f"No skill registered for module '{self.module_name}'",
            )
        except ImportError:
            pass  # llm_app not available in test environment

    def test_skill_display_name(self):
        """Skill has a display_name for apps catalog title."""
        try:
            from apps.llm_app.skills import get_skill

            skill = get_skill(self.module_name)
            if skill:
                self.assertTrue(
                    skill.display_name,
                    f"Skill '{self.module_name}' has no display_name",
                )
        except ImportError:
            pass

    def test_skill_description(self):
        """Skill has a description for apps catalog about section."""
        try:
            from apps.llm_app.skills import get_skill

            skill = get_skill(self.module_name)
            if skill:
                self.assertTrue(
                    skill.description,
                    f"Skill '{self.module_name}' has no description",
                )
        except ImportError:
            pass

    def test_skill_capabilities(self):
        """Skill has capabilities for apps catalog listing."""
        try:
            from apps.llm_app.skills import get_skill

            skill = get_skill(self.module_name)
            if skill:
                self.assertTrue(
                    skill.capabilities,
                    f"Skill '{self.module_name}' has no capabilities list",
                )
        except ImportError:
            pass
