#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Plugin apps: any installed package with a ``scitex.apps`` entry point.

``pip install <pkg>`` is the whole install. Settings add the AppConfig
(config/settings/_optional_apps.py), this module mounts its urls and lists its
launcher tile from its manifest. Contract: scitex_sdk.app.plugins.
"""

from __future__ import annotations

import logging
import re
from importlib.util import find_spec

logger = logging.getLogger(__name__)


def _module_exists(dotted: str) -> bool:
    try:
        return find_spec(dotted) is not None
    except (ImportError, ValueError):
        return False


def _configs() -> list:
    try:
        from scitex_sdk.app.plugins import loaded_plugin_configs
    except ImportError:
        return []
    try:
        return loaded_plugin_configs()
    except Exception:
        logger.exception("[plugin_apps] discovery failed")
        return []


def _route_taken(route: str, existing) -> bool:
    return any(str(p.pattern).startswith(route) for p in existing)


def _login_required_policy(config) -> bool:
    """Whether the plugin's own manifest asks for a login boundary.

    Opt-IN per leaf (``mount_policy.login_required``): plugins that handle
    anonymous traffic themselves (figrecipe, stats) keep byte-identical
    behaviour; leaves whose views assume an authenticated ``request.user``
    (agents, cards, storage) get the boundary without a hub-side wrapper.
    """
    manifest = getattr(config, "manifest", None) or {}
    policy = manifest.get("mount_policy", {})
    return bool(isinstance(policy, dict) and policy.get("login_required", False))


def _wrap_login(pattern):
    """Wrap one plugin route's view with login_required, generically.

    No view symbol is named: the whole mounted tree is wrapped, so a new
    upstream view is login-gated with zero hub changes.
    """
    from django.contrib.auth.decorators import login_required
    from django.urls import URLPattern, URLResolver

    if isinstance(pattern, URLResolver):
        return URLResolver(
            pattern.pattern,
            [_wrap_login(p) for p in pattern.url_patterns],
            pattern.default_kwargs,
            pattern.app_name,
            pattern.namespace,
        )
    if isinstance(pattern, URLPattern):
        return URLPattern(
            pattern.pattern,
            login_required(pattern.callback),
            pattern.default_args,
            pattern.name,
        )
    return pattern


def plugin_urlpatterns(existing) -> list:
    """One mount per plugin, skipping routes the hub already serves.

    A plugin whose manifest declares ``mount_policy.login_required`` is
    mounted through :class:`PluginMountResolver`, which login-wraps its
    whole urlconf on first resolve (lazy, so the optional package stays
    import-safe and startup pays nothing extra).
    """
    from django.urls import include, path
    from django.urls.resolvers import RoutePattern, URLResolver
    from functools import cached_property

    try:
        from scitex_sdk.app.plugins import mount_route  # type: ignore[import-not-found]
    except ImportError:
        # scitex-sdk is the canonical integration surface. Released wheels that
        # predate the plugin API must still boot the Hub; no discovered plugin
        # means there is nothing to mount.
        return []

    class PluginMountResolver(URLResolver):
        def __init__(self, route, urls_module):
            urlconf_module, app_name, namespace = include(urls_module)
            super().__init__(
                RoutePattern(route),
                urlconf_module,
                app_name=app_name,
                namespace=namespace,
            )

        @cached_property
        def url_patterns(self):  # noqa: D102 — Django resolver protocol
            return [_wrap_login(p) for p in super().url_patterns]

    patterns = []
    for config in _configs():
        route = mount_route(config)
        urls_module = f"{config.name}.urls"
        if _route_taken(route, existing) or not _module_exists(urls_module):
            continue
        if _login_required_policy(config):
            patterns.append(PluginMountResolver(route, urls_module))
            logger.info("[plugin_apps] mounted %s at /%s (login-gated)", config.name, route)
        else:
            patterns.append(path(route, include(urls_module)))
            logger.info("[plugin_apps] mounted %s at /%s", config.name, route)
    return patterns


def plugin_module_config(config):
    """Launcher ModuleConfig built from the plugin's own manifest."""
    from apps.infra.workspace_app.registry import _manifest_to_module_config
    from scitex_sdk.app.plugins import mount_route

    try:
        from scitex_sdk.app.plugins import leaf_declarations
    except ImportError:
        declarations = {}
    else:
        declarations = leaf_declarations(
            config.name,
            {
                "context_builder": str,
                "partial_template": str,
                "content_renderer": str,
                "api_policy_module": str,
                "hosted_api_dispatcher": str,
            },
        )

    manifest = dict(config.manifest)
    slug = manifest.get("slug") or config.label
    manifest.update(
        name=slug,
        label=manifest.get("label") or slug,
        app_name=config.label,
        order=manifest.get("order", 90),
        ai_hint=manifest.get("ai_hint") or manifest.get("subtitle", ""),
        # Old plugins retain their standalone-page fallback. Only genuine
        # typed leaf declarations enable a workspace partial/renderer.
        partial_template=declarations.get("partial_template", ""),
        context_builder=declarations.get(
            "context_builder", manifest.get("context_builder", "")
        ),
        content_renderer=declarations.get("content_renderer", ""),
        renders_ui=bool(declarations.get("partial_template")),
    )
    module = _manifest_to_module_config(manifest)
    module.url = "/" + mount_route(config)
    return module


def _plugin_distribution(config) -> str:
    """The unique discovered distribution of this exact ready config class."""
    from scitex_sdk.app.plugins import discover_plugin_apps

    config_path = f"{type(config).__module__}.{type(config).__qualname__}"
    matches = [
        record for record in discover_plugin_apps()
        if record.app_config == config_path
    ]
    if len(matches) != 1:
        return ""
    distribution = matches[0].distribution
    return distribution if isinstance(distribution, str) else ""


def _bind_plugin_renderer(existing, plugin, config) -> None:
    """Attach only presentation capability to the same backing distribution.

    A slug collision alone must never replace native identity, URL, template,
    context builder or policy. The host context still declares the guarded API
    mount and remains the fallback when that mount is absent. Backing ownership
    comes from the discovered entry point, never the leaf's manifest claim.
    """
    owner = existing.pip_package
    candidate = _plugin_distribution(config)
    if (
        not owner or not candidate or not plugin.content_renderer
        or not existing.context_builder
    ):
        return
    if re.sub(r"[-_.]+", "-", owner).lower() == re.sub(
        r"[-_.]+", "-", candidate
    ).lower():
        existing.content_renderer = plugin.content_renderer
        existing.renderer_mount_context_builder = existing.context_builder


def register_plugin_modules() -> None:
    """Add a tile for each plugin whose slug is not already registered."""
    from apps.infra.workspace_app.registry import get_module, register_module

    for config in _configs():
        try:
            module = plugin_module_config(config)
            existing = get_module(module.name)
            if existing is None:
                register_module(module)
            else:
                _bind_plugin_renderer(existing, module, config)
        except Exception:
            logger.exception("[plugin_apps] cannot list %s", config.name)


# EOF
