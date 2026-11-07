#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: tests/apps/workspace/writer_app/test_writer_route_flip_parity.py
"""Cutover + old-direct rule (CCT 2763/2764) + RED START (CCT 2806).

/apps/writer/ serves the LEAF and ONLY the leaf (SITE-3 wrapper in
urls/writer_django.py). The pre-cutover hub-native routes (feature pages +
v2 SITE-3 paths) live ONLY at /apps/writer/old-direct/ in dev — never in
production, no tiles/links, no user path, deleted outright once v1 parity
closes. RED START (binding): the plain hub-side routes went dark FIRST
(404) and the plain route is relit ONLY by the working leaf plugin — no app
earns its route back without one. Scholar #1074 / FigRecipe #1075 template;
NO /v2/-style alias is added (CCT 2795 lesson: transitional scaffolding,
deleted not kept).

STANDING CUTOVER RULE (CCT 2768, operator, binding): every listed app serves
ONLY via its leaf plugin. Default = leaf; old hub-side = old-direct
dev-only (this file); anything unmigrated = 404 — no path may silently
serve hub-side content for a listed app in production.

WRITER DIFFERENCES FROM SCHOLAR/FIGRECIPE (same template, three deltas):

* The leaf urlconf carries a ``<path:endpoint>`` catch-all, so
  config/urls.py splices the old-direct mount BEFORE the default (pinned by
  test_old_direct_is_listed_before_the_default) — scholar's leaf has no
  catch-all and lists the default first. A default-first order would swallow
  every old-direct URL into the leaf dispatcher.
* The default's `working_dir` containment stays HUB-side (SITE-3
  WorkingDirScopedView + login + Origin check, rebound to the leaf paths —
  see writer_django.py for why the leaf's jail declaration does not carry
  the default yet). The cutover therefore pins WHICH leaf routes get the
  injection vs the leaf's own project-boundary authorization
  (test_known_leaf_routes_have_a_defined_treatment), not just that the
  root is gated.
* The old-direct v2 reference is leaf-BACKED (the SITE-3 views over leaf
  views), so a broken leaf darkens v2 everywhere — pinned by
  test_broken_leaf_is_fail_closed. The hub-native feature surface still
  serves as the parity reference.

WHAT EACH TEST PINS
  default_root_serves_the_leaf      /apps/writer/ resolves into the
                                    writer-leaf namespace (the flip).
  every_leaf_route_mounted_at_root  each route the leaf publishes resolves
                                    at /apps/writer/<route> (derived from
                                    the leaf urlconf itself, so a new
                                    upstream route is covered for free).
  every_root_leaf_route_is_gated    anonymous requests to the root-mounted
                                    leaf 302 to login — never 200, never raw.
  site3_routes_rebind_the_guard     the `?working_dir=`-reading leaf routes
                                    are served by hub's SITE-3 views (same
                                    function objects as the v2 reference),
                                    never the raw leaf callbacks.
  leaf_authorized_routes_keep_login every OTHER known leaf route is
                                    login-wrapped in place with the leaf's
                                    csrf decision preserved.
  known_leaf_routes_have_a_defined_treatment  the installed leaf's route
                                    names are all classified (SITE-3 vs
                                    leaf-authorized); an unclassified
                                    upstream addition fails loudly here
                                    (it is omitted fail-closed at runtime).
  leaf_is_mounted_once_no_alias     the wrapper contributes exactly one
                                    mount; a v2-shaped path at the root
                                    dispatches through the SITE-3 API guard
                                    (leaf catch-all), never a v2 alias
                                    route or the legacy namespace.
  skill_route_resolves_to_leaf      the assistant's writer url_route
                                    reverses to the leaf editor
                                    (llm_app.E001 companion).
  old_direct_serves_the_legacy_surface  the pre-cutover hub routes resolve
                                    under /apps/writer/old-direct/ with
                                    the dev gate on, under the legacy
                                    namespace.
  old_direct_keeps_its_gates        anonymous requests to old-direct 302
                                    (index page -> signup, v2 viewer ->
                                    login), never raw.
  old_direct_is_listed_before_the_default  the mount order the leaf
                                    catch-all forces (see above).
  legacy_views_are_off_the_user_path  those same hub routes are NOT served
                                    under the legacy namespace at
                                    /apps/writer/<route> anymore (the leaf
                                    mount serves them there; hub's SITE-3
                                    guard functions serve the leaf paths by
                                    design, never the legacy namespace).
  old_direct_never_ships_without_the_gate  old-direct answers nothing in
                                    the ambient prod-shaped suite.
  old_direct_gate_truth_table       the dev gate: DEBUG on, prod off,
                                    explicit-flag escape hatch.
  broken_leaf_is_fail_closed        leaf unimportable -> writer_django
                                    contributes [] for BOTH the leaf mount
                                    and the leaf-backed v2 (root urlconf
                                    still imports — the #687 outage shape)
                                    and the user path 404s; the hub-native
                                    old-direct surface still serves.

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

ROOT = "/apps/writer/"
OLD_DIRECT = "/apps/writer/old-direct/"

pytestmark = pytest.mark.skipif(
    importlib.util.find_spec("scitex_writer._django.urls") is None,
    reason="scitex-writer is not installed here; the flip is meaningful only where the leaf exists",
)

import scitex_writer._django.urls as _leaf_urls  # noqa: E402
import scitex_writer._django.views as _leaf_views  # noqa: E402
import apps.workspace.writer_app.urls.writer_django as _wrapper  # noqa: E402

# Derived from the leaf urlconf itself: a route added upstream is mounted at
# the root and gated without a hub change, and shows up here automatically.
LEAF_ROUTES = [str(p.pattern) for p in _leaf_urls.urlpatterns]
LEAF_NAMES = [p.name for p in _leaf_urls.urlpatterns]


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


# The pre-cutover hub surface, by mount prefix. Each resolves at BOTH the
# root (leaf catch-all answers) and old-direct (hub views answer) — the flip
# moves which CODE answers, not which PATHS exist.
LEGACY_ROUTES = [
    "",  # index adapter (writer_app:index)
    "editor/",  # hub editor template page
    "editor-v2/",  # SITE-3 wrapper editor
    "viewer-v2/",  # SITE-3 wrapper viewer
    "v2/ping",  # SITE-3 API dispatch (sample endpoint)
    "api/project/1/manuscript-status/",  # hub editor API (sample)
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
    assert "writer-leaf" in match.namespaces, (
        f"{url} resolves into {match.namespaces}, not the leaf."
    )


@pytest.mark.parametrize("route", LEAF_ROUTES)
def test_every_leaf_route_is_mounted_at_root(route):
    # Arrange
    url = ROOT + _sample_url(route)
    # Act
    match = resolve(url)
    # Assert
    assert "writer-leaf" in match.namespaces, (
        f"{url} resolves into {match.namespaces}, not the leaf."
    )


@pytest.mark.parametrize("route", LEAF_ROUTES)
def test_every_root_leaf_route_is_gated(route, anonymous_request):
    # Arrange
    view = resolve(ROOT + _sample_url(route)).func
    # Act
    kwargs = {}
    if "<" in route and "endpoint" in route:
        kwargs = {"endpoint": "ping"}
    elif "<int:project_id>" in route:
        kwargs = {"project_id": 1}
        if "section_name" in route:
            kwargs["section_name"] = "abstract"
    response = view(anonymous_request, **kwargs)
    # Assert
    assert response.status_code == 302, (
        f"{ROOT + route} answered {response.status_code} to an ANONYMOUS "
        "request — the leaf is publicly exposed at the cutover root."
    )
    assert "/auth/login/" in response.url or "login" in response.url, (
        f"{ROOT + route} redirected to {response.url!r}, which is not a login "
        "page — the request was diverted, not authenticated."
    )


def test_site3_routes_rebind_the_guard():
    # Arrange — the raw leaf callbacks, unwrapped by hub.
    raw = {
        "editor": _leaf_views.editor_page,
        "viewer": _leaf_views.viewer_page,
        "api": _leaf_views.api_dispatch,
    }
    hub = {
        "editor": _wrapper.editor_page,
        "viewer": _wrapper.viewer_page,
        "api": _wrapper.api_dispatch,
    }
    # Act / Assert — each `?working_dir=`-reading leaf route is served by
    # hub's SITE-3 view (the SAME function object as the old-direct v2
    # reference — byte-identical behaviour), never the raw leaf callback.
    for name, raw_cb in raw.items():
        if name not in LEAF_NAMES:
            continue  # older leaf without this route: nothing to rebind
        route = next(
            str(p.pattern)
            for p in _leaf_urls.urlpatterns
            if p.name == name
        )
        mounted = resolve(ROOT + _sample_url(route)).func
        assert mounted is not raw_cb, f"leaf route {name!r} mounts the leaf RAW."
        assert mounted is hub[name], (
            f"leaf route {name!r} is served by {mounted}, not the SITE-3 "
            f"guard {hub[name]} — the working_dir bar moved or duplicated."
        )
    # The API stays csrf_exempt HERE (its frontend sends no token; the
    # Origin check above is the CSRF bar instead) — deliberately NOT the
    # leaf's decision: the 2.43.9 leaf guards its dispatch with
    # @project_boundary (csrf_protect), and following it would 403 the
    # token-less compile POSTs (writer #1077: v2 compile CSRF sister).
    assert getattr(_wrapper.api_dispatch, "csrf_exempt", False) is True, (
        "hub api_dispatch lost csrf_exempt — leaf frontend POSTs would 403."
    )


def test_leaf_authorized_routes_keep_login():
    # Arrange — known leaf routes the leaf authorizes itself (SDK host
    # project authority + CSRF via @project_boundary): hub adds login only.
    # (Absent on leaves that predate them — 2.43.6 ships editor/viewer/api
    # only — so an empty selection still proves the rule structurally.)
    for pattern in _leaf_urls.urlpatterns:
        if pattern.name in _wrapper._SITE3_VIEW_BY_LEAF_NAME:
            continue
        if pattern.name not in _wrapper._KNOWN_LEAF_ROUTE_NAMES:
            continue  # unknown: omission is pinned by the treatment test
        # Act
        mounted = resolve(ROOT + _sample_url(str(pattern.pattern))).func
        # Assert — login-wrapped in place (wraps() chain leads to the leaf
        # callback), never raw, never a hub view for another route.
        assert mounted is not pattern.callback, (
            f"leaf route {pattern.name!r} mounts the leaf RAW."
        )
        assert getattr(mounted, "__wrapped__", None) is pattern.callback, (
            f"leaf route {pattern.name!r} does not login-wrap the leaf "
            "callback — it is served by something else entirely."
        )
        assert getattr(mounted, "csrf_exempt", False) == getattr(
            pattern.callback, "csrf_exempt", False
        ), f"leaf route {pattern.name!r} lost the leaf's csrf decision."


def test_known_leaf_routes_have_a_defined_treatment():
    # Arrange — the installed leaf's route names vs the wrapper's contract.
    # Act
    unknown = [
        name for name in LEAF_NAMES if name not in _wrapper._KNOWN_LEAF_ROUTE_NAMES
    ]
    site3 = [name for name in LEAF_NAMES if name in _wrapper._SITE3_VIEW_BY_LEAF_NAME]
    # Assert — every installed route is either classified, or a deliberately
    # unmounted v2 alias (CCT 2795: no v2 alias mount — the leaf's own
    # `<path:endpoint>` catch-all dispatches those spellings through the
    # SITE-3 API guard as opaque endpoints, pinned by
    # test_leaf_is_mounted_once_no_alias). An upstream addition OUTSIDE the
    # alias set is omitted fail-closed at runtime AND fails loudly here;
    # the SITE-3 set is exactly the `?working_dir=` readers — if the leaf
    # renames one, the injection silently stops covering it unless this
    # trips. Generation-aware: pre-2.43.9 leaves publish no twins, so the
    # expected omission is empty there.
    assert set(unknown) == _wrapper._V2_TWIN_ALIASES & set(LEAF_NAMES), (
        f"writer leaf publishes unclassified routes {unknown} — they are "
        "OMITTED fail-closed at runtime. Classify each in "
        "_KNOWN_LEAF_ROUTE_NAMES (SITE-3 injection vs leaf-authorized), or "
        "in _V2_TWIN_ALIASES when it is a deliberately unmounted v2 alias."
    )
    assert set(site3) == {"editor", "viewer", "api"} & set(LEAF_NAMES), (
        f"SITE-3 covers {site3}: a `?working_dir=` reader moved treatment "
        "without hub noticing — SITE 1 may be re-open on the default path."
    )


def test_leaf_is_mounted_once_no_alias():
    # Arrange — the wrapper's own contribution (CCT 2795 lesson: no alias).
    # Act / Assert — exactly one mount: the cutover default at "".
    assert len(_wrapper.urlpatterns) == 1, (
        f"the leaf wrapper mounts {len(_wrapper.urlpatterns)} patterns — "
        "the leaf must be mounted ONCE, with no alias mount."
    )
    # Arrange — the old v2-style path must resolve to NO alias namespace and
    # NO legacy-namespace route (the remainder is an opaque string to the
    # leaf catch-all, served by the SITE-3 API guard — never a second
    # default mount and never the old v2 route, which lives only at
    # old-direct now).
    url = "/apps/writer/editor-v2/"
    # Act
    match = resolve(url)
    # Assert
    assert "writer-leaf-v2" not in match.namespaces, (
        f"{url} serves a v2 alias namespace — aliases are deleted, not kept."
    )
    assert match.namespaces != ["writer_app"], (
        f"{url} is served by hub-side writer under the legacy namespace."
    )
    assert match.func is _wrapper.api_dispatch, (
        f"{url} is served by {match.func} — the leaf catch-all must "
        "dispatch it through the SITE-3 API guard, not a v2 alias route."
    )


def test_skill_route_resolves_to_leaf():
    # Arrange — the assistant's writer url_route (llm_app.E001 companion).
    from django.urls import reverse

    # Act
    page_url = reverse("writer-leaf:editor")
    viewer_url = reverse("writer-leaf:viewer")
    # Assert — the editor serves the cutover root; the viewer keeps its path.
    assert page_url == "/apps/writer/", page_url
    assert viewer_url == "/apps/writer/viewer/", viewer_url


def _resolve_with_gate(routes, flag=True):
    """Resolve `routes` against the REAL root urlconf with the gate forced."""
    import config.urls as root_urlconf
    from django.urls.resolvers import RoutePattern, URLResolver

    try:
        if flag:
            with override_settings(WRITER_OLD_DIRECT_ENABLED=True):
                reloaded = importlib.reload(root_urlconf)
                resolver = URLResolver(RoutePattern(""), reloaded.urlpatterns)
                return [resolver.resolve(r) for r in routes]
        else:
            with override_settings(DEBUG=False, WRITER_OLD_DIRECT_ENABLED=False):
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
    (match,) = _resolve_with_gate(["apps/writer/old-direct/" + route])
    # Assert — the reference serves the legacy surface under the legacy app
    # namespace (the old-direct mount defaults its instance namespace to the
    # app_name, exactly like the pre-cutover user-path mount did). No
    # __module__ assertion here on purpose: several legacy pages are plain
    # Django TemplateViews, whose view function carries django's own module
    # — the namespace is what proves the legacy mount serves them.
    assert match.namespaces == ["writer_app"], (
        f"old-direct/{route} resolves into {match.namespaces}."
    )


def test_old_direct_keeps_its_gates(anonymous_request):
    # Arrange — old-direct keeps the pre-cutover gates (index page ->
    # signup, v2 viewer -> login); anonymous requests never reach a view
    # body. No database: the gates fire before any project lookup.
    import config.urls as root_urlconf
    from django.urls.resolvers import RoutePattern, URLResolver

    try:
        with override_settings(WRITER_OLD_DIRECT_ENABLED=True):
            reloaded = importlib.reload(root_urlconf)
            resolver = URLResolver(RoutePattern(""), reloaded.urlpatterns)
            # Act
            page = resolver.resolve("apps/writer/old-direct/").func(anonymous_request)
            viewer = resolver.resolve("apps/writer/old-direct/viewer-v2/").func(
                anonymous_request
            )
    finally:
        importlib.reload(root_urlconf)
    # Assert
    assert page.status_code == 302 and "/auth/signup/" in page.url, (
        f"old-direct page answered {page.status_code} to anonymous — the adapter gate broke."
    )
    assert viewer.status_code == 302 and "login" in viewer.url, (
        f"old-direct viewer answered {viewer.status_code} to anonymous — the SITE-3 wrapper lost login."
    )


def test_old_direct_is_listed_before_the_default():
    # Arrange — the REAL root urlconf reloaded with the explicit dev flag on.
    # The leaf urlconf carries a <path:endpoint> catch-all: with a
    # default-first order, resolving an old-direct URL would match the
    # default resolver first and dispatch "old-direct/..." as a leaf API
    # endpoint, shadowing the parity reference. (Scholar lists the default
    # first — its leaf has no catch-all — so this order pin is
    # writer/figrecipe's.)
    import config.urls as root_urlconf

    try:
        with override_settings(WRITER_OLD_DIRECT_ENABLED=True):
            reloaded = importlib.reload(root_urlconf)
            routes = [str(p.pattern) for p in reloaded.urlpatterns]
            # Act
            old_direct_idx = routes.index("apps/writer/old-direct/")
            default_idx = routes.index("apps/writer/")
    finally:
        importlib.reload(root_urlconf)
    # Assert
    assert old_direct_idx < default_idx, (
        "old-direct is listed AFTER the default — the leaf catch-all shadows it."
    )


@pytest.mark.parametrize("route", LEGACY_ROUTES)
def test_legacy_views_are_off_the_user_path(route):
    # Arrange — CCT 2763/2764: no user path for hub-side routes. The leaf
    # catch-all publishes every unmatched path, so they resolve at the
    # root — the assertion is that the LEGACY namespace serves nothing
    # there, not a bare 404. (Writer nuance vs scholar/figrecipe: hub's
    # SITE-3 guard functions legitimately serve the root — rebound to the
    # leaf paths, inside the writer-leaf namespace. What must be gone is
    # every hub-NATIVE view: the adapter, the feature pages, the v2 paths.)
    # Unmatched /apps/* paths fall through to the pre-existing project_app
    # catch-all.
    url = ROOT + route
    # Act
    try:
        match = resolve(url)
    except Resolver404:
        return
    # Assert — the leaf mount serves the user path now; the legacy
    # namespace serves nothing on it.
    assert "writer-leaf" in match.namespaces, (
        f"{url} resolves into {match.namespaces}, not the leaf mount."
    )
    assert match.namespaces != ["writer_app"], (
        f"{url} is served by hub-side writer under the legacy namespace."
    )


@pytest.mark.parametrize("route", LEGACY_ROUTES)
def test_old_direct_never_ships_without_the_gate(route):
    # CCT 2763/2764: old-direct NEVER ships in production. This test rebuilds
    # the REAL root urlconf under explicit prod-shaped settings (DEBUG off,
    # no flag) and resolves against the FRESH patterns — it never reads the
    # suite's ambient urlconf module. (See the figrecipe twin for why the
    # ambient resolve() cannot assert this: the gate is evaluated once, at
    # import time of config/urls, and Django's get_resolver is cached.)
    # Act
    (match,) = _resolve_with_gate(["apps/writer/old-direct/" + route], flag=False)
    if match is None:
        return
    # Assert — old-direct must not answer; the catch-all may, writer may not.
    # (The leaf's <path:endpoint> catch-all still MATCHES the string and
    # dispatches it through the SITE-3 API guard as an opaque endpoint —
    # which the leaf 404s as unknown. That is the leaf mount answering for
    # itself inside writer-leaf, not old-direct shipping: the rule is that
    # the LEGACY namespace serves no reference in production.)
    assert match.namespaces != ["writer_app"], (
        f"old-direct/{route} resolves WITHOUT the gate — it ships in prod."
    )


def test_old_direct_gate_truth_table():
    # Arrange
    from apps.workspace.writer_app.urls.legacy import old_direct_enabled

    # Act / Assert — dev on, prod off, explicit-flag escape hatch.
    with override_settings(DEBUG=True):
        assert old_direct_enabled() is True
    with override_settings(DEBUG=False):
        assert old_direct_enabled() is False
    with override_settings(DEBUG=False, WRITER_OLD_DIRECT_ENABLED=True):
        assert old_direct_enabled() is True


LEAF_MODULE = "scitex_writer._django.urls"
_ABSENT = object()


@pytest.fixture
def module_with_broken_leaf():
    """Reload writer_django with the leaf genuinely unimportable, then restore.

    Same real-import-system technique as scholar/figrecipe: binding
    sys.modules to None makes `import` raise ImportError for real.
    """
    saved = sys.modules.get(LEAF_MODULE, _ABSENT)
    sys.modules[LEAF_MODULE] = None
    try:
        yield importlib.reload(_wrapper)
    finally:
        if saved is _ABSENT:
            sys.modules.pop(LEAF_MODULE, None)
        else:
            sys.modules[LEAF_MODULE] = saved
        importlib.reload(_wrapper)


def test_broken_leaf_is_fail_closed(module_with_broken_leaf):
    """Leaf missing -> user path 404s; the urlconf still imports; hub-native stands."""
    # Arrange
    from django.urls.resolvers import RoutePattern, URLResolver

    from apps.workspace.writer_app.urls.legacy import (
        urlpatterns as legacy_patterns,
    )

    # Reaching the module at all proves the root urlconf still imports
    # (the #687 outage shape: one leaf's skew must not 500 the whole site).
    assert module_with_broken_leaf.urlpatterns == []
    # The v2 reference is leaf-BACKED (SITE-3 views over leaf views), so it
    # goes dark WITH the leaf — fail-closed, never hub-native content.
    assert module_with_broken_leaf.v2_urlpatterns == []
    # Act — user path with no leaf contributes nothing (CCT 2768: NO silent
    # hub-side fallback — the plain route stays dark, it is not relit with
    # hub views)...
    user_resolver = URLResolver(
        RoutePattern("apps/writer/"), module_with_broken_leaf.urlpatterns
    )
    with pytest.raises(Resolver404):
        user_resolver.resolve("")
    # ...while the dev reference still serves the hub-native surface.
    ref_resolver = URLResolver(RoutePattern("old-direct/"), legacy_patterns)
    # Assert
    for route in ("", "editor/", "api/project/1/manuscript-status/"):
        assert ref_resolver.resolve("old-direct/" + route) is not None, (
            f"old-direct lost the parity reference for {route}."
        )
