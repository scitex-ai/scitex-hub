#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Vite integration for Django — dual-Vite architecture.

Host Vite (port 5173): Platform files — runs on host with native FS watching (dev only).
Container Vite (port 5174): Dev app files only — runs in container on-demand (dev + prod).
Production platform files: Uses built files from staticfiles/vite manifest.

Usage in templates:
  {% load vite %}
  {% vite_script 'console_app/workspace' %}

Note: In development, host Vite must be running (npm run dev on host).
      Container Vite starts automatically when dev apps have TypeScript files.
      In production, container Vite handles dev app TS; platform uses manifest.
"""

import json
from pathlib import Path

from django import template
from django.conf import settings
from django.utils.safestring import mark_safe

register = template.Library()

# Platform app prefixes — everything NOT in this set is a dev app
_PLATFORM_APPS = frozenset(
    {
        "console_app",
        "vis_app",
        "writer_app",
        "project_app",
        "scholar_app",
        "public_app",
        "accounts_app",
        "hub_app",
        "clew_app",
        "social_app",
        "docs_app",
        "apps_app",
        "dev_app",
        "workspace_app",
        "organizations_app",
        "discovery_app",
        "shared",
    }
)

# Cache manifest in production
_manifest_cache = None

# Cache app group lookups (workspace/ vs infra/)
_app_group_cache: dict = {}


def _find_app_ts_path(app_name: str, ts_rest: str) -> str:
    """Resolve TS path for an app, searching workspace/ and infra/ groups."""
    import os

    from django.conf import settings

    if app_name not in _app_group_cache:
        base = settings.BASE_DIR
        for group in ("workspace", "infra", ""):
            dir_path = (
                os.path.join(base, "apps", group, app_name)
                if group
                else os.path.join(base, "apps", app_name)
            )
            if os.path.isdir(dir_path):
                _app_group_cache[app_name] = group
                break
        else:
            _app_group_cache[app_name] = ""

    group = _app_group_cache[app_name]
    prefix = f"apps/{group}/" if group else "apps/"
    return f"{prefix}{app_name}/static/{app_name}/ts/{ts_rest}.ts"


def get_manifest() -> dict:
    """Load the Vite manifest file (production only)."""
    global _manifest_cache
    if _manifest_cache is not None:
        return _manifest_cache

    manifest_path = (
        Path(settings.BASE_DIR) / "staticfiles" / "vite" / ".vite" / "manifest.json"
    )
    if manifest_path.exists():
        with open(manifest_path) as f:
            _manifest_cache = json.load(f)
    else:
        _manifest_cache = {}

    return _manifest_cache


@register.simple_tag
def vite_hmr_client():
    """
    Include Vite HMR client(s).

    Dev: Host Vite (5173) + Container Vite (5174) HMR clients.
    Prod: Container Vite (5174) HMR client only (for dev apps).
    Browser silently ignores clients for servers that aren't running.
    """
    scripts = ""

    if settings.DEBUG:
        host_port = getattr(settings, "VITE_HOST_PORT", 5173)
        scripts += f'<script type="module" src="http://127.0.0.1:{host_port}/@vite/client"></script>\n'
        # Dev app Vite HMR — direct access in dev
        dev_port = getattr(settings, "VITE_DEV_APP_PORT", 5174)
        scripts += f'<script type="module" src="http://127.0.0.1:{dev_port}/@vite/client" onerror=""></script>'
    else:
        # Production: dev app Vite HMR through nginx proxy
        scripts += '<script type="module" src="/_vite_dev_app/@vite/client" onerror=""></script>'

    return mark_safe(scripts) if scripts else ""


def _is_dev_app_entry(entry_name: str) -> bool:
    """Check if entry belongs to a dev-installed app (not platform)."""
    app_prefix = entry_name.split("/")[0] if "/" in entry_name else entry_name
    return app_prefix not in _PLATFORM_APPS


@register.simple_tag
def vite_script(entry_name: str):
    """
    Load a Vite entry point script.

    Dev app entries → container Vite (port 5174) in BOTH dev and prod.
    Platform entries:
      - DEBUG=True → host Vite (port 5173)
      - DEBUG=False → Vite-built manifest

    Args:
        entry_name: Entry name like 'console_app/workspace'
    """
    # Dev app entries use container Vite — works in dev and prod
    if _is_dev_app_entry(entry_name):
        if settings.DEBUG:
            port = getattr(settings, "VITE_DEV_APP_PORT", 5174)
            return mark_safe(
                f'<script type="module" src="http://127.0.0.1:{port}/{entry_name}.ts"></script>'
            )
        else:
            # Production: through nginx proxy
            ts_path = _entry_to_ts_path(entry_name)
            return mark_safe(
                f'<script type="module" src="/_vite_dev_app/{ts_path}"></script>'
            )

    # Platform entries
    if settings.DEBUG:
        ts_path = _entry_to_ts_path(entry_name)
        port = getattr(settings, "VITE_HOST_PORT", 5173)
        return mark_safe(
            f'<script type="module" src="http://127.0.0.1:{port}/{ts_path}"></script>'
        )
    else:
        # Production: Load from Vite manifest
        manifest = get_manifest()
        ts_path = _entry_to_ts_path(entry_name)

        if ts_path in manifest:
            js_file = manifest[ts_path]["file"]
            return mark_safe(
                f'<script type="module" src="{settings.STATIC_URL}vite/{js_file}"></script>'
            )
        else:
            import logging

            logging.getLogger(__name__).error(
                f"Vite entry '{entry_name}' not found in manifest"
            )
            return ""


@register.simple_tag
def vite_legacy_script(static_path: str):
    """
    Fallback for scripts not yet migrated to Vite.
    Uses traditional Django static with build_id cache-busting.
    """
    from config.context_processors import cache_buster

    # Get build_id (pass a mock request)
    class MockRequest:
        pass

    ctx = cache_buster(MockRequest())
    build_id = ctx.get("build_id", "")

    return mark_safe(
        f'<script type="module" src="{settings.STATIC_URL}{static_path}?v={build_id}"></script>'
    )


def _entry_to_ts_path(entry_name: str) -> str:
    """Convert entry name to TypeScript file path (for Vite).

    Convention:
    - "{app}_app/{path}" -> "apps/{group}/{app}_app/static/{app}_app/ts/{path}.ts"
      where {group} is resolved via filesystem lookup (workspace/ or infra/)
    - "shared/{path}" -> "static/shared/ts/{path}.ts"

    Non-conventional explicit overrides are listed below.
    """
    # Non-conventional overrides: entries where path doesn't follow standard convention.
    # Standard convention is handled dynamically below.
    _non_conventional = {
        # workspace_app: non-standard static location (top-level static/, not apps/)
        "workspace_app/workspace-shell": "static/workspace_app/ts/workspace-shell.ts",
        # shared: entries where key name != file path under static/shared/ts/
        "shared/workspace-tree-init": "static/shared/ts/components/workspace-files-tree/auto-init.ts",
        "shared/workspace-viewer-init": "static/shared/ts/components/workspace-viewer/init.ts",
        "shared/components/workspace-files-tree": "static/shared/ts/components/workspace-files-tree/WorkspaceFilesTree.ts",
        "shared/workspace-panel-resizer": "static/shared/ts/components/workspace-panel-resizer.ts",
        "shared/collapsible-panel-click-expand": "static/shared/ts/components/collapsible-panel-click-expand.ts",
        "shared/resizer": "static/shared/ts/components/resizer/index.ts",
        "shared/repo-monitor": "static/shared/ts/components/repo-monitor/index.ts",
    }

    if entry_name in _non_conventional:
        return _non_conventional[entry_name]

    # Convention-based resolution
    parts = entry_name.split("/")
    if len(parts) >= 2:
        app_name = parts[0]
        rest = "/".join(parts[1:])

        # App-specific: search workspace/ and infra/ groups dynamically
        if app_name.endswith("_app"):
            return _find_app_ts_path(app_name, rest)

        # Shared: "shared/{path}" -> "static/shared/ts/{path}.ts"
        if app_name == "shared":
            return f"static/shared/ts/{rest}.ts"

    # Last resort
    return f"{entry_name}.ts"
