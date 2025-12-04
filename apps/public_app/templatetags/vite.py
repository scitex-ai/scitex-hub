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
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(0.5)
        result = sock.connect_ex(('127.0.0.1', port))
        sock.close()
        return result == 0
    except Exception:
        return False


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
        # Code app
        'code_app/workspace': 'apps/code_app/static/code_app/ts/workspace.ts',
        # Vis app
        'vis_app/vis-editor': 'apps/vis_app/static/vis_app/ts/vis-editor.ts',
        'vis_app/editor-inline': 'apps/vis_app/static/vis_app/ts/editor-inline.ts',
        # Writer app
        'writer_app/index': 'apps/writer_app/static/writer_app/ts/index.ts',
        'writer_app/collaboration-panel': 'apps/writer_app/static/writer_app/ts/collaboration-panel.ts',
        # Project app
        'project_app/clone_button': 'apps/project_app/static/project_app/ts/clone_button.ts',
        'project_app/create_project_type': 'apps/project_app/static/project_app/ts/create_project_type.ts',
        'project_app/init-git-gutter': 'apps/project_app/static/project_app/ts/init-git-gutter.ts',
        # Scholar app
        'scholar_app/scholar-config': 'apps/scholar_app/static/scholar_app/ts/scholar-config.ts',
        # Public app
        'public_app/visitor-status': 'apps/public_app/static/public_app/ts/visitor-status.ts',
        'public_app/server-status': 'apps/public_app/static/public_app/ts/server-status.ts',
        'public_app/landing-demos-inline': 'apps/public_app/static/public_app/ts/landing-demos-inline.ts',
        # Accounts app
        'accounts_app/profile': 'apps/accounts_app/static/accounts_app/ts/profile.ts',
        'accounts_app/account-settings': 'apps/accounts_app/static/accounts_app/ts/account-settings.ts',
        'accounts_app/ssh_keys': 'apps/accounts_app/static/accounts_app/ts/ssh_keys.ts',
        'accounts_app/remote_credentials': 'apps/accounts_app/static/accounts_app/ts/remote_credentials.ts',
        # Social app
        'social_app/explore-inline': 'apps/social_app/static/social_app/ts/explore-inline.ts',
        # Scholar app - additional
        'scholar_app/bibtex/status-tiles': 'apps/scholar_app/static/scholar_app/ts/bibtex/status-tiles.ts',
        # Project app - additional
        'project_app/projects/settings': 'apps/project_app/static/project_app/ts/projects/settings.ts',
        # Shared utilities
        'shared/utils/theme-switcher': 'static/shared/ts/utils/theme-switcher.ts',
        'shared/utils/tooltip-auto-position': 'static/shared/ts/utils/tooltip-auto-position.ts',
        'shared/utils/main': 'static/shared/ts/utils/main.ts',
        'shared/utils/dropdown': 'static/shared/ts/utils/dropdown.ts',
        'shared/utils/django-messages': 'static/shared/ts/utils/django-messages.ts',
        'shared/utils/element-inspector': 'static/shared/ts/utils/element-inspector.ts',
        'shared/code-blocks': 'static/shared/ts/code-blocks.ts',
        'shared/components/confirm-modal': 'static/shared/ts/components/confirm-modal.ts',
        'shared/components/header': 'static/shared/ts/components/header.ts',
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
