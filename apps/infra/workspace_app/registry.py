#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Workspace Module Registry — single source of truth for all workspace modules.

Every workspace module (Writer, Scholar, Hub, etc.) registers here.
Module configuration is loaded from manifest.json files in each app directory.
Templates, views, TypeScript, and validation all reference this registry
instead of maintaining separate hardcoded lists.

Usage:
    from apps.infra.workspace_app.registry import get_module, get_all_modules, is_workspace_path
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


@dataclass
class ModuleConfig:
    """Configuration for a workspace module."""

    # Identity
    name: str  # URL slug, e.g. "writer"
    label: str  # Display label, e.g. "Writer"
    app_name: str  # Django app name, e.g. "writer_app"

    # Icon (one of icon_fa or icon_svg_tab/icon_svg_nav)
    icon_fa: str = ""  # Full FontAwesome class, e.g. "fas fa-pen"
    icon_svg_tab: str = ""  # Custom SVG for tab bar
    icon_svg_nav: str = ""  # Custom SVG for nav bar

    # Templates
    partial_template: str = ""  # e.g. "writer_app/writer_partial.html"

    # Context builder (dotted path or callable)
    context_builder: str = (
        ""  # e.g. "apps.workspace.writer_app.views.index.main.build_writer_context"
    )

    # Layout / tracking
    body_class: str = ""  # e.g. "writer-page"
    track_module: str = ""  # Analytics tracking name (defaults to name)
    keyboard_shortcut: str = ""  # Alt+X shortcut key

    # Sort order in tab bar (lower = leftmost)
    order: int = 50

    # Visibility defaults
    default_enabled: bool = True  # Show in tab bar for new users (no installations)

    # Runtime state (set by context processor, not persisted)
    is_active: bool = False
    is_dev: bool = False  # True for private (non-published) apps
    status: str = ""  # Module status: stable, wip, beta, deprecated

    # LLM integration
    ai_hint: str = ""  # Short description for data-ai-hint (shown to LLM)
    accent_color: str = ""  # Module accent identifier (maps to CSS --app-accent-X)

    # Documentation
    docs_slug: str = ""  # Slug for auto-registering docs page (e.g. "clew")

    # Privileges — declared capabilities with reasons (security, resources)
    privileges: list = field(default_factory=list)

    # Legal
    license: str = "AGPL-3.0"  # SPDX identifier, default matches SciTeX project license

    # URL override — empty means default to /apps/{name}/
    url: str = ""  # e.g. "/hub/" for top-level exceptions

    # File tree configuration
    tree_mode: str = ""  # WorkspaceMode in types.ts (defaults to name)
    allowed_extensions: list = field(default_factory=list)
    hidden_patterns: list = field(
        default_factory=lambda: ["__pycache__", "node_modules", ".git", ".venv"]
    )

    def get_track_module(self) -> str:
        return self.track_module or self.name

    def get_url(self) -> str:
        """Return the navigation URL for this module."""
        if self.url:
            return self.url
        return f"/apps/{self.name}/"

    def get_tree_mode(self) -> str:
        return self.tree_mode or self.name

    def build_context(self, request, current_project=None) -> dict[str, Any]:
        """Build template context using the registered context builder."""
        if not self.context_builder:
            return {"current_project": current_project}
        builder = _import_builder(self.context_builder)
        if builder:
            return builder(request, current_project)
        return {"current_project": current_project}


def _import_builder(dotted_path: str) -> Optional[Callable]:
    """Import a context builder function from a dotted path."""
    try:
        from django.utils.module_loading import import_string

        return import_string(dotted_path)
    except ImportError as e:
        logger.warning(f"[registry] Cannot import context builder '{dotted_path}': {e}")
        return None


# ---------------------------------------------------------------------------
# Clew SVG icons (custom — not in JSON, defined here)
# ---------------------------------------------------------------------------
_CLEW_SVG_NAV = (
    '<svg class="nav-icon-svg" viewBox="0 0 100 100" fill="none" '
    'xmlns="http://www.w3.org/2000/svg" width="20" height="20">'
    '<circle cx="50" cy="50" r="40" stroke="currentColor" stroke-width="5"/>'
    '<line x1="10" y1="50" x2="90" y2="50" stroke="currentColor" stroke-width="4.5"/>'
    '<line x1="13" y1="35" x2="87" y2="35" stroke="currentColor" stroke-width="4"/>'
    '<line x1="13" y1="65" x2="87" y2="65" stroke="currentColor" stroke-width="4"/>'
    '<path d="M30 12 Q70 30 70 50 Q70 70 30 88" stroke="currentColor" stroke-width="4" fill="none"/>'
    '<path d="M70 12 Q30 30 30 50 Q30 70 70 88" stroke="currentColor" stroke-width="4" fill="none"/>'
    '<line x1="85" y1="82" x2="95" y2="95" stroke="currentColor" stroke-width="4.5" stroke-linecap="round"/>'
    "</svg>"
)

_CLEW_SVG_TAB = (
    '<svg class="tab-icon-svg" viewBox="0 0 100 100" fill="none" '
    'xmlns="http://www.w3.org/2000/svg" width="16" height="16" style="flex-shrink:0">'
    '<circle cx="50" cy="50" r="40" stroke="currentColor" stroke-width="5"/>'
    '<line x1="10" y1="50" x2="90" y2="50" stroke="currentColor" stroke-width="4.5"/>'
    '<line x1="13" y1="35" x2="87" y2="35" stroke="currentColor" stroke-width="4"/>'
    '<line x1="13" y1="65" x2="87" y2="65" stroke="currentColor" stroke-width="4"/>'
    '<path d="M30 12 Q70 30 70 50 Q70 70 30 88" stroke="currentColor" stroke-width="4" fill="none"/>'
    '<path d="M70 12 Q30 30 30 50 Q30 70 70 88" stroke="currentColor" stroke-width="4" fill="none"/>'
    '<line x1="85" y1="82" x2="95" y2="95" stroke="currentColor" stroke-width="4.5" stroke-linecap="round"/>'
    "</svg>"
)

# Per-module overrides that cannot be expressed in JSON (e.g. SVG icons)
_MANIFEST_OVERRIDES: dict[str, dict] = {
    "clew": {"icon_svg_tab": _CLEW_SVG_TAB, "icon_svg_nav": _CLEW_SVG_NAV},
}


# ---------------------------------------------------------------------------
# Manifest loading — build ModuleConfig from manifest.json files
# ---------------------------------------------------------------------------
_APPS_ROOT = Path(__file__).resolve().parent.parent.parent  # project root / apps/

# (manifest_path_relative_to_apps_root, )
_BUILTIN_MANIFEST_PATHS: list[str] = [
    "workspace/hub_app/manifest.json",
    "workspace/writer_app/manifest.json",
    "workspace/scholar_app/manifest.json",
    "workspace/figrecipe_app/manifest.json",
    "workspace/clew_app/manifest.json",
    "infra/public_app/manifest.json",
    "workspace/discovery_app/manifest.json",
    "workspace/docs_app/manifest.json",
    "workspace/apps_app/manifest.json",
]


_SUPPORTED_SCHEMA_VERSIONS = {"1.0.0", "2.0.0"}


def _load_manifest(manifest_path: Path) -> dict:
    """Load and validate a manifest.json file."""
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    schema_ver = data.get("$schema_version", "1.0.0")
    if schema_ver not in _SUPPORTED_SCHEMA_VERSIONS:
        raise ValueError(
            f"Unsupported manifest schema version: {schema_ver} in {manifest_path}"
        )
    return data


def _manifest_to_module_config(data: dict) -> ModuleConfig:
    """Convert a manifest dict to a ModuleConfig dataclass."""
    name = data["name"]
    overrides = _MANIFEST_OVERRIDES.get(name, {})

    return ModuleConfig(
        name=name,
        label=data["label"],
        app_name=data["app_name"],
        icon_fa=data.get("icon", ""),
        icon_svg_tab=overrides.get("icon_svg_tab", ""),
        icon_svg_nav=overrides.get("icon_svg_nav", ""),
        partial_template=data.get("partial_template", ""),
        context_builder=data.get("context_builder", ""),
        body_class=data.get("body_class", ""),
        keyboard_shortcut=data.get("keyboard_shortcut", ""),
        order=data.get("order", 50),
        default_enabled=data.get("default_enabled", True),
        ai_hint=data.get("ai_hint", ""),
        accent_color=data.get("accent_color", ""),
        docs_slug=data.get("docs_slug", ""),
        license=data.get("license", "AGPL-3.0"),
        url=data.get("url", ""),
        privileges=data.get("privileges", []),
        allowed_extensions=data.get("allowed_extensions", []),
        hidden_patterns=data.get(
            "hidden_patterns",
            ["__pycache__", "node_modules", ".git", ".venv"],
        ),
    )


def _build_builtin_modules() -> list[ModuleConfig]:
    """Build the builtin modules list from manifest.json files."""
    modules = []
    for rel_path in _BUILTIN_MANIFEST_PATHS:
        manifest_path = _APPS_ROOT / rel_path
        try:
            data = _load_manifest(manifest_path)
            modules.append(_manifest_to_module_config(data))
        except Exception as e:
            logger.error("[registry] Failed to load manifest %s: %s", manifest_path, e)
    return modules


# ---------------------------------------------------------------------------
# Module Registry — loaded from manifest.json files
# ---------------------------------------------------------------------------
_BUILTIN_MODULES: list[ModuleConfig] = _build_builtin_modules()

# Mutable list: built-ins + external modules added at startup
_registry: list[ModuleConfig] = list(_BUILTIN_MODULES)
_registry_by_name: dict[str, ModuleConfig] = {m.name: m for m in _registry}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def get_module(name: str) -> Optional[ModuleConfig]:
    """Get a module config by name. Returns None if not found."""
    return _registry_by_name.get(name)


def get_all_modules() -> list[ModuleConfig]:
    """Get all registered modules sorted by order."""
    return sorted(_registry, key=lambda m: m.order)


def get_module_names() -> set[str]:
    """Get the set of all registered module names."""
    return set(_registry_by_name.keys())


# Non-module paths that should still render inside the workspace layout.
_WORKSPACE_EXTRA_PREFIXES = ("/accounts/",)


def is_workspace_path(path: str) -> bool:
    """Check if a URL path belongs to a workspace module or extra workspace page."""
    if path == "/":
        return True
    for mod in sorted(_registry, key=lambda m: len(m.url or ""), reverse=True):
        if mod.url and path.startswith(mod.url):
            return True
    for prefix in _WORKSPACE_EXTRA_PREFIXES:
        if path.startswith(prefix):
            return True
    return False


def extract_module_from_path(path: str) -> Optional[str]:
    """Extract module name from URL path. Returns None if not a module path."""
    if path == "/":
        return "home"
    for mod in sorted(_registry, key=lambda m: len(m.url or ""), reverse=True):
        if mod.url and path.startswith(mod.url):
            return mod.name
    return None


def register_module(config: ModuleConfig) -> None:
    """Register an external module at runtime."""
    if config.name in _registry_by_name:
        logger.warning(
            f"[registry] Module '{config.name}' already registered, skipping."
        )
        return
    _registry.append(config)
    _registry_by_name[config.name] = config
    logger.info(f"[registry] Registered external module: {config.name}")


def discover_external_modules() -> None:
    """Discover and register modules from pip-installed packages."""
    try:
        from importlib.metadata import entry_points

        eps = entry_points(group="scitex_modules")
        for ep in eps:
            try:
                config = ep.load()
                if isinstance(config, ModuleConfig):
                    register_module(config)
                else:
                    logger.warning(
                        f"[registry] Entry point '{ep.name}' did not return ModuleConfig"
                    )
            except Exception as e:
                logger.warning(f"[registry] Failed to load module '{ep.name}': {e}")
    except Exception:
        pass  # importlib.metadata not available or no entry points


# ---------------------------------------------------------------------------
# ModuleTestMixin — re-exported for backwards compatibility
# ---------------------------------------------------------------------------
from apps.infra.workspace_app.test_mixin import ModuleTestMixin  # noqa: F401

# Run external module discovery at import time
discover_external_modules()


# EOF
