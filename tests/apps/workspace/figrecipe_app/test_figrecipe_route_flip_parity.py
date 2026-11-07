#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: tests/apps/workspace/figrecipe_app/test_figrecipe_route_flip_parity.py
"""Cutover (CCT-2784) + old-direct rule (CCT 2763/2764) + RED START (CCT 2806).

/apps/figrecipe/ serves the LEAF and ONLY the leaf (login-gated wrapper in
urls/figrecipe_django.py). The pre-cutover hub-native routes (adapter page +
SITE-2 guarded API) live ONLY at /apps/figrecipe/old-direct/ in dev — never
in production, no tiles/links, no user path, deleted outright once v1 parity
closes. RED START (binding): the plain hub-side routes went dark FIRST (404)
and the plain route is relit ONLY by the working leaf plugin — no app earns
its route back without one. Scholar #1074 template; NO /v2/-style alias is
added here (CCT 2795 lesson: transitional scaffolding, deleted not kept).

STANDING CUTOVER RULE (CCT 2768, operator, binding): every listed app serves
ONLY via its leaf plugin. Default = leaf; old hub-side = old-direct dev-only
(this file); anything unmigrated = 404 — no path may silently serve hub-side
content for a listed app in production. Target model: hub is an empty shell +
App Store; official apps are published by scitex.ai/ywatanabe and installed
by ywatanabe.

FIGRECIPE DIFFERENCES FROM SCHOLAR (same template, three deltas):

* The leaf urlconf carries a ``<path:endpoint>`` catch-all, so config/urls.py
  splices the old-direct mount BEFORE the default (pinned by
  test_old_direct_is_listed_before_the_default) — scholar's leaf has no
  catch-all and lists the default first. A default-first order would swallow
  every old-direct URL into the leaf dispatcher.
* The leaf publishes every hub route ("" page, "figrecipe/" + nested API),
  so the parity surface resolves at BOTH the root (leaf) and old-direct
  (hub) — the off-user-path assertion is that no HUB view answers at the
  root, not a bare 404.
* The default's file containment is leaf-side (SDK project authority +
  ``prepare_request`` jail, manifest ``mount_policy`` figrecipe#456); the hub
  SITE-2 guard stays authoritative for old-direct until SAC-manager sign-off.
  The guard itself is pinned end-to-end by the retargeted
  tests/security/test_figrecipe_wrapper_authorization.py, not here.

WHAT EACH TEST PINS
  default_root_serves_the_leaf      /apps/figrecipe/ resolves into the
                                    figrecipe-leaf namespace (the flip).
  every_leaf_route_mounted_at_root  each route the leaf publishes resolves
                                    at /apps/figrecipe/<route> (derived from
                                    the leaf urlconf itself, so a new
                                    upstream route is covered for free).
  every_root_leaf_route_is_gated     anonymous requests to the root-mounted
                                    leaf 302 to login — never 200, never raw.
  gated_wrapper_is_not_the_raw_view the mounted callbacks wrap the leaf's
                                    own views (structural pair to the 302).
  leaf_is_mounted_once_no_alias     the wrapper contributes exactly one
                                    mount; /apps/figrecipe/v2/ resolves to NO
                                    alias namespace and NO hub view (the v2/
                                    remainder is just an opaque string to the
                                    leaf catch-all, never a hub route).
  skill_route_resolves_to_leaf      the assistant's figrecipe url_route
                                    reverses to the leaf nested API mount
                                    (llm_app.E001 companion).
  old_direct_serves_the_legacy_surface  the pre-cutover hub routes ("",
                                    "figrecipe/", nested API sample) resolve
                                    under /apps/figrecipe/old-direct/ with
                                    the dev gate on, to hub views under the
                                    legacy namespace.
  old_direct_keeps_its_gates        anonymous requests to old-direct 302
                                    (page -> signup, API -> login), never raw.
  old_direct_is_listed_before_the_default  the mount order the leaf
                                    catch-all forces (see above).
  legacy_views_are_off_the_user_path  those same hub routes are NOT served
                                    by any hub view at /apps/figrecipe/<route>
                                    anymore (the leaf serves them there).
  old_direct_never_ships_without_the_gate  old-direct answers nothing in
                                    the ambient prod-shaped suite.
  old_direct_gate_truth_table       the dev gate: DEBUG on, prod off,
                                    explicit-flag escape hatch.
  broken_leaf_is_fail_closed        leaf unimportable -> figrecipe_django
                                    contributes [] (root urlconf still
                                    imports — the #687 outage shape) and the
                                    user path 404s; old-direct still serves
                                    the legacy reference in dev.

NO DATABASE. Resolving a URL and calling the callback with an explicitly
anonymous request tests exactly one thing — is THIS view gated — following
test_scholar_leaf_mount_is_authenticated.py.
"""

from __future__ import annotations

import importlib
import importlib.util
import re
import sys

import pytest
from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory
from django.test.utils import override_settings
from django.urls import resolve
from django.urls.exceptions import Resolver404

ROOT = "/apps/figrecipe/"
OLD_DIRECT = "/apps/figrecipe/old-direct/"

pytestmark = pytest.mark.skipif(
    importlib.util.find_spec("figrecipe._django.urls") is None,
    reason="figrecipe is not installed here; the flip is meaningful only where the leaf exists",
)

import figrecipe._django.urls as _leaf_urls  # noqa: E402
import figrecipe._django.views as _leaf_views  # noqa: E402

# Derived from the leaf urlconf itself: a route added upstream is mounted at
# the root and gated without a hub change, and shows up here automatically.
LEAF_ROUTES = [str(p.pattern) for p in _leaf_urls.urlpatterns]


def _sample_url(route: str) -> str:
    """Fill path converters so a parametrized route resolves to a sample URL."""

    def _sample(match: re.Match) -> str:
        kind = match.group(1)
        if kind == "uuid":
            return "00000000-0000-0000-0000-000000000000"
        if kind == "int":
            return "1"
        return "x"

    return re.sub(r"<(uuid|int|str|slug|path):[^>]+>", _sample, route)


# The pre-cutover hub surface. The leaf publishes all of these too, so each
# resolves at BOTH the root (leaf view) and old-direct (hub view) — the flip
# moves which CODE answers, not which PATHS exist.
LEGACY_ROUTES = [
    "",  # adapter page (figure_editor)
    "figrecipe/",  # guarded editor page
    "figrecipe/api/switch",  # guarded API dispatch (sample endpoint)
]


@pytest.fixture
def anonymous_request():
    request = RequestFactory().get("/")
    request.user = AnonymousUser()
    return request


def test_default_root_serves_the_leaf():
    # Arrange
    url = ROOT
    # Act
    match = resolve(url)
    # Assert
    assert "figrecipe-leaf" in match.namespaces, (
        f"{url} resolves into {match.namespaces}, not the leaf."
    )


@pytest.mark.parametrize("route", LEAF_ROUTES)
def test_every_leaf_route_is_mounted_at_root(route):
    # Arrange
    url = ROOT + _sample_url(route)
    # Act
    match = resolve(url)
    # Assert
    assert "figrecipe-leaf" in match.namespaces, (
        f"{url} resolves into {match.namespaces}, not the leaf."
    )


@pytest.mark.parametrize("route", LEAF_ROUTES)
def test_every_root_leaf_route_is_gated(route, anonymous_request):
    # Arrange
    view = resolve(ROOT + _sample_url(route)).func
    # Act
    response = view(anonymous_request)
    # Assert
    assert response.status_code == 302, (
        f"{ROOT + route} answered {response.status_code} to an ANONYMOUS "
        "request — the leaf is publicly exposed at the cutover root."
    )
    assert "/auth/login/" in response.url or "login" in response.url, (
        f"{ROOT + route} redirected to {response.url!r}, which is not a login "
        "page — the request was diverted, not authenticated."
    )


def test_gated_root_index_wraps_the_leaf_view():
    # Arrange — the raw leaf callback, unwrapped by hub.
    raw = _leaf_views.editor_page
    # Act
    mounted = resolve(ROOT).func
    # Assert — two hub layers: mount-marker injection outside,
    # login_required innermost (the only decorator _gated applies beneath).
    assert mounted is not raw, (
        "the cutover root mounts the leaf RAW."
    )
    inner = getattr(mounted, "__wrapped__", None)
    assert inner is not None and inner is not raw, (
        "the cutover root lost the login_required layer."
    )
    assert getattr(inner, "__wrapped__", None) is raw, (
        "the cutover root does not wrap the leaf editor with login_required."
    )


def test_gated_nested_api_wraps_the_leaf_view():
    # Arrange — the raw leaf API dispatcher, unwrapped by hub.
    raw = _leaf_views.api_dispatch
    # Act
    mounted = resolve(ROOT + "figrecipe/api/switch").func
    # Assert — two hub layers: mount-marker injection outside,
    # login_required innermost (the only decorator _gated applies beneath).
    assert mounted is not raw, (
        "the cutover nested API mounts the leaf RAW."
    )
    inner = getattr(mounted, "__wrapped__", None)
    assert inner is not None and inner is not raw, (
        "the cutover nested API lost the login_required layer."
    )
    assert getattr(inner, "__wrapped__", None) is raw, (
        "the cutover nested API does not wrap the leaf dispatcher with login_required."
    )


def test_leaf_is_mounted_once_no_alias():
    # Arrange — the wrapper's own contribution (CCT 2795 lesson: no alias).
    import apps.workspace.figrecipe_app.urls.figrecipe_django as wrapper

    # Act / Assert — exactly one mount: the cutover default at "".
    assert len(wrapper.urlpatterns) == 1, (
        f"the leaf wrapper mounts {len(wrapper.urlpatterns)} patterns — "
        "the leaf must be mounted ONCE, with no alias mount."
    )
    # Arrange — a v2-style path must resolve to NO hub view and NO alias
    # namespace (the remainder is an opaque string to the leaf catch-all).
    url = "/apps/figrecipe/v2/" + _sample_url("<path:endpoint>")
    # Act
    try:
        match = resolve(url)
    except Resolver404:
        return
    # Assert
    assert "figrecipe-leaf-v2" not in match.namespaces, (
        f"{url} serves a v2 alias namespace — aliases are deleted, not kept."
    )
    assert match.namespaces != ["figrecipe_app"], (
        f"{url} is served by hub-side figrecipe under the legacy namespace."
    )
    assert not match.func.__module__.startswith("apps.workspace.figrecipe_app"), (
        f"{url} is served by hub-side figrecipe {match.func}."
    )


def test_skill_route_resolves_to_leaf():
    # Arrange — the assistant's figrecipe url_route (llm_app.E001 companion):
    # the leaf root page, which keeps the established hosted "figure_editor"
    # name (the leaf names "" both "editor" and "figure_editor").
    from django.urls import reverse

    # Act
    page_url = reverse("figrecipe-leaf:figure_editor")
    api_base = reverse("figrecipe-leaf:figrecipe_editor")
    # Assert — the page serves the cutover root; the nested mount (the SPA's
    # API base, what views._stx_mount derives) keeps the hosted prefix.
    assert page_url == "/apps/figrecipe/", page_url
    assert api_base == "/apps/figrecipe/figrecipe/", api_base


def _resolve_with_gate(routes, flag=True):
    """Resolve `routes` against the REAL root urlconf with the gate forced."""
    import config.urls as root_urlconf
    from django.urls.resolvers import RoutePattern, URLResolver

    try:
        if flag:
            with override_settings(FIGRECIPE_OLD_DIRECT_ENABLED=True):
                reloaded = importlib.reload(root_urlconf)
                resolver = URLResolver(RoutePattern(""), reloaded.urlpatterns)
                return [resolver.resolve(r) for r in routes]
        else:
            with override_settings(DEBUG=False, FIGRECIPE_OLD_DIRECT_ENABLED=False):
                reloaded = importlib.reload(root_urlconf)
                resolver = URLResolver(RoutePattern(""), reloaded.urlpatterns)
                out = []
                for r in routes:
                    try:
                        out.append(resolver.resolve(r))
                    except Resolver404:
                        out.append(None)
                return out
    finally:
        importlib.reload(root_urlconf)


@pytest.mark.parametrize("route", LEGACY_ROUTES)
def test_old_direct_serves_the_legacy_surface(route):
    # Arrange — the REAL root urlconf reloaded with the explicit dev flag on
    # (the suite runs prod-shaped: pytest-django forces DEBUG=False, so the
    # mount is absent unless the flag opts in — exactly the rule). The
    # restore reload runs AFTER the override exits, so a later test never
    # inherits a gated urlconf from here.
    # Act
    (match,) = _resolve_with_gate(["apps/figrecipe/old-direct/" + route])
    # Assert — the reference serves the legacy surface under the legacy app
    # namespace (the old-direct mount defaults its instance namespace to the
    # app_name, exactly like the pre-cutover user-path mount did).
    assert match.namespaces == ["figrecipe_app"], (
        f"old-direct/{route} resolves into {match.namespaces}."
    )
    assert match.func.__module__.startswith("apps.workspace.figrecipe_app"), (
        f"old-direct/{route} is not served by hub-side figrecipe: {match.func}."
    )


def test_old_direct_keeps_its_gates(anonymous_request):
    # Arrange — old-direct keeps the pre-cutover gates (page -> signup, API
    # -> login); anonymous requests never reach a view body. No database:
    # both gates fire before any project lookup.
    import config.urls as root_urlconf
    from django.urls.resolvers import RoutePattern, URLResolver

    try:
        with override_settings(FIGRECIPE_OLD_DIRECT_ENABLED=True):
            reloaded = importlib.reload(root_urlconf)
            resolver = URLResolver(RoutePattern(""), reloaded.urlpatterns)
            # Act
            page = resolver.resolve("apps/figrecipe/old-direct/").func(anonymous_request)
            api = resolver.resolve("apps/figrecipe/old-direct/figrecipe/api/switch").func(
                anonymous_request
            )
    finally:
        importlib.reload(root_urlconf)
    # Assert
    assert page.status_code == 302 and "/auth/signup/" in page.url, (
        f"old-direct page answered {page.status_code} to anonymous — the adapter gate broke."
    )
    assert api.status_code == 302 and "login" in api.url, (
        f"old-direct API answered {api.status_code} to anonymous — the SITE-2 wrapper lost login."
    )


def test_old_direct_is_listed_before_the_default():
    # Arrange — the REAL root urlconf reloaded with the explicit dev flag on.
    # The leaf urlconf carries a <path:endpoint> catch-all: with a
    # default-first order, resolving an old-direct URL would match the
    # default resolver first and dispatch "old-direct/..." as a leaf API
    # endpoint, shadowing the parity reference. (Scholar lists the default
    # first — its leaf has no catch-all — so this order pin is figrecipe's.)
    import config.urls as root_urlconf

    try:
        with override_settings(FIGRECIPE_OLD_DIRECT_ENABLED=True):
            reloaded = importlib.reload(root_urlconf)
            routes = [str(p.pattern) for p in reloaded.urlpatterns]
            # Act
            old_direct_idx = routes.index("apps/figrecipe/old-direct/")
            default_idx = routes.index("apps/figrecipe/")
    finally:
        importlib.reload(root_urlconf)
    # Assert
    assert old_direct_idx < default_idx, (
        "old-direct is listed AFTER the default — the leaf catch-all shadows it."
    )


@pytest.mark.parametrize("route", LEGACY_ROUTES)
def test_legacy_views_are_off_the_user_path(route):
    # Arrange — CCT 2763/2764: no user path for hub-side routes. The leaf
    # publishes all of these paths, so they resolve at the root — the
    # assertion is that no HUB view answers, not a bare 404. Unmatched
    # /apps/* paths fall through to the pre-existing project_app catch-all.
    url = ROOT + route
    # Act
    try:
        match = resolve(url)
    except Resolver404:
        return
    # Assert — the leaf serves the user path now; hub-side code must not.
    assert match.namespaces != ["figrecipe_app"], (
        f"{url} is served by hub-side figrecipe under the legacy namespace."
    )
    assert not match.func.__module__.startswith("apps.workspace.figrecipe_app"), (
        f"{url} is served by hub-side figrecipe {match.func}."
    )


@pytest.mark.parametrize("route", LEGACY_ROUTES)
def test_old_direct_never_ships_without_the_gate(route):
    # CCT 2763/2764: old-direct NEVER ships in production. This test rebuilds
    # the REAL root urlconf under explicit prod-shaped settings (DEBUG off,
    # no flag) and resolves against the FRESH patterns — it never reads the
    # suite's ambient urlconf module.
    #
    # WHY NOT AMBIENT resolve(): the gate is evaluated ONCE, at import time
    # of config/urls (measured on scholar: all params failed on CI legs while
    # green locally). pytest-django's session fixture flips DEBUG to False only
    # AFTER collection, so in a full-suite worker config/urls is first
    # imported with settings_dev's DEBUG=True and old-direct baked in — and
    # Django's get_resolver is functools.cached, so the gate-on resolver
    # persists for the process. The gate predicate itself is correct
    # (production has DEBUG False and no flag, so the mount is [] there —
    # see test_old_direct_gate_truth_table); the ambient assertion was what
    # was wrong. Resolving against explicitly prod-shaped fresh patterns
    # tests the rule, not the worker's import history.
    # Act
    (match,) = _resolve_with_gate(["apps/figrecipe/old-direct/" + route], flag=False)
    if match is None:
        return
    # Assert — old-direct must not answer; the catch-all may, figrecipe may not.
    # (The leaf's <path:endpoint> catch-all still MATCHES the string and
    # dispatches it as an opaque endpoint — which the leaf 404s as unknown.
    # That is the leaf answering for itself, not old-direct shipping: the
    # rule is that no HUB reference is served in production.)
    assert match.namespaces != ["figrecipe_app"], (
        f"old-direct/{route} resolves WITHOUT the gate — it ships in prod."
    )
    assert not match.func.__module__.startswith("apps.workspace.figrecipe_app"), (
        f"old-direct/{route} is served by hub-side figrecipe WITHOUT the gate: "
        f"{match.func}."
    )


def test_old_direct_gate_truth_table():
    # Arrange
    from apps.workspace.figrecipe_app.urls.legacy import old_direct_enabled

    # Act / Assert — dev on, prod off, explicit-flag escape hatch.
    with override_settings(DEBUG=True):
        assert old_direct_enabled() is True
    with override_settings(DEBUG=False):
        assert old_direct_enabled() is False
    with override_settings(DEBUG=False, FIGRECIPE_OLD_DIRECT_ENABLED=True):
        assert old_direct_enabled() is True


LEAF_MODULE = "figrecipe._django.urls"
_ABSENT = object()


@pytest.fixture
def module_with_broken_leaf():
    """Reload figrecipe_django with the leaf genuinely unimportable, then restore.

    Same real-import-system technique as scholar: binding sys.modules to None
    makes `import` raise ImportError for real.
    """
    import apps.workspace.figrecipe_app.urls.figrecipe_django as module

    saved = sys.modules.get(LEAF_MODULE, _ABSENT)
    sys.modules[LEAF_MODULE] = None
    try:
        yield importlib.reload(module)
    finally:
        if saved is _ABSENT:
            sys.modules.pop(LEAF_MODULE, None)
        else:
            sys.modules[LEAF_MODULE] = saved
        importlib.reload(module)


def test_broken_leaf_is_fail_closed(module_with_broken_leaf):
    """Leaf missing -> user path 404s; the urlconf still imports; old-direct stands."""
    # Arrange
    from django.urls.resolvers import RoutePattern, URLResolver

    from apps.workspace.figrecipe_app.urls.legacy import (
        urlpatterns as legacy_patterns,
    )

    # Reaching the module at all proves the root urlconf still imports
    # (the #687 outage shape: one leaf's skew must not 500 the whole site).
    assert module_with_broken_leaf.urlpatterns == []
    # Act — user path with no leaf contributes nothing (CCT 2768: NO silent
    # hub-side fallback — the plain route stays dark, it is not relit with
    # hub views)...
    user_resolver = URLResolver(
        RoutePattern("apps/figrecipe/"), module_with_broken_leaf.urlpatterns
    )
    with pytest.raises(Resolver404):
        user_resolver.resolve("")
    # ...while the dev reference still serves the legacy surface.
    ref_resolver = URLResolver(RoutePattern("old-direct/"), legacy_patterns)
    # Assert
    for route in LEGACY_ROUTES:
        assert ref_resolver.resolve("old-direct/" + route) is not None, (
            f"old-direct lost the parity reference for {route}."
        )
