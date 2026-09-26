#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""URL patterns for the hub-side scitex-storage security wrapper.

config/urls.py mounts THIS module at ``apps/storage/`` in place of the raw
``scitex_storage._django.urls`` (card sec-working-dir-passthrough-family,
SITE 4). ``app_name`` is kept as the upstream ``scitex_storage`` so any
``{% url 'scitex_storage:index' %}`` reverse keeps resolving.

THIN-HUB RULE: the hub never names what the plugin provides. ``""`` and
``healthz`` are the wrapper's own (jail guard + organize tabs); EVERYTHING
ELSE the installed release declares (fleet/, bubbles/, sunburst/, api/*,
whatever ships next) is exposed through :class:`_PluginRoutes`, which loads
the plugin's OWN urlconf and wraps each of its views with
``login_required`` WITHOUT naming any of them — new upstream views appear
with zero hub changes.
"""

from __future__ import annotations

from functools import cached_property

from django.urls import URLPattern, URLResolver, path
from django.urls.resolvers import RoutePattern

from . import views

app_name = "scitex_storage"


def _wrap_login(pattern):
    """Wrap one plugin route's view with login_required, generically."""
    from django.contrib.auth.decorators import login_required

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


class _PluginRoutes(URLResolver):
    """The plugin's own urlconf, loaded lazily, contributing to THIS namespace.

    ``scitex_storage`` is an OPTIONAL package, so this module must stay
    import-safe when it is absent (same discipline as ``views.py``'s lazy
    imports — a module-level ``from scitex_storage... import`` aborts test
    COLLECTION with ``ModuleNotFoundError``). The plugin urlconf is
    therefore imported inside :attr:`url_patterns`, i.e. on first URL
    resolve/reverse — by which time the mount gate
    (``_scitex_storage_installed`` in config/urls.py) has guaranteed the
    package is present.

    No namespace of its own: the plugin routes resolve and reverse as
    ``scitex_storage:<plugin-declared name>`` (``sunburst``, ``fleet``,
    ``api/list``, ...), exactly as if the plugin urlconf were mounted
    directly. No view symbol is named anywhere in this module.
    """

    def __init__(self):
        super().__init__(RoutePattern(""), "scitex_storage._django.urls")

    @cached_property
    def url_patterns(self):  # noqa: D102 — Django resolver protocol
        from scitex_storage._django import urls as plugin_urls

        return [_wrap_login(p) for p in plugin_urls.urlpatterns]


urlpatterns = [
    path("", views.index, name="index"),
    path("healthz", views.healthz, name="healthz"),
    _PluginRoutes(),
]

# EOF
