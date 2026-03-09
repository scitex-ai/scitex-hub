#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Management command to validate all workspace modules against the workspace
frame spec from docs/MASTER/01_WORKSPACE_TEMPLATE_FOR_APP_PLUGIN.md.

Usage:
    python manage.py validate_workspace_frame          # static checks only
    python manage.py validate_workspace_frame --live   # + HTTP live checks
"""

import re
from pathlib import Path

from django.core.management.base import BaseCommand

BASE_DIR = Path(__file__).resolve().parents[4]
PROTECTED_SELECTORS = [".workspace-sidebar", ".sidebar-header", ".panel-resizer"]
REQUIRED_IDS = [
    "workspace-three-col",
    "ws-ai-pane",
    "ws-worktree-sidebar",
    "ws-viewer-sidebar",
    "ws-apps-sidebar",
    "main-content",
]


class Command(BaseCommand):
    help = "Validate all workspace modules against the frame spec"

    def add_arguments(self, parser):
        parser.add_argument(
            "--live",
            action="store_true",
            help="Also run HTTP checks against a running server",
        )
        parser.add_argument(
            "--base-url",
            default="http://127.0.0.1:8000",
            help="Base URL for live checks (default: http://127.0.0.1:8000)",
        )

    def handle(self, *args, **options):
        from apps.infra.workspace_app.registry import get_all_modules

        modules = get_all_modules()
        passed = failed = 0
        self.stdout.write("\n=== Workspace Frame Validation ===\n")

        for mod in modules:
            p, f = self._check_module(mod, options["live"], options["base_url"])
            passed += p
            failed += f

        total = passed + failed
        summary = f"\nSummary: {passed}/{total} passed, {failed} failed"
        style = self.style.SUCCESS if not failed else self.style.ERROR
        self.stdout.write(style(summary))

    # ------------------------------------------------------------------
    # Per-module dispatch
    # ------------------------------------------------------------------
    def _check_module(self, mod, live, base_url):
        passed = failed = 0

        def record(ok, label):
            nonlocal passed, failed
            if ok:
                passed += 1
                self.stdout.write(self.style.SUCCESS(f"[PASS] {mod.name}: {label}"))
            else:
                failed += 1
                self.stdout.write(self.style.ERROR(f"[FAIL] {mod.name}: {label}"))

        # --- template checks ---
        tmpl = self._find_template(mod)
        if tmpl:
            record(
                self._walk_chain(tmpl, _chain_extends_global),
                "extends global_base.html",
            )
            record(
                not self._walk_chain(tmpl, _chain_has_worktree_block),
                "no workspace_worktree_pane override",
            )
            record(
                self._walk_chain(tmpl, _chain_has_content_block),
                "has {% block content %}",
            )
        else:
            for label in (
                "extends global_base.html",
                "no workspace_worktree_pane override",
                "has {% block content %}",
            ):
                failed += 1
                self.stdout.write(
                    self.style.ERROR(f"[FAIL] {mod.name}: {label} (template not found)")
                )

        # --- CSS checks ---
        css_issues = self._check_css(mod)
        if css_issues:
            for issue in css_issues:
                failed += 1
                self.stdout.write(self.style.ERROR(f"[FAIL] {mod.name}: {issue}"))
        else:
            passed += 1
            self.stdout.write(
                self.style.SUCCESS(
                    f"[PASS] {mod.name}: CSS clean (no frame element overrides)"
                )
            )

        # --- live HTTP checks ---
        if live:
            lp, lf = self._live_checks(mod, base_url)
            passed += lp
            failed += lf

        return passed, failed

    # ------------------------------------------------------------------
    # Template helpers
    # ------------------------------------------------------------------
    def _find_template(self, mod):
        """Return Path to the module's primary (non-partial) HTML template."""
        tmpl_dir = BASE_DIR / "apps" / mod.app_name / "templates" / mod.app_name
        if not tmpl_dir.exists():
            return None
        for name in [
            "index.html",
            f"{mod.name}.html",
            f"{mod.name}_base.html",
            f"{mod.name}_unified.html",
        ]:
            p = tmpl_dir / name
            if p.exists():
                return p
        for p in sorted(tmpl_dir.glob("*.html")):
            if "partial" not in p.name:
                return p
        return None

    def _walk_chain(self, start: Path, predicate) -> bool:
        """Walk template extends chain; return predicate result (stops at global_base)."""
        visited: set = set()
        path = start
        while path and path not in visited and path.exists():
            visited.add(path)
            try:
                text = path.read_text(errors="replace")
            except OSError:
                return False
            result = predicate(text)
            if result is not None:
                return result
            m = re.search(r'\{%[-\s]*extends\s+["\']([^"\']+)["\']', text)
            if not m:
                return False
            parent = m.group(1)
            if parent == "global_base.html":
                return predicate.__name__ == "_chain_extends_global"
            parent_path = path.parent / parent
            if not parent_path.exists():
                for candidate in BASE_DIR.rglob(parent):
                    if "templates" in str(candidate):
                        parent_path = candidate
                        break
            path = parent_path
        return False

    # ------------------------------------------------------------------
    # CSS helpers
    # ------------------------------------------------------------------
    def _check_css(self, mod):
        """Return list of violation strings; empty list means clean."""
        css_dir = BASE_DIR / "apps" / mod.app_name / "static" / mod.app_name / "css"
        if not css_dir.exists():
            return []
        issues = []
        for css_file in sorted(css_dir.glob("*.css")):
            fname = css_file.name
            try:
                text = css_file.read_text(errors="replace")
            except OSError:
                continue
            if re.search(r"sidebar-title[^{]*\{[^}]*font-size", text, re.S):
                issues.append(f"CSS contains sidebar-title font-size in {fname}")
            if re.search(r"footer[^{]*\{[^}]*display\s*:\s*none", text, re.S):
                issues.append(f"CSS contains footer {{ display: none }} in {fname}")
            for sel in PROTECTED_SELECTORS:
                if re.search(re.escape(sel) + r"[^{]*\{[^}]*!important", text, re.S):
                    issues.append(f"CSS uses !important on {sel} in {fname}")
        return issues

    # ------------------------------------------------------------------
    # Live HTTP checks
    # ------------------------------------------------------------------
    def _live_checks(self, mod, base_url):
        try:
            import requests
        except ImportError:
            self.stdout.write(
                self.style.WARNING(
                    f"[SKIP] {mod.name}: live checks require 'requests' package"
                )
            )
            return 0, 0

        url = f"{base_url.rstrip('/')}/{mod.name}/"
        passed = failed = 0

        def record(ok, label):
            nonlocal passed, failed
            if ok:
                passed += 1
                self.stdout.write(self.style.SUCCESS(f"[PASS] {mod.name}: {label}"))
            else:
                failed += 1
                self.stdout.write(self.style.ERROR(f"[FAIL] {mod.name}: {label}"))

        try:
            resp = requests.get(url, timeout=10, allow_redirects=True)
        except Exception as exc:
            failed += 1
            self.stdout.write(self.style.ERROR(f"[FAIL] {mod.name}: GET {url} — {exc}"))
            return passed, failed

        record(resp.status_code == 200, f"HTTP 200 at {url}")
        html = resp.text

        for elem_id in REQUIRED_IDS:
            record(f'id="{elem_id}"' in html, f"#{elem_id} present in HTML")

        no_zero = not re.search(
            r'class="[^"]*sidebar-title[^"]*"[^>]*style="[^"]*font-size\s*:\s*0', html
        )
        record(no_zero, "no font-size:0 on .sidebar-title inline style")

        return passed, failed


# ------------------------------------------------------------------
# Chain predicate functions (used by _walk_chain)
# Returns True/False to stop walking, or None to continue up the chain.
# ------------------------------------------------------------------
def _chain_extends_global(text: str):
    """Signal found when global_base.html is reached (handled by _walk_chain)."""
    return None  # keep walking; termination handled in _walk_chain


def _chain_has_worktree_block(text: str):
    if re.search(r"\{%[-\s]*block\s+workspace_worktree_pane", text):
        return True  # violation found — stop
    return None  # keep walking


def _chain_has_content_block(text: str):
    if re.search(r"\{%[-\s]*block\s+content[\s%-]", text):
        return True  # found — stop
    return None  # keep walking


# EOF
