#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: tests/apps/scholar_app/test_scholar_route_flip_parity.py
"""Cutover (CCT 2760) + old-direct rule (CCT 2763/2764) + RED START (CCT 2806).

/apps/scholar/ serves the LEAF and ONLY the leaf (login-gated). The
pre-cutover hub-native routes live ONLY at /apps/scholar/old-direct/ in
dev — never in production, no tiles/links, no user path, deleted outright
once v1 parity closes. RED START (binding, supersedes the gradual flip):
the plain hub-side routes went dark FIRST (404) and the plain route is
relit ONLY by the working leaf plugin — no app earns its route back
without one. CCT 2795: NO /v2/ alias remains (transitional scaffolding
only, deleted — no live caller needed it).

STANDING CUTOVER RULE (CCT 2768, operator, binding): every listed app serves
ONLY via its leaf plugin. Default = leaf; old hub-side = old-direct dev-only
(this file); anything unmigrated = 404 — no path may silently serve hub-side
content for a listed app in production. Target model: hub is an empty shell +
App Store; official apps are published by scitex.ai/ywatanabe and installed
by ywatanabe.

WHAT EACH TEST PINS
  default_root_serves_the_leaf      /apps/scholar/ resolves into the
                                    scholar-leaf namespace (the flip).
  every_leaf_route_mounted_at_root  each route the leaf publishes resolves
                                    at /apps/scholar/<route> (derived from
                                    the leaf urlconf itself, so a new
                                    upstream route is covered for free).
  every_root_leaf_route_is_gated     anonymous requests to the root-mounted
                                    leaf 302 to login — never 200, never raw
                                    (fail-closed; SITE-3 lesson).
  gated_wrapper_is_not_the_raw_view the mounted callback wraps the leaf's
                                    own view (structural pair to the 302).
  no_v2_alias_remains               /apps/scholar/v2/ resolves to NO
                                    scholar view anymore (CCT 2795: the
                                    compat alias is deleted, not kept).
  old_direct_serves_the_parity_gap  the v1 parity surface the leaf does NOT
                                    publish yet (search page, save-to-library,
                                    PDF download, library, bibtex,
                                    citation-graph) resolves under
                                    /apps/scholar/old-direct/ with the dev
                                    gate on (suite runs prod-shaped, so the
                                    test reloads the real root urlconf with
                                    the explicit flag).
  legacy_routes_are_off_the_user_path  those same hub-native paths are NOT
                                    served by any scholar view at
                                    /apps/scholar/<route> anymore.
  old_direct_never_ships_without_the_gate  old-direct answers nothing in
                                    the ambient prod-shaped suite.
  old_direct_gate_truth_table       the dev gate: DEBUG on, prod off,
                                    explicit-flag escape hatch.
  broken_leaf_is_fail_closed        leaf unimportable -> scholar_django
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

ROOT = "/apps/scholar/"
# CCT 2795: the v2/ compat alias is deleted, not kept — no V2 constant, no
# alias test. no_v2_alias_remains below pins the deletion.
OLD_DIRECT = "/apps/scholar/old-direct/"

pytestmark = pytest.mark.skipif(
    importlib.util.find_spec("scitex_scholar._django.urls") is None,
    reason="scitex-scholar is not installed here; the flip is meaningful only where the leaf exists",
)

import scitex_scholar._django.urls as _leaf_urls  # noqa: E402
import scitex_scholar._django.views as _leaf_views  # noqa: E402

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


# The v1 parity gap: hub-native routes the leaf does not publish yet. Each
# must resolve under old-direct (dev) until the parity card retires it.
PARITY_GAP_ROUTES = [
    "search/",  # legacy search page (scholar_search)
    "api/search/",  # legacy unified search API
    "api/save-paper/",  # save-to-library
    "api/papers/save-bulk/",  # save-to-library (bulk)
    "api/pdf/download/",  # PDF download (leaf has NO pdf route)
    "api/pdf/serve/",  # PDF serve
    "api/library/papers/",  # legacy personal library
    "bibtex/enrichment/",  # bibtex page
    "api/import/bibtex/",  # library "Import BibTeX (.bib)" posts here
    "citation-graph/network/",  # hub citation-graph
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
    assert "scholar-leaf" in match.namespaces, (
        f"{url} resolves into {match.namespaces}, not the leaf."
    )


@pytest.mark.parametrize("route", LEAF_ROUTES)
def test_every_leaf_route_is_mounted_at_root(route):
    # Arrange
    url = ROOT + _sample_url(route)
    # Act
    match = resolve(url)
    # Assert
    assert "scholar-leaf" in match.namespaces, (
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
    raw = _leaf_views.index
    # Act
    mounted = resolve(ROOT).func
    # Assert
    assert mounted is not raw, (
        "the cutover root mounts the leaf RAW — SITE 3 all over again."
    )
    assert getattr(mounted, "__wrapped__", None) is raw, (
        "the cutover root does not wrap the leaf index with login_required."
    )


@pytest.mark.parametrize("route", LEAF_ROUTES)
def test_no_v2_alias_remains(route):
    # CCT 2795: the v2/ compat alias was transitional scaffolding only and
    # is deleted, not kept. Every leaf route resolves at the plain root; the
    # v2/ path must resolve to NO scholar view (leaf or hub-side) — unmatched
    # /apps/* paths fall through to the pre-existing project_app catch-all.
    # Arrange
    url = "/apps/scholar/v2/" + _sample_url(route)
    # Act
    try:
        match = resolve(url)
    except Resolver404:
        return
    # Assert
    assert "scholar-leaf" not in match.namespaces, (
        f"{url} still serves the leaf under a v2 alias — CCT 2795 deleted it."
    )
    assert "scholar-leaf-v2" not in match.namespaces, (
        f"{url} still serves the deleted scholar-leaf-v2 namespace."
    )
    assert match.namespaces != ["scholar_app"], (
        f"{url} is served by hub-side scholar under the legacy namespace."
    )
    assert not match.func.__module__.startswith("apps.workspace.scholar_app"), (
        f"{url} is served by hub-side scholar {match.func}."
    )


@pytest.mark.parametrize("route", PARITY_GAP_ROUTES)
def test_old_direct_serves_the_parity_gap(route):
    # Arrange — the REAL root urlconf reloaded with the explicit dev flag on
    # (the suite runs prod-shaped: pytest-django forces DEBUG=False, so the
    # mount is absent unless the flag opts in — exactly the rule). The
    # restore reload runs AFTER the override exits, so a later test never
    # inherits a gated urlconf from here.
    import config.urls as root_urlconf
    from django.urls.resolvers import RoutePattern, URLResolver

    try:
        with override_settings(SCHOLAR_OLD_DIRECT_ENABLED=True):
            reloaded = importlib.reload(root_urlconf)
            resolver = URLResolver(RoutePattern(""), reloaded.urlpatterns)
            # Act
            match = resolver.resolve("apps/scholar/old-direct/" + route)
    finally:
        importlib.reload(root_urlconf)
    # Assert — the reference serves the gap under the legacy app namespace
    # (the old-direct mount defaults its instance namespace to the app_name,
    # exactly like the pre-cutover user-path mount did).
    assert match.namespaces == ["scholar_app"], (
        f"old-direct/{route} resolves into {match.namespaces}."
    )
    assert match.func.__module__.startswith("apps.workspace.scholar_app"), (
        f"old-direct/{route} is not served by hub-side scholar: {match.func}."
    )


def test_legacy_redirect_names_still_reverse_to_old_direct():
    # Arrange — the real root urlconf reloaded with the explicit dev flag on.
    # The legacy views call redirect("scholar_app:...") (api_key_views,
    # bibtex download/upload); those names must reverse, to old-direct URLs.
    import config.urls as root_urlconf
    from django.urls import reverse

    try:
        with override_settings(SCHOLAR_OLD_DIRECT_ENABLED=True):
            reloaded = importlib.reload(root_urlconf)
            # Act
            url = reverse("scholar_app:api_keys", urlconf=reloaded)
    finally:
        importlib.reload(root_urlconf)
    # Assert
    assert url == "/apps/scholar/old-direct/api-keys/", url


@pytest.mark.parametrize("route", PARITY_GAP_ROUTES)
def test_legacy_routes_are_off_the_user_path(route):
    # Arrange — CCT 2763/2764: no user path for hub-side routes. Unmatched
    # /apps/* paths fall through to the pre-existing project_app catch-all;
    # the assertion is that no SCHOLAR view answers, not a bare 404.
    url = ROOT + route
    # Act
    try:
        match = resolve(url)
    except Resolver404:
        return
    # Assert — no scholar view answers on the user path (unmatched /apps/*
    # paths fall through to the pre-existing project_app catch-all).
    assert match.namespaces != ["scholar_app"], (
        f"{url} is served by hub-side scholar under the legacy namespace."
    )
    assert not match.func.__module__.startswith("apps.workspace.scholar_app"), (
        f"{url} is served by hub-side scholar {match.func}."
    )


@pytest.mark.parametrize("route", PARITY_GAP_ROUTES)
def test_old_direct_never_ships_without_the_gate(route):
    # CCT 2763/2764: old-direct NEVER ships in production. This test rebuilds
    # the REAL root urlconf under explicit prod-shaped settings (DEBUG off,
    # no flag) and resolves against the FRESH patterns — it never reads the
    # suite's ambient urlconf module.
    #
    # WHY NOT AMBIENT resolve(): the gate is evaluated ONCE, at import time
    # of config/urls (measured: all 10 params failed on CI legs while green
    # locally). pytest-django's session fixture flips DEBUG to False only
    # AFTER collection, so in a full-suite worker config/urls is first
    # imported with settings_dev's DEBUG=True and old-direct baked in — and
    # Django's get_resolver is functools.cached, so the gate-on resolver
    # persists for the process. The gate predicate itself is correct
    # (production has DEBUG False and no flag, so the mount is [] there —
    # see test_old_direct_gate_truth_table); the ambient assertion was what
    # was wrong. Resolving against explicitly prod-shaped fresh patterns
    # tests the rule, not the worker's import history.
    import config.urls as root_urlconf
    from django.urls.resolvers import RoutePattern, URLResolver

    try:
        with override_settings(DEBUG=False, SCHOLAR_OLD_DIRECT_ENABLED=False):
            reloaded = importlib.reload(root_urlconf)
            resolver = URLResolver(RoutePattern(""), reloaded.urlpatterns)
            # Act
            try:
                match = resolver.resolve("apps/scholar/old-direct/" + route)
            except Resolver404:
                return
    finally:
        importlib.reload(root_urlconf)
    # Assert — old-direct must not answer; the catch-all may, scholar may not.
    assert match.namespaces != ["scholar_app"], (
        f"old-direct/{route} resolves WITHOUT the gate — it ships in prod."
    )
    assert not match.func.__module__.startswith("apps.workspace.scholar_app"), (
        f"old-direct/{route} is served by hub-side scholar WITHOUT the gate: "
        f"{match.func}."
    )


def test_old_direct_gate_truth_table():
    # Arrange
    from apps.workspace.scholar_app.urls.legacy import old_direct_enabled

    # Act / Assert — dev on, prod off, explicit-flag escape hatch.
    with override_settings(DEBUG=True):
        assert old_direct_enabled() is True
    with override_settings(DEBUG=False):
        assert old_direct_enabled() is False
    with override_settings(DEBUG=False, SCHOLAR_OLD_DIRECT_ENABLED=True):
        assert old_direct_enabled() is True


LEAF_MODULE = "scitex_scholar._django.urls"
_ABSENT = object()


@pytest.fixture
def module_with_broken_leaf():
    """Reload scholar_django with the leaf genuinely unimportable, then restore.

    Same real-import-system technique as
    test_scholar_leaf_mount_is_authenticated.py: binding sys.modules to None
    makes `import` raise ImportError for real.
    """
    import apps.workspace.scholar_app.urls.scholar_django as module

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

    from apps.workspace.scholar_app.urls.legacy import (
        urlpatterns as legacy_patterns,
    )

    # Reaching the module at all proves the root urlconf still imports
    # (the #687 outage shape: one leaf's skew must not 500 the whole site).
    assert module_with_broken_leaf.urlpatterns == []
    # Act — user path with no leaf contributes nothing...
    user_resolver = URLResolver(
        RoutePattern("apps/scholar/"), module_with_broken_leaf.urlpatterns
    )
    with pytest.raises(Resolver404):
        user_resolver.resolve("")
    # ...while the dev reference still serves the legacy surface.
    ref_resolver = URLResolver(RoutePattern("old-direct/"), legacy_patterns)
    # Assert
    for route in PARITY_GAP_ROUTES:
        if "<" in route:
            continue
        assert ref_resolver.resolve("old-direct/" + route) is not None, (
            f"old-direct lost the parity reference for {route}."
        )
