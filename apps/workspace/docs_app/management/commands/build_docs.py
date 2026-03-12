#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build Sphinx documentation for all SciTeX Python packages."""

from __future__ import annotations

import subprocess
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

# Map package name → relative path from BASE_DIR to Sphinx source dir
_SPHINX_SOURCES = {
    "scitex-python": "../scitex-python/docs/sphinx",
    "scitex-cloud": "docs/sphinx",
    "figrecipe": "../figrecipe/docs/sphinx",
    "scitex-writer": "../scitex-writer/docs/sphinx",
    "scitex-io": "../scitex-io/docs/sphinx",
    "scitex-stats": "../scitex-stats/docs/sphinx",
    "scitex-clew": "../scitex-clew/docs/sphinx",
    "scitex-dataset": "../scitex-dataset/docs/sphinx",
    "scitex-linter": "../scitex-linter/docs/sphinx",
    "scitex-container": "../scitex-container/docs/sphinx",
}


class Command(BaseCommand):
    help = "Build Sphinx documentation for SciTeX Python packages"

    def add_arguments(self, parser):
        parser.add_argument(
            "--module",
            type=str,
            default="all",
            help="Package name to build (default: all). Use --list to see available.",
        )
        parser.add_argument(
            "--clean",
            action="store_true",
            help="Clean build directory before building",
        )
        parser.add_argument(
            "--list",
            action="store_true",
            help="List available packages and their build status",
        )

    def handle(self, *args, **options):
        if options["list"]:
            return self._list_status()

        module = options["module"]
        clean = options["clean"]

        if module == "all":
            modules = dict(_SPHINX_SOURCES)
        elif module in _SPHINX_SOURCES:
            modules = {module: _SPHINX_SOURCES[module]}
        else:
            self.stderr.write(
                self.style.ERROR(
                    f"Unknown module: {module}. Use --list to see available."
                )
            )
            return

        self.stdout.write(f"Building docs for: {', '.join(modules.keys())}")
        built, failed = 0, 0
        for name, src_path in modules.items():
            ok = self._build_one(name, src_path, clean)
            if ok:
                built += 1
            else:
                failed += 1

        self.stdout.write(
            self.style.SUCCESS(f"\nDone: {built} built, {failed} skipped/failed")
        )

    def _list_status(self):
        """List all packages and their Sphinx build status."""
        base = Path(settings.BASE_DIR)
        for name, src_path in _SPHINX_SOURCES.items():
            src = base / src_path
            build = src / "_build" / "html" / "index.html"
            has_conf = (src / "conf.py").exists()
            has_build = build.exists()
            status = "BUILT" if has_build else ("READY" if has_conf else "NO CONF")
            icon = {
                "BUILT": self.style.SUCCESS("[BUILT]"),
                "READY": self.style.WARNING("[READY]"),
                "NO CONF": self.style.ERROR("[NO CONF]"),
            }[status]
            self.stdout.write(f"  {icon} {name:<20s} {src}")

    def _build_one(self, name: str, src_path: str, clean: bool) -> bool:
        """Build Sphinx docs for a single package. Returns True on success."""
        base = Path(settings.BASE_DIR)
        src_dir = base / src_path
        conf_py = src_dir / "conf.py"

        if not src_dir.exists():
            self.stdout.write(
                self.style.WARNING(f"  SKIP {name}: source dir not found")
            )
            return False
        if not conf_py.exists():
            self.stdout.write(self.style.WARNING(f"  SKIP {name}: no conf.py"))
            return False

        build_dir = src_dir / "_build" / "html"

        if clean and build_dir.exists():
            subprocess.run(["rm", "-rf", str(build_dir)], check=True)

        self.stdout.write(f"  Building {name}...")
        try:
            result = subprocess.run(
                ["sphinx-build", "-b", "html", "-q", str(src_dir), str(build_dir)],
                capture_output=True,
                text=True,
                timeout=120,
            )
            if result.returncode == 0:
                self.stdout.write(self.style.SUCCESS(f"  OK {name} -> {build_dir}"))
                return True
            else:
                self.stdout.write(
                    self.style.ERROR(f"  FAIL {name}: {result.stderr[:200]}")
                )
                return False
        except FileNotFoundError:
            self.stdout.write(
                self.style.ERROR("sphinx-build not found. Install: pip install sphinx")
            )
            return False
        except subprocess.TimeoutExpired:
            self.stdout.write(self.style.ERROR(f"  TIMEOUT {name} (120s)"))
            return False
