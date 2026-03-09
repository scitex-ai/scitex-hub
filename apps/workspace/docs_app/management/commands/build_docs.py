#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: /home/ywatanabe/proj/scitex-cloud/apps/docs_app/management/commands/build_docs.py

from django.core.management.base import BaseCommand
from django.conf import settings
from pathlib import Path
import subprocess


class Command(BaseCommand):
    help = "Build Sphinx documentation for SciTeX modules"

    def add_arguments(self, parser):
        parser.add_argument(
            "--module",
            type=str,
            choices=["scholar", "code", "viz", "writer", "all"],
            default="all",
            help="Which module documentation to build (default: all)",
        )
        parser.add_argument(
            "--clean",
            action="store_true",
            help="Clean build directory before building",
        )

    def handle(self, *args, **options):
        module = options["module"]
        clean = options["clean"]

        modules_to_build = {
            "scholar": "externals/SciTeX-Scholar/docs",
            "code": "externals/SciTeX-Code/docs",
            "viz": "externals/SciTeX-Viz/docs",
            "writer": "externals/SciTeX-Writer/docs",
        }

        if module == "all":
            modules = modules_to_build
        else:
            modules = {module: modules_to_build[module]}

        self.stdout.write(
            self.style.SUCCESS(
                f"Building documentation for: {', '.join(modules.keys())}"
            )
        )

        for module_name, doc_path in modules.items():
            self._build_module_docs(module_name, doc_path, clean)

    def _build_module_docs(self, module_name, doc_path, clean):
        """Build documentation for a specific module."""
        full_path = Path(settings.BASE_DIR) / doc_path

        if not full_path.exists():
            self.stdout.write(
                self.style.WARNING(
                    f"Documentation directory not found for {module_name}: {full_path}"
                )
            )
            return

        # Check for conf.py or sphinx configuration
        conf_py = full_path / "conf.py"
        sphinx_dir = full_path / "sphinx"

        if not conf_py.exists() and sphinx_dir.exists():
            # Some projects have sphinx/ subdirectory
            full_path = sphinx_dir
            conf_py = full_path / "conf.py"

        if not conf_py.exists():
            self.stdout.write(
                self.style.WARNING(
                    f"No Sphinx configuration found for {module_name} at {full_path}"
                )
            )
            return

        # Build directory
        build_dir = full_path / "_build" / "html"

        # Clean if requested
        if clean and build_dir.exists():
            self.stdout.write(f"Cleaning {build_dir}")
            subprocess.run(["rm", "-rf", str(build_dir)], check=True)

        # Build documentation
        self.stdout.write(f"Building {module_name} documentation...")
        try:
            result = subprocess.run(
                ["sphinx-build", "-b", "html", str(full_path), str(build_dir)],
                capture_output=True,
                text=True,
                check=True,
            )

            self.stdout.write(
                self.style.SUCCESS(f"✓ Successfully built {module_name} documentation")
            )
            self.stdout.write(f"  Output: {build_dir}")

        except subprocess.CalledProcessError as e:
            self.stdout.write(
                self.style.ERROR(f"✗ Failed to build {module_name} documentation")
            )
            self.stdout.write(self.style.ERROR(f"Error: {e.stderr}"))
        except FileNotFoundError:
            self.stdout.write(
                self.style.ERROR(
                    "sphinx-build not found. Please install Sphinx: pip install sphinx"
                )
            )
