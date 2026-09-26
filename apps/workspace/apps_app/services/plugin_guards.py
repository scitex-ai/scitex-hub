#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generic mount-policy enforcement for plugin apps (``scitex.apps``).

A plugin LEAF declares facts about itself in its own manifest under the
``mount_policy`` key; this module enforces them WITHOUT app-specific code —
no view symbol, route, store path, or query parameter belonging to any one
plugin is named anywhere here. Adding a plugin (or a new route to one) is
an upstream-only change: declare it in the leaf manifest and the host
enforces it.

Contract (all keys optional; absent key = open behaviour, exactly as if
the plugin were mounted raw)::

    "mount_policy": {
      "login_required": true,     # anonymous users redirect to LOGIN_URL
      "audience": "staff",        # only staff/superuser/listed operators
      "tenant_store": "a/b.yaml", # workspace-relative store, injected as an
      "tenant_attribute": "name", # UNFORGEABLE request attribute (never the
                                  # query string); 404 when no project
      "discard_query_params": ["store"],  # inbound forgeries dropped+logged
      "writable_routes": ["dm/thread/<str:peer>"],  # non-safe methods only
                                  # here (Django converter syntax, anchored
                                  # full match on the mount sub-path)
    }

Notes on the individual rules:

* ``login_required`` is enforced at URL-mount time (see
  :mod:`apps.workspace.apps_app.services.plugin_apps`), not here.
* ``audience: staff`` exists because a leaf read path can serve a shared
  store the host cannot re-scope (live leak-check 2026-09-26: a non-staff
  user read 8151 fleet cards with the old hub gate bypassed). The gate is
  therefore policy, not code: the leaf says WHO, the host enforces HOW.
* Tenancy travels on a request ATTRIBUTE because a query parameter lives in
  the exact namespace the caller controls — an injected ``?store=`` and a
  hostile one are byte-identical downstream by construction.
* Writable routes re-arm CSRF: leaf write views are typically
  ``@csrf_exempt`` while the host authenticates with a session cookie, and
  cookie auth plus an exempt POST is textbook cross-site request forgery.
  A plugin view that is NOT exempt is unaffected (the check passes through).
* A restricted-audience plugin that declares NO ``writable_routes`` denies
  ALL non-safe methods (fail closed); unrestricted plugins without the key
  keep no method gate (their behaviour is unchanged from a raw mount).
"""

from __future__ import annotations

import logging
import re
from functools import cached_property, lru_cache

logger = logging.getLogger(__name__)

#: Non-mutating methods never need the write gate.
_SAFE_METHODS = ("GET", "HEAD", "OPTIONS")

#: The only audience restriction the generic layer understands.
_AUDIENCE_STAFF = "staff"

#: Django path converters mapped to regex fragments for ``writable_routes``.
_CONVERTER_RES = {
    "str": "[^/]+",
    "slug": "[-a-zA-Z0-9_]+",
    "uuid": "[0-9a-fA-F-]+",
    "int": "[0-9]+",
    "path": ".+",
}

_MOUNT_POLICY_KEY = "mount_policy"


def _configs() -> list:
    try:
        from scitex_app.plugins import loaded_plugin_configs
    except ImportError:
        return []
    try:
        return loaded_plugin_configs()
    except Exception:
        logger.exception("[plugin_guards] discovery failed")
        return []


def _policy_of(config) -> dict:
    manifest = getattr(config, "manifest", None) or {}
    policy = manifest.get(_MOUNT_POLICY_KEY, {})
    return policy if isinstance(policy, dict) else {}


def _route_of(config) -> str:
    from scitex_app.plugins import mount_route

    return mount_route(config)


@lru_cache(maxsize=1)
def _cached_mount_table() -> tuple:
    """``(route_prefix, label, policy)`` per plugin with a mount policy.

    Cached for the process lifetime: entry points do not change under a
    running server (a reinstall restarts it). ``route_prefix`` always has
    leading and trailing slashes (``/apps/cards/``).
    """
    table = []
    for config in _configs():
        policy = _policy_of(config)
        if not policy:
            continue
        route = _route_of(config).strip("/")
        manifest = getattr(config, "manifest", None) or {}
        label = manifest.get("label") or getattr(config, "verbose_name", route)
        table.append((f"/{route}/" if route else "/", str(label), policy))
    return tuple(table)


def _mount_table():
    """The governing ``(prefix, label, policy)`` rows, test-overridable.

    Tests drive the guard with synthetic policies via the
    ``PLUGIN_MOUNT_TABLE_OVERRIDE`` setting (a list of the same tuples),
    so no test names a real plugin and the suite runs without the optional
    packages installed.
    """
    from django.conf import settings

    override = getattr(settings, "PLUGIN_MOUNT_TABLE_OVERRIDE", None)
    if override is not None:
        return tuple(override)
    return _cached_mount_table()


def plugin_mount_prefixes():
    """Route prefixes of every plugin mount (hub chrome may scope by these)."""
    try:
        from scitex_app.plugins import mount_route

        return tuple(f"/{mount_route(c).strip('/')}/" for c in _configs())
    except Exception:
        return ()


def _match_mount(path: str):
    """The ``(prefix, label, policy)`` governing ``path``, or ``None``."""
    for prefix, label, policy in _mount_table():
        if path == prefix.rstrip("/") or path.startswith(prefix):
            return prefix, label, policy
    return None


def plugin_access_allowed(user, policy: dict) -> bool:
    """Whether ``user`` may reach a mount governed by ``policy``.

    Open mounts admit any authenticated user (anonymous is turned away by
    the login boundary). ``audience: staff`` additionally admits only
    staff, superusers, and usernames listed in
    ``settings.SCITEX_HUB_PLUGIN_OPERATORS``. The operator list is
    deployment DATA (an env var in settings), never app logic.
    """
    if user is None or not getattr(user, "is_authenticated", False):
        return False
    if policy.get("audience") != _AUDIENCE_STAFF:
        return True
    if getattr(user, "is_staff", False) or getattr(user, "is_superuser", False):
        return True
    from django.conf import settings

    operators = set(getattr(settings, "SCITEX_HUB_PLUGIN_OPERATORS", ())) or set()
    return getattr(user, "username", "") in operators


def can_open_plugin_mount(user, path: str) -> bool:
    """Tile-level predicate: opening a tile at ``path`` gets past its mount.

    Unrestricted paths are unaffected (``True``); restricted ones delegate
    to the SAME predicate the request guard enforces, so a tile a user can
    see never opens onto a 403.
    """
    match = _match_mount(path)
    if match is None:
        return True
    _prefix, _label, policy = match
    return plugin_access_allowed(user, policy)


def _compile_route(pattern: str) -> re.Pattern:
    """``dm/thread/<str:peer>`` -> ``^dm/thread/[^/]+$`` (anchored)."""

    def _convert(match: re.Match) -> str:
        converter, _name = match.group(1) or "str", match.group(2)
        return _CONVERTER_RES.get(converter, "[^/]+")

    return re.compile("^" + re.sub(r"<(?:(str|slug|uuid|int|path):)?(\w+)>", _convert, pattern) + "$")


def _writable_compiled(policy):
    declared = policy.get("writable_routes", None)
    if declared is None:
        return None
    routes = [declared] if isinstance(declared, str) else list(declared or [])
    return tuple(_compile_route(r.strip("/")) for r in routes)


def _is_writable_subpath(subpath: str, compiled) -> bool:
    return any(rx.match(subpath) for rx in compiled)


def resolve_plugin_tenant_store(request, rel_store: str):
    """Workspace store for the requester's active project, or ``None``.

    Generic hub infrastructure (current project + workspace base), NOT app
    knowledge: the leaf only names its store RELATIVE to the project
    (``tenant_store``), and the resolved path is containment-validated
    against the owning workspace base before anything may use it.
    """
    from pathlib import Path

    from apps.infra.project_app.services.filesystem.paths import (
        get_org_base_path,
        get_user_base_path,
    )
    from apps.infra.project_app.services.project_utils import get_current_project

    if not rel_store or Path(rel_store).is_absolute():
        logger.error("[plugin_guards] refusing non-relative tenant store %r", rel_store)
        return None
    project = get_current_project(request, user=request.user)
    if project is None:
        return None
    if getattr(project, "is_org_owned", False):
        base = get_org_base_path(project.org_owner)
    else:
        base = get_user_base_path(project.owner)
    store = base / project.slug / rel_store
    try:
        inside = store.resolve().is_relative_to(base.resolve())
    except OSError:
        inside = False
    if not inside:
        logger.error(
            "[plugin_guards] resolved store %s escapes workspace base %s — refusing",
            store,
            base,
        )
        return None
    return store


def _wants_html(request) -> bool:
    """Navigations get a page; fetches/scripts get shaped JSON.

    WHY the path is not the discriminator here (it was, app-specifically,
    in the retired per-app middleware): the board's fetches send no JSON
    Accept header, so content negotiation is the only generic signal. A
    browser navigation sends ``text/html``; ``fetch``/curl send ``*/*``.
    """
    accept = request.headers.get("Accept", "")
    return "text/html" in accept and "application/json" not in accept


class PluginMountGuardMiddleware:
    """Enforce leaf-declared ``mount_policy`` on plugin-mounted routes.

    Runs after Authentication so ``request.user`` is final, and no-ops in
    one prefix check for every non-plugin request. See the module docstring
    for the contract; NO plugin name, route, store, or parameter is named
    in this file.
    """

    sync_capable = True

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        from django.conf import settings
        from django.http import JsonResponse
        from django.shortcuts import redirect, render

        match = _match_mount(request.path)
        if match is None:
            return self.get_response(request)
        prefix, label, policy = match

        user = getattr(request, "user", None)
        if user is None or not user.is_authenticated:
            return redirect(f"{settings.LOGIN_URL}?next={request.path}")

        if not plugin_access_allowed(user, policy):
            if _wants_html(request):
                return render(
                    request,
                    "plugin_apps/restricted.html",
                    {"app_label": label},
                    status=403,
                )
            return JsonResponse(
                {
                    "error": (f"{label} is limited to authorized accounts for now."),
                    "reason": "plugin-mount-restricted-audience",
                },
                status=403,
            )

        tenant_store = policy.get("tenant_store", "")
        tenant_attr = policy.get("tenant_attribute", "")
        if tenant_store and tenant_attr:
            store = resolve_plugin_tenant_store(request, tenant_store)
            if store is None:
                return JsonResponse(
                    {
                        "error": (
                            "No active project — this app shows your project "
                            "workspace. Create or open a project first."
                        ),
                        "hint": "/new/",
                    },
                    status=404,
                )
            setattr(request, tenant_attr, store)

        for param in policy.get("discard_query_params", []) or []:
            if param in request.GET:
                logger.warning(
                    "[plugin_guards] discarding client-supplied ?%s= from user %s "
                    "(server-side tenancy only)",
                    param,
                    getattr(user, "username", "?"),
                )
                params = request.GET.copy()
                params.pop(param, None)
                request.GET = params

        if request.method not in _SAFE_METHODS:
            compiled = _writable_compiled(policy)
            subpath = request.path[len(prefix):].strip("/")
            if compiled is None:
                if policy.get("audience") == _AUDIENCE_STAFF:
                    return JsonResponse(
                        {"error": "Writes are not enabled on this mount.", "reason": "plugin-mount-readonly"},
                        status=403,
                    )
            elif not _is_writable_subpath(subpath, compiled):
                return JsonResponse(
                    {"error": "Writes are not enabled for this route.", "reason": "plugin-mount-readonly"},
                    status=403,
                )
            else:
                rejection = self._rearm_csrf(request)
                if rejection is not None:
                    return rejection

        return self.get_response(request)

    @staticmethod
    def _rearm_csrf(request):
        """Re-apply CSRF on an allowlisted write; ``None`` lets it through.

        Leaf write views are typically ``@csrf_exempt`` while the host
        authenticates with a session cookie — cookie auth plus an exempt
        POST is textbook cross-site request forgery, and the login boundary
        is precisely what makes the forgery succeed. Passing a plain
        callable (no ``csrf_exempt`` attribute) makes ``CsrfViewMiddleware``
        enforce; it sits ahead of this middleware, so its ``process_request``
        has already populated the token and this call is a check. A plugin
        view that is NOT exempt passes through untouched.
        """
        from django.middleware.csrf import CsrfViewMiddleware

        csrf = CsrfViewMiddleware(lambda _req: None)
        reason = csrf.process_view(request, lambda *a, **kw: None, (), {})
        if reason is not None:
            logger.warning(
                "[plugin_guards] CSRF rejection on opened write %s for user %s",
                request.path,
                getattr(getattr(request, "user", None), "username", "?"),
            )
            return reason
        return None


__all__ = [
    "PluginMountGuardMiddleware",
    "can_open_plugin_mount",
    "plugin_access_allowed",
    "plugin_mount_prefixes",
    "resolve_plugin_tenant_store",
]
