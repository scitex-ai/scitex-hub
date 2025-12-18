#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Vite integration for Django.

In development (DEBUG=True): Serves JS from Vite dev server with HMR
In production (DEBUG=False): Uses built files from staticfiles/vite manifest

Usage in templates:
  {% load vite %}
  {% vite_script 'code_app/workspace' %}

Note: In development, Vite dev server must be running (npm run dev).
      No fallback to tsc-compiled JS - keeps the system simple and predictable.
"""

import json
from pathlib import Path
from django import template
from django.conf import settings
from django.utils.safestring import mark_safe

register = template.Library()

# Cache manifest in production
_manifest_cache = None


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
    if settings.DEBUG:
        return mark_safe(
            '<script type="module" src="http://127.0.0.1:5173/@vite/client"></script>'
        )
    return ''


@register.simple_tag
def vite_script(entry_name: str):
    """
    Load a Vite entry point script.

    In development (DEBUG=True): Load from Vite dev server (HMR)
    In production (DEBUG=False): Load from Vite-built manifest

    Args:
        entry_name: Entry name like 'code_app/workspace'
    """
    if settings.DEBUG:
        # Development: Load from Vite dev server (HMR enabled)
        ts_path = _entry_to_ts_path(entry_name)
        return mark_safe(
            f'<script type="module" src="http://127.0.0.1:5173/{ts_path}"></script>'
        )
    else:
        # Production: Load from Vite manifest
        manifest = get_manifest()
        ts_path = _entry_to_ts_path(entry_name)

        if ts_path in manifest:
            js_file = manifest[ts_path]['file']
            return mark_safe(
                f'<script type="module" src="{settings.STATIC_URL}vite/{js_file}"></script>'
            )
        else:
            # Entry not in manifest - log error in production
            import logging
            logging.getLogger(__name__).error(f"Vite entry '{entry_name}' not found in manifest")
            return ''


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
        'writer_app/modules/ai2-prompt': 'apps/writer_app/static/writer_app/ts/modules/ai2-prompt.ts',
        'writer_app/arxiv/submission': 'apps/writer_app/static/writer_app/ts/arxiv/submission.ts',
        'writer_app/collaboration/session': 'apps/writer_app/static/writer_app/ts/collaboration/session.ts',
        'writer_app/version_control/index': 'apps/writer_app/static/writer_app/ts/version_control/index.ts',
        'writer_app/compilation/compilation': 'apps/writer_app/static/writer_app/ts/compilation/compilation.ts',
        'writer_app/shared/utils': 'apps/writer_app/static/writer_app/ts/shared/utils.ts',
        'writer_app/editor/preview-panel/index': 'apps/writer_app/static/writer_app/ts/editor/preview-panel/index.ts',
        'writer_app/editor/collaborative/index': 'apps/writer_app/static/writer_app/ts/editor/collaborative/index.ts',
        # Project app
        'project_app/clone_button': 'apps/project_app/static/project_app/ts/clone_button.ts',
        'project_app/create_project_type': 'apps/project_app/static/project_app/ts/create_project_type.ts',
        'project_app/init-git-gutter': 'apps/project_app/static/project_app/ts/init-git-gutter.ts',
        'project_app/shared/project_app': 'apps/project_app/static/project_app/ts/shared/project_app.ts',
        'project_app/shared/file-tree': 'apps/project_app/static/project_app/ts/shared/file-tree.ts',
        'project_app/shared/pdf_viewer': 'apps/project_app/static/project_app/ts/shared/pdf_viewer.ts',
        'project_app/projects/create': 'apps/project_app/static/project_app/ts/projects/create.ts',
        'project_app/projects/delete_confirmation': 'apps/project_app/static/project_app/ts/projects/delete_confirmation.ts',
        'project_app/projects/settings_collaborators': 'apps/project_app/static/project_app/ts/projects/settings_collaborators.ts',
        'project_app/repository/browse': 'apps/project_app/static/project_app/ts/repository/browse.ts',
        'project_app/repository/browse_toolbar': 'apps/project_app/static/project_app/ts/repository/browse_toolbar.ts',
        'project_app/repository/colorful-icons': 'apps/project_app/static/project_app/ts/repository/colorful-icons.ts',
        'project_app/repository/file_browser_git_status': 'apps/project_app/static/project_app/ts/repository/file_browser_git_status.ts',
        'project_app/repository/file_view': 'apps/project_app/static/project_app/ts/repository/file_view.ts',
        'project_app/repository/file_edit': 'apps/project_app/static/project_app/ts/repository/file_edit.ts',
        'project_app/repository/file_history': 'apps/project_app/static/project_app/ts/repository/file_history.ts',
        'project_app/repository/admin/index': 'apps/project_app/static/project_app/ts/repository/admin/index.ts',
        'project_app/components/DiffMerge/index': 'apps/project_app/static/project_app/ts/components/DiffMerge/index.ts',
        'project_app/issues/detail': 'apps/project_app/static/project_app/ts/issues/detail.ts',
        'project_app/projects/detail': 'apps/project_app/static/project_app/ts/projects/detail.ts',
        'project_app/pull_requests/conversation': 'apps/project_app/static/project_app/ts/pull_requests/conversation.ts',
        'project_app/pull_requests/detail': 'apps/project_app/static/project_app/ts/pull_requests/detail.ts',
        'project_app/pull_requests/form': 'apps/project_app/static/project_app/ts/pull_requests/form.ts',
        'project_app/security/scan': 'apps/project_app/static/project_app/ts/security/scan.ts',
        'project_app/security/alert_detail': 'apps/project_app/static/project_app/ts/security/alert_detail.ts',
        'project_app/users/profile': 'apps/project_app/static/project_app/ts/users/profile.ts',
        'project_app/workflows/detail': 'apps/project_app/static/project_app/ts/workflows/detail.ts',
        'project_app/workflows/editor': 'apps/project_app/static/project_app/ts/workflows/editor.ts',
        'project_app/workflows/run_detail': 'apps/project_app/static/project_app/ts/workflows/run_detail.ts',
        # Scholar app
        'scholar_app/scholar-config': 'apps/scholar_app/static/scholar_app/ts/scholar-config.ts',
        # Public app
        'public_app/visitor-status': 'apps/public_app/static/public_app/ts/visitor-status.ts',
        'public_app/server-status': 'apps/public_app/static/public_app/ts/server-status.ts',
        'public_app/landing-demos-inline': 'apps/public_app/static/public_app/ts/landing-demos-inline.ts',
        'public_app/landing/module-cards': 'apps/public_app/static/public_app/ts/landing/module-cards.ts',
        'public_app/tools/plot-viewer/index': 'apps/public_app/static/public_app/ts/tools/plot-viewer/index.ts',
        'public_app/pages/api-docs': 'apps/public_app/static/public_app/ts/pages/api-docs.ts',
        'public_app/pages/release-timeline': 'apps/public_app/static/public_app/ts/pages/release-timeline.ts',
        # Accounts app
        'accounts_app/profile': 'apps/accounts_app/static/accounts_app/ts/profile.ts',
        'accounts_app/account-settings': 'apps/accounts_app/static/accounts_app/ts/account-settings.ts',
        'accounts_app/ssh_keys': 'apps/accounts_app/static/accounts_app/ts/ssh_keys.ts',
        'accounts_app/remote_credentials': 'apps/accounts_app/static/accounts_app/ts/remote_credentials.ts',
        # Social app
        'social_app/explore-inline': 'apps/social_app/static/social_app/ts/explore-inline.ts',
        # Scholar app - additional
        'scholar_app/bibtex/status-tiles': 'apps/scholar_app/static/scholar_app/ts/bibtex/status-tiles.ts',
        'scholar_app/bibtex/bibtex-enrichment': 'apps/scholar_app/static/scholar_app/ts/bibtex/bibtex-enrichment.ts',
        'scholar_app/bibtex/queue-management': 'apps/scholar_app/static/scholar_app/ts/bibtex/queue-management.ts',
        'scholar_app/shared/collapsible-panels': 'apps/scholar_app/static/scholar_app/ts/shared/collapsible-panels.ts',
        'scholar_app/shared/panel-resizer': 'apps/scholar_app/static/scholar_app/ts/shared/panel-resizer.ts',
        'scholar_app/common/project-selector': 'apps/scholar_app/static/scholar_app/ts/common/project-selector.ts',
        'scholar_app/scholar-workspace-init': 'apps/scholar_app/static/scholar_app/ts/scholar-workspace-init.ts',
        'scholar_app/bibtex/job-detail-ui': 'apps/scholar_app/static/scholar_app/ts/bibtex/job-detail-ui.ts',
        'scholar_app/bibtex/scholar-ai2-integration': 'apps/scholar_app/static/scholar_app/ts/bibtex/scholar-ai2-integration.ts',
        'scholar_app/common/init-tabs': 'apps/scholar_app/static/scholar_app/ts/common/init-tabs.ts',
        'scholar_app/common/scholar-index-main': 'apps/scholar_app/static/scholar_app/ts/common/scholar-index-main.ts',
        'scholar_app/search/nouislider-init': 'apps/scholar_app/static/scholar_app/ts/search/nouislider-init.ts',
        'scholar_app/search/panel-toggle': 'apps/scholar_app/static/scholar_app/ts/search/panel-toggle.ts',
        'scholar_app/search/scitex-search': 'apps/scholar_app/static/scholar_app/ts/search/scitex-search.ts',
        'scholar_app/search/advanced-sorting': 'apps/scholar_app/static/scholar_app/ts/search/advanced-sorting.ts',
        'scholar_app/search/drag-sort': 'apps/scholar_app/static/scholar_app/ts/search/drag-sort.ts',
        'scholar_app/search/swarm-plots': 'apps/scholar_app/static/scholar_app/ts/search/swarm-plots.ts',
        'scholar_app/search/seekbar-integration': 'apps/scholar_app/static/scholar_app/ts/search/seekbar-integration.ts',
        'scholar_app/search/search-ui': 'apps/scholar_app/static/scholar_app/ts/search/search-ui.ts',
        'scholar_app/init/swarm-plots-init': 'apps/scholar_app/static/scholar_app/ts/init/swarm-plots-init.ts',
        'scholar_app/graph/citation-graph': 'apps/scholar_app/static/scholar_app/ts/graph/citation-graph.ts',
        'scholar_app/search/search-controls': 'apps/scholar_app/static/scholar_app/ts/search/search-controls.ts',
        # Project app - additional
        'project_app/projects/settings': 'apps/project_app/static/project_app/ts/projects/settings.ts',
        # Shared utilities
        'shared/utils/theme-switcher': 'static/shared/ts/utils/theme-switcher.ts',
        'shared/utils/tooltip-auto-position': 'static/shared/ts/utils/tooltip-auto-position.ts',
        'shared/utils/main': 'static/shared/ts/utils/main.ts',
        'shared/utils/dropdown': 'static/shared/ts/utils/dropdown.ts',
        'shared/utils/django-messages': 'static/shared/ts/utils/django-messages.ts',
        'shared/utils/element-inspector': 'static/shared/ts/utils/element-inspector.ts',
        'shared/utils/console-interceptor': 'static/shared/ts/utils/console-interceptor.ts',
        'shared/code-blocks': 'static/shared/ts/code-blocks.ts',
        'shared/components/confirm-modal': 'static/shared/ts/components/confirm-modal.ts',
        'shared/components/header': 'static/shared/ts/components/header.ts',
        'shared/components/workspace-files-tree': 'static/shared/ts/components/workspace-files-tree/WorkspaceFilesTree.ts',
        'shared/components/seekbar': 'static/shared/ts/components/seekbar.ts',
        'shared/utils/highlight-js-bibtex': 'static/shared/ts/utils/highlight-js-bibtex.ts',
        'shared/workspace-panel-resizer': 'static/shared/ts/components/workspace-panel-resizer.ts',
    }
    return mappings.get(entry_name, f'{entry_name}.ts')


