#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Plugin apps: any installed package with a ``scitex.apps`` entry point.

``pip install <pkg>`` is the whole install. Settings add the AppConfig
(config/settings/_optional_apps.py), this module mounts its urls and lists its
launcher tile from its manifest. Contract: scitex_app.plugins.
"""

from __future__ import annotations

import logging
from importlib.util import find_spec

logger = logging.getLogger(__name__)


def _module_exists(dotted: str) -> bool:
    try:
        return find_spec(dotted) is not None
    except (ImportError, ValueError):
        return False


def _configs() -> list:
    try:
        from scitex_app.plugins import loaded_plugin_configs
    except ImportError:
        return []
    try:
        return loaded_plugin_configs()
    except Exception:
        logger.exception("[plugin_apps] discovery failed")
        return []


def _route_taken(route: str, existing) -> bool:
    return any(str(p.pattern).startswith(route) for p in existing)


def plugin_urlpatterns(existing) -> list:
    """One ``include()`` per plugin, skipping routes the hub already serves."""
    from django.urls import include, path
    from scitex_app.plugins import mount_route

    patterns = []
    for config in _configs():
        route = mount_route(config)
        urls_module = f"{config.name}.urls"
        if _route_taken(route, existing) or not _module_exists(urls_module):
            continue
        patterns.append(path(route, include(urls_module)))
        logger.info("[plugin_apps] mounted %s at /%s", config.name, route)
    return patterns


def plugin_module_config(config):
    """Launcher ModuleConfig built from the plugin's own manifest."""
    from apps.infra.workspace_app.registry import _manifest_to_module_config
    from scitex_app.plugins import mount_route

    manifest = dict(config.manifest)
    slug = manifest.get("slug") or config.label
    manifest.update(
        name=slug,
        label=manifest.get("label") or slug,
        app_name=config.label,
        order=manifest.get("order", 90),
        ai_hint=manifest.get("ai_hint") or manifest.get("subtitle", ""),
        # The app serves its own pages; there is no workspace partial.
        partial_template="",
        renders_ui=False,
    )
    module = _manifest_to_module_config(manifest)
    module.url = "/" + mount_route(config)
    return module


def register_plugin_modules() -> None:
    """Add a tile for each plugin whose slug is not already registered."""
    from apps.infra.workspace_app.registry import get_module, register_module

    for config in _configs():
        try:
            module = plugin_module_config(config)
            if get_module(module.name) is None:
                register_module(module)
        except Exception:
            logger.exception("[plugin_apps] cannot list %s", config.name)


# EOF
