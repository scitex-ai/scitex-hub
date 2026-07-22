#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Template syntax validation tests.

Validates all Django templates compile without syntax errors.
Catches issues like:
- Split template tags across lines ({% if \\n foo %})
- Missing {% endif %}, {% endfor %}, etc.
- Unregistered template tags
- Invalid template syntax

Run with: pytest tests/custom/unit/templates/test_template_syntax.py -v
"""

from pathlib import Path

import pytest

# Skip if Django not available
pytest.importorskip("django")

from django.template import engines
from django.template.exceptions import TemplateSyntaxError


def get_all_template_files():
    """Find all HTML template files in the project."""
    project_root = Path(__file__).parent.parent.parent.parent.parent
    template_dirs = [
        project_root / "templates",
        project_root / "apps",
    ]

    template_files = []
    for base_dir in template_dirs:
        if base_dir.exists():
            for html_file in base_dir.rglob("*.html"):
                # Skip node_modules, venv, static files
                path_str = str(html_file)
                if any(
                    skip in path_str
                    for skip in [
                        "node_modules",
                        "venv",
                        ".venv",
                        "staticfiles",
                        "media/static",
                    ]
                ):
                    continue
                # Get relative path from project root
                rel_path = html_file.relative_to(project_root)
                template_files.append((str(rel_path), html_file))

    return template_files


def get_template_name(full_path, project_root):
    """Convert full path to Django template name."""
    path = Path(full_path)

    # Check if it's in apps/*/templates/
    if "templates" in path.parts:
        idx = path.parts.index("templates")
        return "/".join(path.parts[idx + 1 :])

    # Check if it's in root templates/
    try:
        rel = path.relative_to(project_root / "templates")
        return str(rel)
    except ValueError:
        return None


class TestTemplateSyntax:
    """Test all templates compile without syntax errors."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup Django template engine."""
        self.engine = engines["django"]
        self.project_root = Path(__file__).parent.parent.parent.parent.parent

    def test_all_templates_compile(self):
        """Validate all templates compile without syntax errors."""
        template_files = get_all_template_files()
        errors = []

        for rel_path, full_path in template_files:
            try:
                with open(full_path, "r", encoding="utf-8") as f:
                    source = f.read()
                # Try to compile the template
                self.engine.from_string(source)
            except TemplateSyntaxError as e:
                errors.append(f"{rel_path}: {e}")
            except Exception as e:
                # Some templates may have {% extends %} that fail
                # without proper context, but syntax should still be valid
                if "TemplateSyntaxError" in str(type(e).__name__):
                    errors.append(f"{rel_path}: {e}")

        if errors:
            error_msg = "Template syntax errors found:\n" + "\n".join(errors)
            pytest.fail(error_msg)

    @pytest.mark.parametrize(
        "rel_path,full_path",
        get_all_template_files(),
        ids=lambda x: x if isinstance(x, str) else None,
    )
    def test_individual_template_syntax(self, rel_path, full_path):
        """Test each template individually for better error reporting."""
        try:
            with open(full_path, "r", encoding="utf-8") as f:
                source = f.read()
            self.engine.from_string(source)
        except TemplateSyntaxError as e:
            pytest.fail(f"Template syntax error in {rel_path}: {e}")


class TestCriticalTemplates:
    """Test critical templates that must always work."""

    CRITICAL_TEMPLATES = [
        "global_base.html",
        "auth_app/signin.html",
        "auth_app/signup.html",
        "project_app/issues/form.html",
        "project_app/issues/list.html",
        "project_app/issues/detail.html",
        "public_app/landing.html",
    ]

    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup Django template engine."""
        self.engine = engines["django"]

    @pytest.mark.parametrize("template_name", CRITICAL_TEMPLATES)
    def test_critical_template_loads(self, template_name):
        """Ensure critical templates can be loaded by Django."""
        try:
            self.engine.get_template(template_name)
        except TemplateSyntaxError as e:
            pytest.fail(f"Critical template {template_name} has syntax error: {e}")
        except Exception as e:
            # Template not found is different from syntax error
            if "TemplateDoesNotExist" in str(type(e).__name__):
                pytest.skip(f"Template {template_name} not found in template dirs")
            raise
