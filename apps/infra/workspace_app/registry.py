#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Workspace Module Registry — single source of truth for all workspace modules.

Every workspace module (Writer, Scholar, Hub, etc.) registers here.
Templates, views, TypeScript, and validation all reference this registry
instead of maintaining separate hardcoded lists.

Usage:
    from apps.infra.workspace_app.registry import get_module, get_all_modules, is_workspace_path
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
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
    accent_color: str = ""  # Module accent identifier (maps to CSS --module-accent-X)

    # Documentation
    docs_slug: str = ""  # Slug for auto-registering docs page (e.g. "clew")

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
# Clew SVG icons (custom — not FontAwesome)
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


# ---------------------------------------------------------------------------
# Module Registry — all workspace modules declared here
# ---------------------------------------------------------------------------
_BUILTIN_MODULES: list[ModuleConfig] = [
    ModuleConfig(
        name="writer",
        label="Writer",
        app_name="writer_app",
        icon_fa="fas fa-pen",
        partial_template="writer_app/writer_partial.html",
        context_builder="apps.workspace.writer_app.views.index.main.build_writer_context",
        body_class="writer-page",
        keyboard_shortcut="W",
        order=20,
        ai_hint="Scientific manuscript editor: LaTeX editing with live preview, figure/table management, bibliography, PDF compilation.",
        accent_color="writer",
        allowed_extensions=[
            ".tex",
            ".bib",
            ".pdf",
            ".png",
            ".jpg",
            ".jpeg",
            ".svg",
            ".eps",
        ],
        hidden_patterns=[
            "__pycache__",
            "node_modules",
            ".git",
            ".venv",
            "build",
            ".aux",
            ".log",
            ".out",
        ],
    ),
    ModuleConfig(
        name="scholar",
        label="Scholar",
        app_name="scholar_app",
        icon_fa="fas fa-graduation-cap",
        partial_template="scholar_app/scholar_partial.html",
        body_class="scholar-page",
        keyboard_shortcut="S",
        order=30,
        ai_hint="Literature management: search papers (CrossRef/OpenAlex/Semantic Scholar), manage bibliography, explore citation graphs, download PDFs.",
        accent_color="scholar",
        allowed_extensions=[".bib"],
        hidden_patterns=["__pycache__", "node_modules", ".git", ".venv", "build"],
    ),
    ModuleConfig(
        name="vis",
        label="Vis",
        app_name="vis_app",
        icon_fa="fas fa-chart-line",
        partial_template="vis_app/vis_partial.html",
        body_class="vis-workspace",
        keyboard_shortcut="V",
        order=40,
        ai_hint="Data visualization and figure management: view plots, manage figure recipes, export publication-ready figures.",
        accent_color="visualizer",
        allowed_extensions=[
            ".png",
            ".jpg",
            ".jpeg",
            ".svg",
            ".pdf",
            ".csv",
            ".json",
            ".xlsx",
            ".tsv",
        ],
        hidden_patterns=["__pycache__", "node_modules", ".git", ".venv"],
    ),
    ModuleConfig(
        name="clew",
        label="Clew",
        app_name="clew_app",
        icon_svg_tab=_CLEW_SVG_TAB,
        icon_svg_nav=_CLEW_SVG_NAV,
        partial_template="clew_app/index_partial.html",
        body_class="clew-page",
        keyboard_shortcut="R",
        order=50,  # hidden (default_enabled=False)
        default_enabled=False,
        ai_hint="Verification system: trace manuscript claims (statistics, figures, tables) back through computational chains to source data.",
        docs_slug="clew",
        accent_color="clew",
        hidden_patterns=["__pycache__", "node_modules", ".git", ".venv"],
    ),
    ModuleConfig(
        name="hub",
        label="Home",
        app_name="hub_app",
        icon_fa="fas fa-home",
        partial_template="hub_app/index_partial.html",
        context_builder="apps.workspace.hub_app.views.index.build_hub_context",
        body_class="hub-page",
        keyboard_shortcut="H",
        order=10,
        url="/hub/",
        ai_hint="User dashboard: profile, projects, and current project workspace.",
        accent_color="hub",
        hidden_patterns=["__pycache__", "node_modules", ".git", ".venv"],
    ),
    ModuleConfig(
        name="tools",
        label="Tools",
        app_name="public_app",
        icon_fa="fas fa-tools",
        partial_template="public_app/pages/tools_partial.html",
        context_builder="apps.infra.public_app.views.tools_views.build_tools_context",
        body_class="tools-page",
        keyboard_shortcut="T",
        order=60,
        url="/tools/",
        ai_hint="Shared utilities and tools for project management.",
        hidden_patterns=["__pycache__", "node_modules", ".git", ".venv"],
    ),
    ModuleConfig(
        name="apps",
        label="Apps",
        app_name="apps_app",
        icon_fa="fas fa-store",
        partial_template="apps_app/browse_partial.html",
        context_builder="apps.workspace.apps_app.views.build_apps_context",
        body_class="apps-page",
        keyboard_shortcut="M",
        order=90,
        url="/apps/",
        ai_hint="Browse, install, and publish community modules.",
        hidden_patterns=["__pycache__", "node_modules", ".git", ".venv"],
    ),
    ModuleConfig(
        name="docs",
        label="Docs",
        app_name="docs_app",
        icon_fa="fas fa-book",
        partial_template="docs_app/docs_partial.html",
        context_builder="apps.workspace.docs_app.views.build_docs_context",
        body_class="docs-page",
        keyboard_shortcut="D",
        order=100,
        url="/docs/",
        ai_hint="Documentation: Python packages, MCP tools, SSH access, API reference, self-hosting guide, licensing.",
        accent_color="docs",
        hidden_patterns=["__pycache__", "node_modules", ".git", ".venv"],
    ),
    ModuleConfig(
        name="figrecipe",
        label="Figrecipe",
        app_name="figrecipe_editor",
        icon_fa="fas fa-palette",
        partial_template="vis_app/vis_partial.html",
        body_class="figrecipe-page",
        keyboard_shortcut="F",
        order=45,
        ai_hint="Interactive figure editor: create and edit publication-ready matplotlib plots with drag-and-drop layout, statistical annotations, and multi-panel composition.",
        accent_color="figrecipe",
        license="AGPL-3.0",
        allowed_extensions=[".py", ".csv", ".json", ".yaml", ".figz", ".pltz"],
        hidden_patterns=["__pycache__", "node_modules", ".git", ".venv"],
    ),
    ModuleConfig(
        name="discovery",
        label="Discovery",
        app_name="discovery_app",
        icon_fa="fas fa-compass",
        partial_template="discovery_app/discovery_partial.html",
        context_builder="apps.workspace.discovery_app.views.build_discovery_context",
        body_class="discovery-page",
        keyboard_shortcut="X",
        order=15,
        url="/discovery/",
        ai_hint="Discover public repositories, researchers, and organizations.",
        accent_color="hub",
        hidden_patterns=["__pycache__", "node_modules", ".git", ".venv"],
    ),
]

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
    # Root path "/" is the hub dashboard for authenticated users
    if path == "/":
        return True
    for name in _registry_by_name:
        if f"/{name}/" in path:
            return True
    for prefix in _WORKSPACE_EXTRA_PREFIXES:
        if path.startswith(prefix):
            return True
    return False


def extract_module_from_path(path: str) -> Optional[str]:
    """Extract module name from URL path. Returns None if not a module path."""
    # Root path "/" maps to hub module
    if path == "/":
        return "hub"
    for name in _registry_by_name:
        if f"/{name}/" in path:
            return name
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
