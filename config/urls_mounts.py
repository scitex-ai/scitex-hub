# -*- coding: utf-8 -*-
# File: config/urls_mounts.py
"""Pattern builders for the leaf-app mounts used by config/urls.py.

Split out of config/urls.py (size limit); urls.py imports them back under
the same names.
"""

from __future__ import annotations

from django.urls import include, path


def _sdk_creator_patterns():
    """URL patterns for the SDK App Creator wizard, login-gated.

    Thin-hub mount, no SDK view symbol named: scitex-sdk 0.2.0 declares no
    ``scitex.apps`` entry point, so the generic plugin mount
    (``plugin_urlpatterns``) cannot discover it and the mount is explicit.
    The whole tree is login-wrapped with the same generic wrapper the plugin
    mount uses, so a new upstream view is gated with zero hub changes. []
    when the package is absent, so the hub boots without it.
    """
    try:
        from scitex_sdk.creator import urls as creator_urls
    except ImportError:
        return []
    from apps.workspace.apps_app.services.plugin_apps import _wrap_login

    return [_wrap_login(p) for p in creator_urls.urlpatterns]


def _live_paper_patterns():
    """URL patterns for the Live Paper viewer leaf, login-gated.

    Thin-hub mount (scholar pattern): the leaf owns views through
    ``scitex_live_paper.mount(resolver=...)`` (per-request BundleContext);
    the hub owns auth (whole tree login-wrapped) and bundle resolution
    (apps.workspace.live_paper_app.mount.hub_resolver). [] when the
    package is absent, so the hub boots without it.
    """
    try:
        from apps.workspace.live_paper_app import mount as live_paper_mount
    except ImportError:
        return []
    from apps.workspace.apps_app.services.plugin_apps import _wrap_login

    return (
        [_wrap_login(p) for p in live_paper_mount.urlpatterns],
        live_paper_mount.app_namespace,
    )


def _scholar_old_direct_patterns():
    """Dev-only old-direct reference for Scholar (CCT 2763/2764 + CCT 2806).

    The pre-cutover hub-native routes at apps/scholar/old-direct/, for
    parity comparison while v1 parity is open. [] in production by rule —
    the gate lives in scholar_app/urls/legacy.py so mount and tests read
    one definition. No registry/manifest entry exists for old-direct, so
    no launcher tile or link can render it. Per-app template for the RED
    START sequence (plain goes dark first, relit only by a working leaf;
    CCT 2795: no /v2/ alias remains).
    """
    from apps.workspace.scholar_app.urls.legacy import (
        old_direct_enabled,
    )
    from apps.workspace.scholar_app.urls.legacy import (
        urlpatterns as legacy_patterns,
    )

    if not old_direct_enabled():
        return []
    # No explicit instance namespace ON PURPOSE: it defaults to the
    # app_name ("scholar_app"), byte-identical to the pre-cutover user-path
    # mount — so the legacy views' redirect("scholar_app:...") calls keep
    # resolving, now to old-direct URLs. That is exactly what a parity
    # reference should be: the old tree, same names, different prefix.
    return [
        path(
            "apps/scholar/old-direct/",
            include((legacy_patterns, "scholar_app")),
        ),
    ]


def _figrecipe_old_direct_patterns():
    """Dev-only old-direct reference for FigRecipe (CCT 2763/2764 + CCT 2806).

    The pre-cutover hub-native routes at apps/figrecipe/old-direct/, for
    parity comparison while v1 parity is open. [] in production by rule —
    the gate lives in figrecipe_app/urls/legacy.py so mount and tests read
    one definition. No registry/manifest entry exists for old-direct, so
    no launcher tile or link can render it. Scholar #1074 template.

    ORDER MATTERS (figrecipe-only): this list is spliced BEFORE the default
    mount below. The leaf urlconf carries a ``<path:endpoint>`` catch-all,
    so a default-first order would swallow every old-direct URL into the
    leaf dispatcher (scholar's leaf has no catch-all, which is why scholar
    can list the default first).
    """
    from apps.workspace.figrecipe_app.urls.legacy import (
        old_direct_enabled,
    )
    from apps.workspace.figrecipe_app.urls.legacy import (
        urlpatterns as legacy_patterns,
    )

    if not old_direct_enabled():
        return []
    # No explicit instance namespace ON PURPOSE: it defaults to the
    # app_name ("figrecipe_app"), byte-identical to the pre-cutover user-path
    # mount — so the adapter's reverse() calls keep resolving, now to
    # old-direct URLs. That is exactly what a parity reference should be:
    # the old tree, same names, different prefix.
    return [
        path(
            "apps/figrecipe/old-direct/",
            include((legacy_patterns, "figrecipe_app")),
        ),
    ]


def _writer_old_direct_patterns():
    """Dev-only old-direct reference for Writer (CCT 2763/2764 + CCT 2806).

    The pre-cutover hub-native routes at apps/writer/old-direct/, for
    parity comparison while v1 parity is open. [] in production by rule —
    the gate lives in writer_app/urls/legacy.py so mount and tests read
    one definition. No registry/manifest entry exists for old-direct, so
    no launcher tile or link can render it. Scholar #1074 / FigRecipe #1075
    template.

    ORDER MATTERS: the leaf urlconf carries a ``<path:endpoint>`` catch-all,
    so the generic plugin mount (``plugin_urlpatterns``) hoists this hub
    sub-route AHEAD of the leaf mount at apps/writer/; mounted after it,
    every old-direct URL would be swallowed by the leaf dispatcher.
    """
    from apps.workspace.writer_app.urls.legacy import (
        old_direct_enabled,
    )
    from apps.workspace.writer_app.urls.legacy import (
        urlpatterns as legacy_patterns,
    )

    if not old_direct_enabled():
        return []
    # No explicit instance namespace ON PURPOSE: it defaults to the
    # app_name ("writer_app"), byte-identical to the pre-cutover user-path
    # mount — so the hub views' reverse("writer_app:...") calls keep
    # resolving, now to old-direct URLs. That is exactly what a parity
    # reference should be: the old tree, same names, different prefix.
    return [
        path(
            "apps/writer/old-direct/",
            include((legacy_patterns, "writer_app")),
        ),
    ]


# EOF
