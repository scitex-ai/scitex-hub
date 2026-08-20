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
        "figrecipe_app",
        "writer_app",
        "project_app",
        "scholar_app",
        "public_app",
        "accounts_app",
        "repo_app",
        "clew_app",
        "social_app",
        "docs_app",
        "apps_app",
        "dev_app",
        "workspace_app",
        "organizations_app",
        "discovery_app",
        "shared",
        "scitex_ui",
    }
)

# Cache manifest in production (with mtime for auto-invalidation after rebuilds)
_manifest_cache = None
_manifest_mtime: float = 0.0

# Cache name→entry reverse index for manifest lookups
_manifest_name_index: dict | None = None

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
    """Load the Vite manifest file (production only).

    Re-reads from disk when the file's mtime changes, so a Vite rebuild
    is picked up without restarting Django workers.
    """
    global _manifest_cache, _manifest_mtime, _manifest_name_index

    manifest_path = (
        Path(settings.BASE_DIR) / "staticfiles" / "vite" / ".vite" / "manifest.json"
    )

    try:
        current_mtime = manifest_path.stat().st_mtime
    except OSError:
        # File doesn't exist — return empty and don't cache
        _manifest_cache = {}
        _manifest_mtime = 0.0
        _manifest_name_index = None
        return _manifest_cache

    if _manifest_cache is not None and current_mtime == _manifest_mtime:
        return _manifest_cache

    with open(manifest_path) as f:
        _manifest_cache = json.load(f)
    _manifest_mtime = current_mtime
    # Invalidate the name index so it gets rebuilt from the new manifest
    _manifest_name_index = None

    return _manifest_cache


def _get_manifest_by_name(name: str) -> dict | None:
    """Look up a manifest entry by its 'name' field.

    Vite manifest keys are source file paths (e.g. '../figrecipe/src/...').
    For external packages, _entry_to_ts_path won't match the key.
    This uses the 'name' field that Vite sets from rollupOptions.output.entryFileNames.
    """
    global _manifest_name_index
    manifest = get_manifest()
    if _manifest_name_index is None:
        _manifest_name_index = {}
        for _key, entry in manifest.items():
            entry_name = entry.get("name")
            if entry_name:
                _manifest_name_index[entry_name] = entry
    return _manifest_name_index.get(name)


@register.simple_tag
def vite_hmr_client():
    """
    Include Vite HMR client(s).

    Dev: Host Vite (5173) + Container Vite (5174) HMR clients.
    Prod: Container Vite (5174) HMR client only (for dev apps).
    Browser silently ignores clients for servers that aren't running.
    """
    scripts = ""

    if settings.DEBUG and not getattr(settings, "VITE_USE_BUILD", False):
        host_port = getattr(settings, "VITE_HOST_PORT", 5173)
        dev_port = getattr(settings, "VITE_DEV_APP_PORT", 5174)
        # Use browser's hostname so both localhost and LAN IP work automatically
        scripts += (
            f'<script type="module">'
            f"const h=window.location.hostname;"
            f"const p=window.location.protocol;"
            f'const s=document.createElement("script");s.type="module";'
            f's.src=p+"//"+h+":{host_port}/@vite/client";document.head.appendChild(s);'
            f'const s2=document.createElement("script");s2.type="module";'
            f's2.src=p+"//"+h+":{dev_port}/@vite/client";s2.onerror=()=>{{}};'
            f"document.head.appendChild(s2);"
            f"</script>"
        )
    elif getattr(settings, "VITE_DEV_APP_ENABLED", False):
        # Production with dev apps: HMR through nginx proxy (only when explicitly enabled)
        scripts += '<script type="module" src="/_vite_dev_app/@vite/client" onerror=""></script>'

    return mark_safe(scripts) if scripts else ""


def _is_dev_app_entry(entry_name: str) -> bool:
    """Check if entry belongs to a dev-installed app (not platform)."""
    app_prefix = entry_name.split("/")[0] if "/" in entry_name else entry_name
    return app_prefix not in _PLATFORM_APPS


def _manifest_miss(msg: str, entry_name: str) -> str:
    """Fail LOUD on a manifest-lookup miss — never silently ship a page
    with a missing script (the module pane would stay blank with zero
    errors anywhere; observed as "Explore renders zero body").

    DEBUG: raise so the dev sees the failure immediately.
    Production: emit a console.error script tag so browser/QA console
    capture records the miss (server-side log alone is invisible to QA).
    """
    import logging

    logging.getLogger(__name__).error(msg)
    if settings.DEBUG:
        raise template.TemplateSyntaxError(msg)
    payload = json.dumps(f"[vite] missing entry: {entry_name}")
    return mark_safe(f"<script>console.error({payload});</script>")


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
                f'<script type="module">{{const s=document.createElement("script");s.type="module";'
                f's.src=window.location.protocol+"//"+window.location.hostname+":{port}/{entry_name}.ts";'
                f"document.head.appendChild(s);}}</script>"
            )
        else:
            # Production: through nginx proxy
            ts_path = _entry_to_ts_path(entry_name)
            return mark_safe(
                f'<script type="module" src="/_vite_dev_app/{ts_path}"></script>'
            )

    # Platform entries
    # VITE_USE_BUILD=True: use built manifest even in dev (no Vite dev server needed)
    if settings.DEBUG and not getattr(settings, "VITE_USE_BUILD", False):
        ts_path = _entry_to_ts_path(entry_name)
        port = getattr(settings, "VITE_HOST_PORT", 5173)
        return mark_safe(
            f'<script type="module">{{const s=document.createElement("script");s.type="module";'
            f's.src=window.location.protocol+"//"+window.location.hostname+":{port}/{ts_path}";'
            f"document.head.appendChild(s);}}</script>"
        )
    else:
        # Production: Load from Vite manifest
        manifest = get_manifest()
        ts_path = _entry_to_ts_path(entry_name)

        # Look up by ts_path key first, then fall back to name-based index
        # (external packages like figrecipe have non-standard manifest keys)
        entry = manifest.get(ts_path) or _get_manifest_by_name(entry_name)

        if entry:
            js_file = entry["file"]
            tags = ""
            # Collect CSS from this entry AND all its imports (transitive)
            css_files = list(entry.get("css", []))
            for imp in entry.get("imports", []):
                if imp in manifest:
                    css_files.extend(manifest[imp].get("css", []))
            # Deduplicate while preserving order
            seen = set()
            for css_file in css_files:
                if css_file not in seen:
                    seen.add(css_file)
                    tags += f'<link rel="stylesheet" href="{settings.STATIC_URL}vite/{css_file}" />\n'
            tags += f'<script type="module" src="{settings.STATIC_URL}vite/{js_file}"></script>'
            return mark_safe(tags)
        else:
            return _manifest_miss(
                f"Vite entry '{entry_name}' not found in manifest "
                f"(tried ts_path='{ts_path}' and name='{entry_name}')",
                entry_name,
            )


@register.simple_tag(takes_context=True)
def vite_asset_url(context, entry_name: str) -> str:
    """Resolve a Vite entry to its ABSOLUTE JS asset URL (no wrapped <script> tag).

    ``vite_script`` always emits a full ``<script>``/``<link>`` tag, which is
    the right shape for a normal page include but cannot be embedded as a
    *value* — e.g. inside a ``javascript:`` bookmarklet href that injects the
    script onto a THIRD-PARTY page, where a root-relative ``/static/...`` URL
    would incorrectly resolve against that page's own origin. This tag
    reuses the same manifest resolution as ``vite_script`` and returns an
    absolute URL string, built via ``request.build_absolute_uri()`` so
    scheme/host/port are always correct (dev and prod alike) instead of a
    caller hand-assembling ``https://`` + host.

    Dev app entries are not supported (they only make sense as an emitted
    <script> tag against the container Vite dev server, not a bare URL).
    """
    if _is_dev_app_entry(entry_name):
        raise ValueError(
            f"vite_asset_url does not support dev app entries: {entry_name!r}"
        )

    if settings.DEBUG and not getattr(settings, "VITE_USE_BUILD", False):
        ts_path = _entry_to_ts_path(entry_name)
        port = getattr(settings, "VITE_HOST_PORT", 5173)
        request = context.get("request")
        scheme = request.scheme if request is not None else "http"
        # Already a full URL (host Vite dev server) -- nothing to make absolute.
        return f"{scheme}://localhost:{port}/{ts_path}"

    manifest = get_manifest()
    ts_path = _entry_to_ts_path(entry_name)
    entry = manifest.get(ts_path) or _get_manifest_by_name(entry_name)

    if not entry:
        import logging

        logging.getLogger(__name__).error(
            f"vite_asset_url: entry '{entry_name}' not found in manifest (tried ts_path='{ts_path}' and name='{entry_name}')"
        )
        return ""

    relative_url = f"{settings.STATIC_URL}vite/{entry['file']}"
    request = context.get("request")
    if request is not None:
        return request.build_absolute_uri(relative_url)
    return relative_url


@register.simple_tag
def vite_preload(entry_name: str):
    """Emit <link rel="modulepreload"> for a Vite entry point.

    Use this for scripts that are dynamically imported at runtime
    so the browser fetches them early (without executing).
    In dev mode this is a no-op since Vite serves files on demand.
    """
    if settings.DEBUG and not getattr(settings, "VITE_USE_BUILD", False):
        return ""

    manifest = get_manifest()
    ts_path = _entry_to_ts_path(entry_name)
    entry = manifest.get(ts_path) or _get_manifest_by_name(entry_name)

    if entry:
        js_file = entry["file"]
        return mark_safe(
            f'<link rel="modulepreload" href="{settings.STATIC_URL}vite/{js_file}" />'
        )

    return _manifest_miss(
        f"Vite preload entry '{entry_name}' not found in manifest", entry_name
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
        "shared/workspace-sidebar": "static/shared/ts/components/sidebar/index.ts",
        "shared/repo-monitor": "static/shared/ts/components/repo-monitor/index.ts",
        # dev_app: scripts in scripts/ subdir instead of ts/
        "dev_app/scripts/design": "apps/workspace/dev_app/static/dev_app/scripts/design.ts",
        "dev_app/scripts/scitex-icon-generator": "apps/workspace/dev_app/static/dev_app/scripts/scitex-icon-generator.ts",
        # public_app: index.ts in subdir
        "public_app/tools/run-stats": "apps/infra/public_app/static/public_app/ts/tools/run-stats/index.ts",
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

        # Pip-installed packages: resolve via importlib to find static/ts path
        try:
            import importlib

            mod = importlib.import_module(app_name)
            pkg_dir = Path(mod.__file__).parent
            ts_path = pkg_dir / "static" / app_name / "ts" / f"{rest}.ts"
            if ts_path.exists():
                # Return the absolute resolved path to the package's TS source.
                # Pip/editable installs can live anywhere (a .venv, site-packages,
                # or a sibling source checkout), so there is no reliable
                # repo-root-relative form. An absolute path always points at the
                # real file on disk and is a no-op when a caller joins it onto a
                # base dir (vs. the broken "{entry}.ts" last resort). Production
                # asset resolution matches external packages via the manifest
                # name index, not this on-disk path, so absolute is safe there.
                return str(ts_path.resolve())
        except (ImportError, TypeError):
            pass

    # Last resort
    return f"{entry_name}.ts"
