#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Plugin apps: any installed package with a ``scitex.apps`` entry point.

``pip install <pkg>`` is the whole install. Settings add the AppConfig
(config/settings/_optional_apps.py), this module mounts its urls and lists its
launcher tile from its manifest. Contract: scitex_sdk.app.plugins.
"""

from __future__ import annotations

import logging
from importlib.util import find_spec

logger = logging.getLogger(__name__)

#: The hub's own distribution; its declared dependencies are the leaf floors.
_HUB_DISTRIBUTION = "scitex-hub"


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
    """Whether the hub serves ``route`` itself (the plugin is then skipped)."""
    return any(str(p.pattern) == route for p in existing)


def _hub_subroutes(route: str, existing) -> list:
    """Hub patterns nested strictly UNDER a plugin's route.

    E.g. a dev-only parity reference at ``apps/<slug>/old-direct/``. They do
    not take the plugin's route, but they must resolve BEFORE the plugin
    mount: a leaf urlconf may end in a ``<path:...>`` catch-all that would
    otherwise swallow them.
    """
    return [
        p
        for p in existing
        if str(p.pattern) != route and str(p.pattern).startswith(route)
    ]


def _hub_requirements() -> dict:
    """``{canonical distribution name: SpecifierSet}`` the hub itself declares.

    Read from the hub's own installed metadata (its pyproject dependencies),
    so the floor pip enforces is also enforced at mount time: editable or
    bind-mounted leaf installs bypass pip's resolver entirely. Optional
    extras are ignored. Empty when the hub runs from an uninstalled tree.
    """
    from importlib.metadata import PackageNotFoundError, requires

    from packaging.requirements import InvalidRequirement, Requirement
    from packaging.utils import canonicalize_name

    try:
        raw = requires(_HUB_DISTRIBUTION) or []
    except PackageNotFoundError:
        return {}
    floors = {}
    for line in raw:
        try:
            req = Requirement(line)
        except InvalidRequirement:
            continue
        if req.marker is not None and not req.marker.evaluate({"extra": ""}):
            continue
        floors[canonicalize_name(req.name)] = req.specifier
    return floors


def _version_incompatibility(config, floors: dict):
    """Why the installed leaf is below the hub's floor, or ``None`` when it is not.

    The floor is the hub's statement of the oldest leaf it can mount safely
    (e.g. the first release whose views authorize every request through
    ``scitex_sdk.host``). The leaf is identified by its manifest
    ``pip_package``; a leaf the hub declares no floor for is not checked.
    """
    from importlib.metadata import PackageNotFoundError, version

    from packaging.utils import canonicalize_name

    manifest = getattr(config, "manifest", None) or {}
    dist = str(manifest.get("pip_package") or "")
    spec = floors.get(canonicalize_name(dist)) if dist else None
    if spec is None:
        return None
    try:
        installed = version(dist)
    except PackageNotFoundError:
        return f"{dist} has no installed distribution (hub requires {dist}{spec})"
    if spec.contains(installed, prereleases=True):
        return None
    return f"{dist} {installed} does not satisfy the hub requirement {dist}{spec}"


def _policy_error(config):
    """The SDK's mount-time verdict on the manifest ``mount_policy``, or ``None``.

    ``scitex_sdk.app.jail.validate_mount_policy`` is the contract's own bar
    (e.g. a file-touching leaf without a jail, or a jail without a login
    boundary). A leaf it refuses is not mounted.
    """
    try:
        from scitex_sdk.app.jail import validate_mount_policy
        from scitex_sdk.app.plugins import LeafContractError
    except ImportError:
        return None
    try:
        validate_mount_policy(getattr(config, "manifest", None), plugin=config.name)
    except LeafContractError as exc:
        return f"invalid mount_policy: {exc}"
    return None


def _login_required_policy(config) -> bool:
    """Whether the plugin's own manifest asks for a login boundary.

    Opt-IN per leaf (``mount_policy.login_required``): plugins that handle
    anonymous traffic themselves (figrecipe, stats) keep byte-identical
    behaviour; leaves whose views assume an authenticated ``request.user``
    (agent-container, cards, storage) get the boundary without a hub-side wrapper.
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

    The hub never names a plugin route: whatever the leaf's own urlconf
    declares is served. Two host rules apply generically:

    * a leaf below the hub's declared dependency floor is NOT mounted
      (one WARNING: a real incompatibility, fail closed);
    * hub patterns nested under a plugin route are MOVED out of
      ``existing`` (a list, mutated in place) to just ahead of the plugin
      mount, so a leaf catch-all cannot shadow them.

    The outcome is logged once, as a single INFO summary.
    """
    from functools import cached_property

    from django.urls import include, path
    from django.urls.resolvers import RoutePattern, URLResolver

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

    floors = _hub_requirements()
    patterns = []
    mounted, skipped = [], []
    for config in _configs():
        route = mount_route(config)
        urls_module = f"{config.name}.urls"
        if _route_taken(route, existing):
            skipped.append(f"{config.label} (hub serves /{route})")
            continue
        if not _module_exists(urls_module):
            skipped.append(f"{config.label} (no urls module)")
            continue
        reason = _version_incompatibility(config, floors) or _policy_error(config)
        if reason is not None:
            logger.warning(
                "[plugin_apps] NOT mounting %s at /%s: %s",
                config.name,
                route,
                reason,
            )
            skipped.append(f"{config.label} (incompatible)")
            continue
        for sub in _hub_subroutes(route, existing):
            existing.remove(sub)
            patterns.append(sub)
        gated = _login_required_policy(config)
        if gated:
            patterns.append(PluginMountResolver(route, urls_module))
        else:
            patterns.append(path(route, include(urls_module)))
        version = getattr(config, "app_version", "") or "?"
        mounted.append(
            f"{config.label} {version} at /{route}" + (" (login)" if gated else "")
        )
    logger.info(
        "[plugin_apps] mounted %d plugin app(s): %s%s",
        len(mounted),
        ", ".join(mounted) or "none",
        f"; not mounted: {', '.join(skipped)}" if skipped else "",
    )
    return patterns


def plugin_module_config(config):
    """Launcher ModuleConfig built from the plugin's own manifest."""
    from scitex_sdk.app.plugins import mount_route

    from apps.infra.workspace_app.registry import _manifest_to_module_config

    manifest = dict(config.manifest)
    slug = manifest.get("slug") or config.label
    manifest.update(
        name=slug,
        label=manifest.get("label") or slug,
        app_name=config.label,
        order=manifest.get("order", 90),
        ai_hint=manifest.get("ai_hint") or manifest.get("subtitle", ""),
        # Trusted installed leaves own their optional workspace content too.
        partial_template=manifest.get("partial_template", ""),
        renders_ui=bool(manifest.get("partial_template")),
    )
    module = _manifest_to_module_config(manifest)
    module.url = "/" + mount_route(config)
    # These manifests come from operator-installed packages. Keep raw SVG
    # handling here, rather than enabling it for user-authored dev manifests.
    for name in ("icon_svg_tab", "icon_svg_nav"):
        if manifest.get(name):
            setattr(module, name, manifest[name])
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
