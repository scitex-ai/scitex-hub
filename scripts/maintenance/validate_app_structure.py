#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Timestamp: "2025-11-04 14:42:51 (ywatanabe)"
# File: /home/ywatanabe/proj/scitex-hub/scripts/maintenance/validate_app_structure.py
# ----------------------------------------
from __future__ import annotations
import os

__FILE__ = "./scripts/maintenance/validate_app_structure.py"
__DIR__ = os.path.dirname(__FILE__)
# ----------------------------------------

"""
Functionalities:
  * Validates app structure compliance with FULLSTACK.md standards
  * Checks frontend structure (templates, CSS, TypeScript) consistency
  * Validates backend structure (models, views, URLs) organization
  * Reports mismatches and organizational issues
  * Ignores partials, base templates, and shared components
  * Saves validation results to console

Dependencies:
  * scripts:
    * None
  * packages:
    * pathlib, collections

Input:
  * Command-line argument: app_name (optional)
  * Directory structure: apps/[app_name]/

Output:
  * Console output: validation results and summary
"""

"""Imports"""
import sys
import re
from pathlib import Path
from collections import defaultdict
from typing import List
from typing import Set
from typing import Dict
from typing import Tuple

"""Parameters"""
# Patterns to skip during validation
SKIP_TEMPLATE_PATTERNS = {
    "_partials",  # Partials inherit parent styles
    "base",  # Base templates don't need own CSS/TS
    "shared",  # Shared components have shared CSS
    "legacy",  # Legacy files
    ".old",  # Old backup files
}

SKIP_TEMPLATE_PREFIXES = {
    "_",  # Underscore-prefixed partials
}

"""Functions & Classes"""


class AppStructureValidator:
    """Validates Django app structure against FULLSTACK.md standards.

    Example
    -------
    >>> app_path = Path("./apps/project_app")
    >>> validator = AppStructureValidator(app_path, "project_app")
    >>> passed = validator.validate()
    >>> print(passed)
    True

    Parameters
    ----------
    app_path : str or Path
        Path to the app directory
    app_name : str
        Name of the app

    Attributes
    ----------
    app_path : Path
        Path object for app directory
    app_name : str
        Name of the app
    templates_path : Path
        Path to templates directory
    css_path : Path
        Path to CSS files directory
    ts_path : Path
        Path to TypeScript files directory
    models_path : Path
        Path to models directory
    views_path : Path
        Path to views directory
    urls_path : Path
        Path to URLs directory
    services_path : Path
        Path to services directory
    errors : list
        List of validation errors
    warnings : list
        List of validation warnings
    successes : list
        List of validation successes
    """

    def __init__(self, app_path: str | Path, app_name: str) -> None:
        self.app_path: Path = Path(app_path)
        self.app_name: str = app_name
        self.templates_path: Path = self.app_path / "templates" / app_name
        self.css_path: Path = self.app_path / "static" / app_name / "css"
        self.ts_path: Path = self.app_path / "static" / app_name / "ts"
        self.models_path: Path = self.app_path / "models"
        self.views_path: Path = self.app_path / "views"
        self.urls_path: Path = self.app_path / "urls"
        self.services_path: Path = self.app_path / "services"
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.successes: List[str] = []

    def validate(self) -> bool:
        """Runs all validations.

        Returns
        -------
        bool
            True if all validations passed, False otherwise
        """
        print(f"\n🔍 VALIDATING APP: {self.app_name}")
        print(f"   Path: {self.app_path}\n")

        has_frontend: bool = self.templates_path.exists()
        if has_frontend:
            self.validate_frontend_structure()

        has_backend: bool = self.models_path.exists() or self.views_path.exists()
        if has_backend:
            self.validate_backend_structure()

        if not has_frontend and not has_backend:
            print("   ⚠️  No frontend or backend structure found")
            return False

        return self.print_summary()

    def _should_skip_template(self, template_path: Path) -> bool:
        """Checks if template should be skipped during validation.

        Parameters
        ----------
        template_path : Path
            Path to template file

        Returns
        -------
        bool
            True if template should be skipped
        """
        # Check if stem starts with underscore
        if any(
            template_path.stem.startswith(prefix) for prefix in SKIP_TEMPLATE_PREFIXES
        ):
            return True

        # Check if any part of path contains skip patterns
        path_parts = template_path.parts
        if any(
            pattern in part for part in path_parts for pattern in SKIP_TEMPLATE_PATTERNS
        ):
            return True

        return False

    def validate_frontend_structure(self) -> None:
        """Validates frontend (templates, CSS, TypeScript) structure."""
        print("📱 FRONTEND STRUCTURE:")

        main_templates: List[Path] = self._get_main_templates()
        print(f"   • Templates: {len(main_templates)} main templates")

        features: defaultdict = defaultdict(list)
        for tmpl in main_templates:
            rel_path: Path = tmpl.relative_to(self.templates_path)
            feature: str = rel_path.parts[0] if len(rel_path.parts) > 1 else "root"
            features[feature].append((tmpl.stem, rel_path))

        print(f"   • Features: {len(features)} feature directories")

        css_files: List[Path] = (
            list(self.css_path.rglob("*.css")) if self.css_path.exists() else []
        )
        print(f"   • CSS Files: {len(css_files)}")

        ts_files: List[Path] = (
            list(self.ts_path.rglob("*.ts")) if self.ts_path.exists() else []
        )
        print(f"   • TypeScript Files: {len(ts_files)}")

        # Check for inline scripts
        self._validate_inline_scripts()

        # Check 1:1:1 correspondence (template : CSS : TS)
        missing_css: List[str] = []
        missing_ts: List[str] = []

        for feature, templates in features.items():
            if feature == "root":
                continue

            for tmpl_name, rel_path in templates:
                # Construct expected paths
                css_file: Path = self.css_path / feature / f"{tmpl_name}.css"
                ts_file: Path = self.ts_path / feature / f"{tmpl_name}.ts"

                if not css_file.exists():
                    missing_css.append(f"{feature}/{tmpl_name}.css")
                if not ts_file.exists():
                    missing_ts.append(f"{feature}/{tmpl_name}.ts")

        # Report results
        if not missing_css and not missing_ts:
            self.successes.append(
                "✅ Perfect 1:1:1 correspondence (templates ↔ CSS ↔ TypeScript)"
            )
        else:
            if missing_css:
                if len(missing_css) <= 5:
                    for css in missing_css:
                        self.warnings.append(f"Missing CSS: {css}")
                else:
                    self.warnings.append(
                        f"⚠️  {len(missing_css)} templates missing CSS files"
                    )

            if missing_ts:
                if len(missing_ts) <= 5:
                    for ts in missing_ts:
                        self.warnings.append(f"Missing TS: {ts}")
                else:
                    self.warnings.append(
                        f"⚠️  {len(missing_ts)} templates missing TypeScript files"
                    )

    def _validate_inline_scripts(self) -> None:
        """Checks for inline JavaScript in templates."""
        if not self.templates_path.exists():
            return

        violations: List[Tuple[Path, int]] = []

        # Get all template files (including partials)
        all_templates = list(self.templates_path.rglob("*.html"))

        for tmpl_file in all_templates:
            try:
                content = tmpl_file.read_text(encoding="utf-8")

                # Find all <script> tags
                script_pattern = r"<script(?:\s+[^>]*)?>.*?</script>"
                scripts = re.finditer(
                    script_pattern, content, re.DOTALL | re.IGNORECASE
                )

                inline_count = 0
                for script_match in scripts:
                    script_tag = script_match.group(0)

                    # Skip external scripts (with src attribute)
                    if re.search(r"src\s*=", script_tag, re.IGNORECASE):
                        continue

                    # Extract script content (between tags)
                    content_match = re.search(
                        r"<script[^>]*>(.*?)</script>",
                        script_tag,
                        re.DOTALL | re.IGNORECASE,
                    )
                    if not content_match:
                        continue

                    script_content = content_match.group(1).strip()

                    # Skip empty scripts
                    if not script_content:
                        continue

                    # Check if it's a Django config script (mostly template variables)
                    # These typically start with window.XXX = and contain {% %} tags
                    is_config_only = (
                        re.search(r"window\.\w+\s*=\s*\{", script_content)
                        and (
                            script_content.count("{%") > 3
                            or script_content.count("{{") > 5
                        )
                        and not re.search(
                            r"(function|const|let|var)\s+\w+\s*=|addEventListener|document\.",
                            script_content,
                        )
                    )

                    if not is_config_only:
                        inline_count += 1

                if inline_count > 0:
                    violations.append((tmpl_file, inline_count))

            except Exception as e:
                self.warnings.append(
                    f"⚠️  Error reading {tmpl_file.relative_to(self.templates_path)}: {e}"
                )

        # Report results
        if not violations:
            self.successes.append("✅ No inline JavaScript in templates")
        else:
            total_scripts = sum(count for _, count in violations)
            self.warnings.append(
                f"⚠️  {len(violations)} templates with {total_scripts} inline script(s)"
            )

            # List violating files (limit to 10)
            if len(violations) <= 10:
                for tmpl_file, count in violations:
                    rel_path = tmpl_file.relative_to(self.templates_path)
                    plural = "s" if count > 1 else ""
                    self.warnings.append(
                        f"   • {rel_path} ({count} inline script{plural})"
                    )
            else:
                for tmpl_file, count in violations[:10]:
                    rel_path = tmpl_file.relative_to(self.templates_path)
                    plural = "s" if count > 1 else ""
                    self.warnings.append(
                        f"   • {rel_path} ({count} inline script{plural})"
                    )
                self.warnings.append(f"   ... and {len(violations) - 10} more files")

    def validate_backend_structure(self) -> None:
        """Validates backend (models, views, services) structure."""
        print("\n🔧 BACKEND STRUCTURE:")

        if self.models_path.exists():
            self._validate_models_layer()

        if self.views_path.exists():
            self._validate_views_layer()

        if self.urls_path.exists():
            self._validate_urls_layer()

        if self.services_path.exists():
            self._validate_services_layer()
        else:
            self.warnings.append(
                "⚠️  No services/ directory found (recommended for business logic)"
            )

    def _validate_models_layer(self) -> None:
        """Validates models are feature-organized."""
        feature_dirs: List[Path] = [
            directory
            for directory in self.models_path.iterdir()
            if directory.is_dir()
            and not directory.name.startswith("_")
            and directory.name != "__pycache__"
        ]

        monolithic_files: List[Path] = [
            file
            for file in self.models_path.glob("*.py")
            if file.name
            not in ("__init__.py", "core.py")  # core.py is OK for utilities
        ]

        if feature_dirs:
            num_modules: int = len(feature_dirs)
            print(f"   • Models: {num_modules} feature-organized modules")
            self.successes.append(
                f"✅ Models organized by feature ({num_modules} modules)"
            )

            # Check if core.py is small (utilities only)
            core_py: Path = self.models_path / "core.py"
            if core_py.exists():
                size_kb: float = core_py.stat().st_size / 1024
                if size_kb > 5:  # > 5KB suggests it needs splitting
                    self.warnings.append(
                        f"⚠️  core.py is {size_kb:.1f}KB (consider splitting if >5KB)"
                    )

        if monolithic_files:
            num_files: int = len(monolithic_files)
            warning_msg: str = (
                f"⚠️  {num_files} model files at root level (should be in feature dirs)"
            )
            self.warnings.append(warning_msg)

    def _validate_views_layer(self) -> None:
        """Validates views are feature-organized."""
        feature_dirs: List[Path] = [
            directory
            for directory in self.views_path.iterdir()
            if directory.is_dir()
            and not directory.name.startswith("_")
            and directory.name not in ("__pycache__", "shared")  # shared is OK
        ]

        monolithic_files: List[Path] = [
            file
            for file in self.views_path.glob("*.py")
            if file.name != "__init__.py"
            and not file.name.endswith("_views.py")  # Flag old monolithic views
        ]

        if feature_dirs:
            num_dirs: int = len(feature_dirs)
            print(f"   • Views: {num_dirs} feature-organized directories")
            self.successes.append(
                f"✅ Views organized by feature ({num_dirs} directories)"
            )

        # Check for old monolithic view files
        old_view_files: List[Path] = [
            file for file in self.views_path.glob("*_views.py")
        ]
        if old_view_files:
            self.warnings.append(
                f"⚠️  {len(old_view_files)} old monolithic view files found (move to legacy/)"
            )

    def _validate_urls_layer(self) -> None:
        """Validates URLs are feature-organized."""
        url_files: List[Path] = [
            file for file in self.urls_path.glob("*.py") if file.name != "__init__.py"
        ]

        if url_files:
            num_modules: int = len(url_files)
            print(f"   • URLs: {num_modules} feature-organized modules")
            self.successes.append(
                f"✅ URLs organized by feature ({num_modules} modules)"
            )

    def _validate_services_layer(self) -> None:
        """Validates services layer exists and is organized."""
        feature_dirs: List[Path] = [
            directory
            for directory in self.services_path.iterdir()
            if directory.is_dir()
            and not directory.name.startswith("_")
            and directory.name != "__pycache__"
        ]

        if feature_dirs:
            num_dirs: int = len(feature_dirs)
            print(f"   • Services: {num_dirs} feature-organized modules")
            self.successes.append(f"✅ Services layer exists ({num_dirs} modules)")
        else:
            self.warnings.append("⚠️  services/ exists but no feature modules found")

    def _get_main_templates(self) -> List[Path]:
        """Gets main templates (excluding partials, base, shared).

        Returns
        -------
        List[Path]
            List of main template file paths
        """
        if not self.templates_path.exists():
            return []

        templates: List[Path] = []
        for tmpl_file in self.templates_path.rglob("*.html"):
            if self._should_skip_template(tmpl_file):
                continue
            templates.append(tmpl_file)

        return templates

    def print_summary(self) -> bool:
        """Prints validation summary.

        Returns
        -------
        bool
            True if validation passed, False otherwise
        """
        separator: str = "=" * 60
        print(f"\n{separator}")
        print(f"SUMMARY: {self.app_name}")
        print(f"{separator}")

        if self.successes:
            num_successes: int = len(self.successes)
            print(f"\n✅ SUCCESSES ({num_successes}):")
            for success in self.successes:
                print(f"   {success}")

        if self.warnings:
            num_warnings: int = len(self.warnings)
            print(f"\n⚠️  WARNINGS ({num_warnings}):")
            for i, warning in enumerate(self.warnings, 1):
                if i > 10:  # Limit output
                    remaining = len(self.warnings) - 10
                    print(f"   ... and {remaining} more warnings")
                    break
                print(f"   {warning}")

        if self.errors:
            num_errors: int = len(self.errors)
            print(f"\n❌ ERRORS ({num_errors}):")
            for error in self.errors:
                print(f"   {error}")
            print("\n❌ VALIDATION FAILED\n")
            return False

        print("\n✅ VALIDATION PASSED\n")
        return True


def main() -> int:
    """Main entry point.

    Returns
    -------
    int
        Exit status (0 for success, 1 for failure)
    """
    project_root: Path = Path(__file__).parent.parent.parent
    apps_path: Path = project_root / "apps"

    if len(sys.argv) > 1:
        app_names: List[str] = sys.argv[1:]
    else:
        app_names: List[str] = [
            directory.name
            for directory in apps_path.iterdir()
            if directory.is_dir()
            and not directory.name.startswith("_")
            and directory.name != "__pycache__"
        ]

    separator: str = "=" * 60
    print(f"\n{separator}")
    print("APP STRUCTURE VALIDATION")
    print(f"{separator}")

    all_passed: bool = True
    for app_name in sorted(app_names):
        app_path: Path = apps_path / app_name
        if not app_path.exists():
            print(f"\n❌ App not found: {app_name}")
            all_passed = False
            continue

        validator: AppStructureValidator = AppStructureValidator(app_path, app_name)
        if not validator.validate():
            all_passed = False

    print(f"{separator}")
    if all_passed:
        print("✅ ALL VALIDATIONS PASSED")
    else:
        print("❌ SOME VALIDATIONS FAILED")
    print(f"{separator}\n")

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())

# EOF
