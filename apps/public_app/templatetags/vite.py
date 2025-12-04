#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Vite integration for Django.

In development: Serves JS from Vite dev server with HMR
In production: Uses built files from staticfiles/vite

Usage in templates:
  {% load vite %}
  {% vite_script 'code_app/workspace' %}
"""

import json
import socket
from pathlib import Path
from django import template
from django.conf import settings
from django.utils.safestring import mark_safe

register = template.Library()

# Cache manifest in production
_manifest_cache = None


def is_vite_server_running(port: int = 5173) -> bool:
    """Check if Vite dev server is running and responsive."""
    if not settings.DEBUG:
        return False

    # Disable Vite HMR - current codebase uses .js imports which causes
    # Vite to load pre-compiled JS files (slow, sourcemap warnings).
    # TODO: Enable when imports are changed to .ts extensions
    return False

    # try:
    #     sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    #     sock.settimeout(0.5)
    #     result = sock.connect_ex(('127.0.0.1', port))
    #     sock.close()
    #     return result == 0
    # except Exception:
    #     return False


def get_manifest() -> dict:
    """Load the Vite manifest file (production only)."""
    global _manifest_cache
    if _manifest_cache is not None:
        return _manifest_cache

    manifest_path = Path(settings.BASE_DIR) / 'staticfiles' / 'vite' / '.vite' / 'manifest.json'
    if manifest_path.exists():
        with open(manifest_path) as f:
            _manifest_cache = json.load(f)
    else:
        _manifest_cache = {}

    return _manifest_cache


@register.simple_tag
def vite_hmr_client():
    """
    Include Vite HMR client in development.
    Returns empty string in production.
    """
    if is_vite_server_running():
        return mark_safe(
            '<script type="module" src="http://127.0.0.1:5173/@vite/client"></script>'
        )
    return ''


@register.simple_tag
def vite_script(entry_name: str):
    """
    Load a Vite entry point script.

    In development with Vite: Load from Vite dev server (HMR)
    In development without Vite: Load from tsc-compiled JS files
    In production: Load from Vite-built manifest

    Args:
        entry_name: Entry name like 'code_app/workspace'
    """
    if is_vite_server_running():
        # Development with Vite: Load from Vite server (HMR enabled)
        ts_path = _entry_to_ts_path(entry_name)
        return mark_safe(
            f'<script type="module" src="http://127.0.0.1:5173/{ts_path}"></script>'
        )
    else:
        # Check Vite manifest first (production)
        manifest = get_manifest()
        ts_path = _entry_to_ts_path(entry_name)

        if ts_path in manifest:
            js_file = manifest[ts_path]['file']
            return mark_safe(
                f'<script type="module" src="{settings.STATIC_URL}vite/{js_file}"></script>'
            )
        else:
            # Fallback: Load from tsc-compiled JS files (development without Vite)
            js_path = _entry_to_js_path(entry_name)
            return mark_safe(
                f'<script type="module" src="{settings.STATIC_URL}{js_path}"></script>'
            )


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
    build_id = ctx.get('build_id', '')

    return mark_safe(
        f'<script type="module" src="{settings.STATIC_URL}{static_path}?v={build_id}"></script>'
    )


def _entry_to_ts_path(entry_name: str) -> str:
    """Convert entry name to TypeScript file path (for Vite)."""
    # Map entry names to actual TS file locations
    mappings = {
        'code_app/workspace': 'apps/code_app/static/code_app/ts/workspace.ts',
        'vis_app/vis-editor': 'apps/vis_app/static/vis_app/ts/vis-editor.ts',
        'vis_app/editor-inline': 'apps/vis_app/static/vis_app/ts/editor-inline.ts',
        'shared/utils/theme-switcher': 'static/shared/ts/utils/theme-switcher.ts',
        'shared/utils/element-inspector': 'static/shared/ts/utils/element-inspector.ts',
        'shared/components/confirm-modal': 'static/shared/ts/components/confirm-modal.ts',
    }
    return mappings.get(entry_name, f'{entry_name}.ts')


def _entry_to_js_path(entry_name: str) -> str:
    """Convert entry name to compiled JS path (for tsc fallback)."""
    # Map entry names to compiled JS file locations
    mappings = {
        'code_app/workspace': 'code_app/js/workspace.js',
        'vis_app/vis-editor': 'vis_app/js/vis-editor.js',
        'vis_app/editor-inline': 'vis_app/js/editor-inline.js',
        'shared/utils/theme-switcher': 'shared/js/utils/theme-switcher.js',
        'shared/utils/element-inspector': 'shared/js/utils/element-inspector.js',
        'shared/components/confirm-modal': 'shared/js/components/confirm-modal.js',
    }
    return mappings.get(entry_name, f'{entry_name}.js')
