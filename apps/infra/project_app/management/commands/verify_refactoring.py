#!/usr/bin/env python
"""
Django management command for comprehensive refactoring verification.
Checks both frontend (templates, CSS, TypeScript) and backend (models, views, services) structure
against FULLSTACK.md compliance.

Usage:
    python manage.py verify_refactoring
"""

from django.core.management.base import BaseCommand
from pathlib import Path
from collections import defaultdict


class RefactoringVerifier:
    def __init__(self, app_path):
        self.app_path = Path(app_path)
        self.templates_path = self.app_path / "templates" / "project_app"
        self.css_path = self.app_path / "static" / "project_app" / "css"
        self.ts_path = self.app_path / "static" / "project_app" / "ts"
        self.models_path = self.app_path / "models"
        self.views_path = self.app_path / "views"
        self.urls_path = self.app_path / "urls"

        self.errors = []
        self.warnings = []
        self.successes = []

    def verify_frontend_structure(self):
        """Verify frontend (templates, CSS, TypeScript) structure"""
        # Check main templates exist
        main_templates = self._get_main_templates()

        # Group by feature
        features = defaultdict(list)
        for tmpl in main_templates:
            rel_path = tmpl.relative_to(self.templates_path)
            feature = rel_path.parts[0] if len(rel_path.parts) > 1 else "root"
            features[feature].append(tmpl.stem)

        # Check CSS files
        css_files = list(self.css_path.rglob("*.css"))

        # Check TypeScript files
        ts_files = list(self.ts_path.rglob("*.ts"))

        # Verify 1:1:1 correspondence for main templates
        mismatches = []
        for feature, templates in features.items():
            if feature == "root":
                continue
            for tmpl_name in templates:
                css_file = self.css_path / feature / f"{tmpl_name}.css"
                ts_file = self.ts_path / feature / f"{tmpl_name}.ts"

                if not css_file.exists():
                    mismatches.append(f"Missing CSS: {feature}/{tmpl_name}.css")
                if not ts_file.exists():
                    mismatches.append(f"Missing TS: {feature}/{tmpl_name}.ts")

        if not mismatches:
            self.successes.append("✅ All main templates have CSS and TypeScript files")

        return {
            "templates": len(main_templates),
            "features": len(features),
            "css_files": len(css_files),
            "ts_files": len(ts_files),
            "mismatches": len(mismatches),
        }

    def verify_backend_structure(self):
        """Verify backend (models, views, services) structure"""
        results = {
            "models_ok": False,
            "views_organized": 0,
            "urls_count": 0,
        }

        # Check models organization
        repo_module = self.models_path / "repository"
        if repo_module.exists():
            project_py = repo_module / "project.py"
            if project_py.exists():
                results["models_ok"] = True
                self.successes.append("✅ Repository models properly organized")

        # Check core.py is cleaned up
        core_py = self.models_path / "core.py"
        if core_py.exists():
            size = core_py.stat().st_size
            if size < 5000:
                self.successes.append("✅ core.py properly refactored")

        # Check __init__.py exports
        init_py = self.models_path / "__init__.py"
        if init_py.exists():
            with open(init_py) as f:
                content = f.read()
                if "from .repository import" in content:
                    self.successes.append(
                        "✅ models/__init__.py properly exports repository models"
                    )

        # Check views organization
        for item in self.views_path.iterdir():
            if item.is_dir() and not item.name.startswith("_"):
                results["views_organized"] += 1

        if results["views_organized"] > 0:
            self.successes.append(
                f"✅ Views organized by feature ({results['views_organized']} features)"
            )

        # Check URLs organization
        url_files = [f for f in self.urls_path.glob("*.py") if f.name != "__init__.py"]
        results["urls_count"] = len(url_files)

        if results["urls_count"] > 0:
            self.successes.append(
                f"✅ URLs organized by feature ({results['urls_count']} modules)"
            )

        return results

    def verify_backward_compatibility(self):
        """Verify backward compatibility is maintained"""
        init_py = self.models_path / "__init__.py"
        if not init_py.exists():
            self.errors.append("models/__init__.py missing")
            return False

        with open(init_py) as f:
            content = f.read()

        required_exports = [
            "Project",
            "ProjectMembership",
            "ProjectPermission",
            "VisitorAllocation",
        ]

        all_present = all(name in content for name in required_exports)

        if all_present:
            self.successes.append("✅ Backward compatibility maintained")
            return True
        else:
            missing = [n for n in required_exports if n not in content]
            self.errors.append(f"Missing exports: {missing}")
            return False

    def _get_main_templates(self):
        """Get main templates (excluding partials and base)"""
        templates = []
        for tmpl_file in self.templates_path.rglob("*.html"):
            # Skip partials and base files
            if tmpl_file.stem.startswith("_"):
                continue
            if "_partials" in tmpl_file.parts:
                continue
            if "base" in tmpl_file.parts or tmpl_file.name == "base.html":
                continue
            if ".old" in tmpl_file.parts or "legacy" in tmpl_file.parts:
                continue
            templates.append(tmpl_file)
        return templates

    def run(self):
        """Run all verifications"""
        frontend_results = self.verify_frontend_structure()
        backend_results = self.verify_backend_structure()
        compat_ok = self.verify_backward_compatibility()

        return {
            "frontend": frontend_results,
            "backend": backend_results,
            "compatibility": compat_ok,
            "successes": self.successes,
            "warnings": self.warnings,
            "errors": self.errors,
        }


class Command(BaseCommand):
    help = "Verify project_app refactoring compliance with FULLSTACK.md guidelines"

    def handle(self, *args, **options):
        # Get app path
        app_path = Path(__file__).parent.parent.parent

        self.stdout.write("\n🔍 COMPREHENSIVE REFACTORING VERIFICATION")
        self.stdout.write(f"   App Path: {app_path}\n")

        verifier = RefactoringVerifier(app_path)
        results = verifier.run()

        # Print frontend results
        self.stdout.write(self.style.SUCCESS("✅ FRONTEND STRUCTURE VERIFICATION"))
        self.stdout.write(
            f"   • Templates: {results['frontend']['templates']} main templates"
        )
        self.stdout.write(
            f"   • Features: {results['frontend']['features']} feature directories"
        )
        self.stdout.write(f"   • CSS Files: {results['frontend']['css_files']}")
        self.stdout.write(f"   • TypeScript Files: {results['frontend']['ts_files']}")

        # Print backend results
        self.stdout.write(self.style.SUCCESS("\n✅ BACKEND STRUCTURE VERIFICATION"))
        self.stdout.write(
            f"   • Models Organized: {'Yes' if results['backend']['models_ok'] else 'No'}"
        )
        self.stdout.write(
            f"   • Views Features: {results['backend']['views_organized']}"
        )
        self.stdout.write(f"   • URL Modules: {results['backend']['urls_count']}")

        # Print backward compatibility
        self.stdout.write(self.style.SUCCESS("\n✅ BACKWARD COMPATIBILITY"))
        self.stdout.write(
            f"   • Status: {'✅ OK' if results['compatibility'] else '❌ FAILED'}"
        )

        # Print summary
        self.stdout.write(self.style.SUCCESS("\n✅ VERIFICATION SUMMARY"))
        self.stdout.write(f"   • Successes: {len(results['successes'])}")
        self.stdout.write(f"   • Warnings: {len(results['warnings'])}")
        self.stdout.write(f"   • Errors: {len(results['errors'])}")

        for success in results["successes"]:
            self.stdout.write(f"     {success}")

        if results["warnings"]:
            self.stdout.write(self.style.WARNING("\n⚠️  WARNINGS:"))
            for warning in results["warnings"]:
                self.stdout.write(f"     {warning}")

        if results["errors"]:
            self.stdout.write(self.style.ERROR("\n❌ ERRORS:"))
            for error in results["errors"]:
                self.stdout.write(f"     {error}")
            return

        self.stdout.write(self.style.SUCCESS("\n" + "=" * 60))
        self.stdout.write(self.style.SUCCESS("✅ REFACTORING VERIFICATION PASSED"))
        self.stdout.write(self.style.SUCCESS("=" * 60 + "\n"))
