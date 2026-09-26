#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generic mount-policy guard for plugin apps (``scitex.apps``).

Covers ``apps.workspace.apps_app.services.plugin_guards`` — the thin-hub
replacement for the retired per-app wrappers (``todo_app/middleware.py``,
``agents_app/views.py``, ``storage_app/views.py``).

Every test drives the guard with a SYNTHETIC policy via the
``PLUGIN_MOUNT_TABLE_OVERRIDE`` setting, so no test names a real plugin and
the whole file runs with none of the optional packages installed:

    override_settings(
        PLUGIN_MOUNT_TABLE_OVERRIDE=[
            ("/apps/cards/", "Cards", {"audience": "staff", ...}),
        ]
    )

DB-free by design (this dev container's database role cannot create test
databases): users are stub objects, the project lookup behind tenancy is
stubbed with ``unittest.mock``, and page-chrome DB queries are neutralized
with the same three mocks as ``test_storage_organize.py``.

What is pinned:

- anonymous requests never reach a governed mount (302 to LOGIN_URL);
- open mounts admit any signed-in user; ``audience: staff`` additionally
  admits only staff, superusers, and ``SCITEX_HUB_PLUGIN_OPERATORS``;
- a refused navigation renders the generic restricted page (no board,
  fleet, or file data); a refused data fetch gets shaped JSON;
- ``discard_query_params`` drops client-supplied tenancy forgeries;
- ``tenant_store`` + ``tenant_attribute`` fail closed (404 with the /new/
  hint) when no project resolves, and publish the contained store on an
  unforgable request attribute otherwise;
- non-safe methods are fail-closed on restricted mounts, allowlisted per
  route on open ones, and re-arm CSRF on the allowlisted writes (leaf
  write views are typically ``@csrf_exempt`` while the host authenticates
  with a session cookie);
- non-plugin paths pass through untouched;
- the guard is installed in MIDDLEWARE (and the three retired per-app
  middlewares/views are not).
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from django.contrib.auth.models import AnonymousUser
from django.http import HttpResponse
from django.test import RequestFactory, override_settings

from apps.workspace.apps_app.services import plugin_guards
from apps.workspace.apps_app.services.plugin_guards import (
    PluginMountGuardMiddleware,
    _compile_route,
    _wants_html,
    can_open_plugin_mount,
    plugin_access_allowed,
)

RF = RequestFactory()

#: A cards-shaped policy: restricted audience, server-side tenancy, the
#: client-supplied store seam discarded, DM writes allowlisted.
STAFF_POLICY = {
    "login_required": True,
    "audience": "staff",
    "tenant_store": ".scitex/todo/tasks.yaml",
    "tenant_attribute": "scitex_store",
    "discard_query_params": ["store"],
    "writable_routes": ["dm/thread/<str:peer>", "dm/upload"],
}

#: An agents/storage-shaped policy: login boundary only, no audience gate.
OPEN_POLICY = {"login_required": True}

STAFF_TABLE = [("/apps/cards/", "Cards", STAFF_POLICY)]
OPEN_TABLE = [("/apps/agents/", "Agents", OPEN_POLICY)]

#: Audience-only restriction (no tenancy): pins WHO may open a mount
#: without depending on the project lookup behind tenant stores.
AUDIENCE_ONLY_TABLE = [("/apps/cards/", "Cards", {"audience": "staff"})]


def _user(**flags):
    base = {
        "is_authenticated": True,
        "is_staff": False,
        "is_superuser": False,
        "username": "alice",
    }
    base.update(flags)
    return SimpleNamespace(**base)


def _run(request, *, table):
    """Run the guard; report (response, reached_downstream, downstream_saw)."""
    seen = {}

    def get_response(req):
        seen["get"] = req.GET.copy()
        seen["store_attr"] = getattr(req, "scitex_store", None)
        seen["called"] = True
        return HttpResponse("downstream-ok")

    with override_settings(PLUGIN_MOUNT_TABLE_OVERRIDE=table):
        response = PluginMountGuardMiddleware(get_response)(request)
    return response, seen


def _request(user, path="/apps/cards/", method="get", data=None, **extra):
    request = getattr(RF, method)(path, data or {}, **extra)
    request.user = user
    return request


def _chrome_neutralized():
    """Neutralize hub-chrome DB queries for tests that render a page.

    Same three mocks as ``test_storage_organize.py``: the project context
    processor resolves any two-segment path against the Project table, the
    sidebar pins resolver queries ModuleInstallation, and the site dock
    resolver queries AppsModule installations.
    """
    from apps.infra.project_app.models import Project

    manager = mock.Mock()
    manager.select_related.return_value.get.side_effect = Project.DoesNotExist
    return (
        mock.patch.object(Project, "objects", manager),
        mock.patch(
            "apps.workspace.apps_app.views.launcher.get_pinned_module_names",
            return_value=[],
            create=True,
        ),
        mock.patch(
            "apps.infra.public_app.templatetags.site_dock.dock_items",
            return_value=[],
        ),
    )


# =====================================================================
# Installation: the generic guard is mounted, the per-app ones are gone
# =====================================================================
def test_guard_middleware_is_installed_after_authentication():
    # Arrange
    from django.conf import settings

    # Act
    middleware = list(settings.MIDDLEWARE)

    # Assert
    guard = "apps.workspace.apps_app.services.plugin_guards.PluginMountGuardMiddleware"
    assert guard in middleware
    assert middleware.index(
        "django.contrib.auth.middleware.AuthenticationMiddleware"
    ) < middleware.index(guard)


def test_retired_per_app_mount_code_is_not_installed():
    # Arrange
    from django.conf import settings

    # Act
    middleware = list(settings.MIDDLEWARE)

    # Assert — the bespoke wrappers are deleted; nothing may re-add them.
    assert "apps.workspace.todo_app.middleware.TodoBoardTenancyMiddleware" not in middleware
    assert "apps.workspace.storage_app.views" not in str(middleware)


def test_retired_per_app_wrapper_modules_are_gone():
    # Arrange
    import importlib.util

    # Act / Assert — thin-hub: no wrapper views, urls, or middleware to import.
    # find_spec of a SUBMODULE raises ModuleNotFoundError (rather than
    # returning None) when the parent package is absent entirely — absence
    # is the expected state here, not an error (same probe the old
    # registry tile-guard used).
    for dotted in (
        "apps.workspace.todo_app.middleware",
        "apps.workspace.agents_app.views",
        "apps.workspace.agents_app.urls",
        "apps.workspace.storage_app.views",
        "apps.workspace.storage_app.urls",
        "apps.workspace.storage_app.volumes",
        "apps.workspace.storage_app.organize",
    ):
        try:
            spec = importlib.util.find_spec(dotted)
        except ModuleNotFoundError:
            spec = None
        assert spec is None, (
            f"{dotted} still importable — the bespoke wrapper was not deleted"
        )


# =====================================================================
# Audience: who may open a governed mount
# =====================================================================
def test_anonymous_request_redirects_to_login_without_reaching_downstream():
    # Arrange
    request = _request(AnonymousUser())

    # Act
    response, seen = _run(request, table=STAFF_TABLE)

    # Assert
    assert response.status_code == 302
    assert response.url.startswith("/auth/login/")
    assert seen == {}


def test_open_mount_admits_any_signed_in_user():
    # Arrange
    request = _request(_user(), path="/apps/agents/")

    # Act
    response, seen = _run(request, table=OPEN_TABLE)

    # Assert
    assert response.status_code == 200
    assert seen.get("called") is True


def test_restricted_mount_refuses_a_plain_user_on_data_paths_as_json():
    # Arrange — board fetches send no text/html Accept header.
    request = _request(_user(), path="/apps/cards/tasks")

    # Act
    response, seen = _run(request, table=STAFF_TABLE)

    # Assert — shaped JSON, never the board, never downstream.
    assert response.status_code == 403
    assert seen == {}
    assert response["Content-Type"].startswith("application/json")
    assert b"plugin-mount-restricted-audience" in response.content


def test_restricted_mount_renders_a_data_free_page_for_navigations():
    # Arrange — a browser navigation sends text/html.
    request = _request(
        _user(), path="/apps/cards/", HTTP_ACCEPT="text/html,application/xhtml+xml"
    )
    p1, p2, p3 = _chrome_neutralized()

    # Act
    with p1, p2, p3:
        response, seen = _run(request, table=STAFF_TABLE)

    # Assert — the generic placeholder names the app and shows no board data.
    assert response.status_code == 403
    assert seen == {}
    assert response["Content-Type"].startswith("text/html")
    assert b"data-own-scope-app" in response.content


def test_restricted_mount_admits_staff_superuser_and_listed_operators():
    # Arrange — audience-only policy: admission without depending on tenancy.
    staff = _request(_user(is_staff=True), path="/apps/cards/tasks")
    root = _request(_user(is_superuser=True), path="/apps/cards/tasks")
    operator = _request(_user(username="opsperson"), path="/apps/cards/tasks")

    # Act
    staff_resp, staff_seen = _run(staff, table=AUDIENCE_ONLY_TABLE)
    root_resp, root_seen = _run(root, table=AUDIENCE_ONLY_TABLE)
    with override_settings(SCITEX_HUB_PLUGIN_OPERATORS=["opsperson"]):
        op_resp, op_seen = _run(operator, table=AUDIENCE_ONLY_TABLE)

    # Assert
    assert (staff_resp.status_code, staff_seen.get("called")) == (200, True)
    assert (root_resp.status_code, root_seen.get("called")) == (200, True)
    assert (op_resp.status_code, op_seen.get("called")) == (200, True)


def test_restricted_mount_refuses_unlisted_users_even_with_operators_set():
    # Arrange
    request = _request(_user(username="visitor"), path="/apps/cards/tasks")

    # Act
    with override_settings(SCITEX_HUB_PLUGIN_OPERATORS=["opsperson"]):
        response, seen = _run(request, table=STAFF_TABLE)

    # Assert
    assert (response.status_code, seen) == (403, {})


def test_non_plugin_paths_pass_through_untouched():
    # Arrange
    request = _request(_user(username="visitor"), path="/apps/scholar/")

    # Act
    with override_settings(SCITEX_HUB_PLUGIN_OPERATORS=[]):
        response, seen = _run(request, table=STAFF_TABLE)

    # Assert — one prefix check, then downstream, even for a stranger.
    assert (response.status_code, seen.get("called")) == (200, True)


# =====================================================================
# plugin_access_allowed / can_open_plugin_mount units (tile/mount agreement)
# =====================================================================
def test_access_units():
    # Arrange
    plain = _user()
    staff = _user(is_staff=True)
    root = _user(is_superuser=True)
    operator = _user(username="opsperson")
    anonymous = AnonymousUser()

    # Act / Assert — open policy: every signed-in user, no anonymous.
    assert plugin_access_allowed(plain, {}) is True
    assert plugin_access_allowed(anonymous, {}) is False
    # Restricted policy: staff, superusers, listed operators only.
    assert plugin_access_allowed(plain, {"audience": "staff"}) is False
    assert plugin_access_allowed(staff, {"audience": "staff"}) is True
    assert plugin_access_allowed(root, {"audience": "staff"}) is True
    assert plugin_access_allowed(anonymous, {"audience": "staff"}) is False
    with override_settings(SCITEX_HUB_PLUGIN_OPERATORS=["opsperson"]):
        assert plugin_access_allowed(operator, {"audience": "staff"}) is True
        assert plugin_access_allowed(plain, {"audience": "staff"}) is False


def test_tile_predicate_agrees_with_the_request_guard():
    # Arrange
    plain = _user()
    staff = _user(is_staff=True)

    # Act / Assert — a tile the user can see must not open onto a 403.
    with override_settings(PLUGIN_MOUNT_TABLE_OVERRIDE=AUDIENCE_ONLY_TABLE):
        assert can_open_plugin_mount(plain, "/apps/cards/") is False
        assert can_open_plugin_mount(plain, "/apps/cards/tasks") is False
        assert can_open_plugin_mount(staff, "/apps/cards/") is True
        # Paths without a policy are unaffected.
        assert can_open_plugin_mount(plain, "/apps/scholar/") is True


def test_wants_html_distinguishes_navigations_from_fetches():
    # Arrange
    navigation = _request(
        _user(), HTTP_ACCEPT="text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
    )
    fetch = _request(_user(), HTTP_ACCEPT="*/*")

    # Act / Assert
    assert _wants_html(navigation) is True
    assert _wants_html(fetch) is False


# =====================================================================
# Tenancy: the client-supplied store seam is discarded, the server-side
# store travels on an unforgable request attribute, and a missing project
# fails closed.
# =====================================================================
def test_forged_store_param_with_no_project_still_fails_closed():
    # Arrange — the forgery the old ?store= seam allowed, plus no project.
    # Tenancy fails closed before the discard could matter; this pins the
    # ORDER (the discard itself is pinned below with a resolving project).
    request = _request(
        _user(is_staff=True), path="/apps/cards/tasks", data={"store": "/etc/passwd"}
    )

    # Act
    with mock.patch(
        "apps.infra.project_app.services.project_utils.get_current_project",
        return_value=None,
    ):
        response, seen = _run(request, table=STAFF_TABLE)

    # Assert
    assert (response.status_code, seen) == (404, {})


def test_forged_store_param_never_reaches_downstream(tmp_path):
    # Arrange
    project = SimpleNamespace(
        slug="p1", owner=SimpleNamespace(username="alice"), is_org_owned=False
    )
    request = _request(
        _user(is_staff=True, username="alice"),
        path="/apps/cards/tasks",
        data={"store": "/home/victim/other.yaml"},
    )

    # Act
    with (
        mock.patch(
            "apps.infra.project_app.services.project_utils.get_current_project",
            return_value=project,
        ),
        mock.patch(
            "apps.infra.project_app.services.filesystem.paths.get_user_base_path",
            return_value=tmp_path,
        ),
        override_settings(PLUGIN_MOUNT_TABLE_OVERRIDE=STAFF_TABLE),
    ):
        response = PluginMountGuardMiddleware(lambda req: HttpResponse("ok"))(request)
        captured_get = request.GET.copy()
        captured_attr = getattr(request, "scitex_store", None)

    # Assert — the forgery is dropped; the attribute carries the own store.
    assert response.status_code == 200
    assert "store" not in captured_get
    assert str(captured_attr) == str(tmp_path / "p1" / ".scitex/todo/tasks.yaml")


def test_missing_project_fails_closed_with_the_new_project_hint():
    # Arrange
    request = _request(_user(is_staff=True), path="/apps/cards/")

    # Act
    with mock.patch(
        "apps.infra.project_app.services.project_utils.get_current_project",
        return_value=None,
    ):
        response, seen = _run(request, table=STAFF_TABLE)

    # Assert
    assert response.status_code == 404
    assert seen == {}
    assert b"/new/" in response.content


def test_absolute_tenant_store_declaration_is_refused(tmp_path):
    # Arrange — a leaf declaring an absolute tenant_store is misconfigured;
    # the resolver must refuse rather than serve outside the workspace.
    table = [("/apps/x/", "X", {**OPEN_POLICY, "tenant_store": "/etc/x.yaml", "tenant_attribute": "scitex_store"})]
    request = _request(_user(), path="/apps/x/")

    # Act
    response, seen = _run(request, table=table)

    # Assert
    assert (response.status_code, seen) == (404, {})


# =====================================================================
# Writes: fail closed on restricted mounts, allowlisted per route
# elsewhere, CSRF re-armed on the opened writes.
# =====================================================================
def test_restricted_mount_without_writable_routes_denies_all_writes():
    # Arrange — fail closed: a restricted mount with no allowlist denies
    # every non-safe method, even for staff.
    table = [("/apps/x/", "X", {"audience": "staff"})]
    request = _request(_user(is_staff=True), path="/apps/x/dm/thread/bob", method="post")

    # Act
    response, seen = _run(request, table=table)

    # Assert
    assert response.status_code == 403
    assert seen == {}
    assert b"plugin-mount-readonly" in response.content


def test_post_to_a_non_allowlisted_route_is_refused():
    # Arrange — give the request a resolving project so the WRITE gate (not
    # the tenancy 404) is what answers. Both orders are fail-closed, but
    # this test pins the write gate specifically.
    request = _request(_user(is_staff=True), path="/apps/cards/tasks", method="post")
    project = SimpleNamespace(
        slug="p1", owner=SimpleNamespace(username="alice"), is_org_owned=False
    )

    # Act
    with (
        mock.patch(
            "apps.infra.project_app.services.project_utils.get_current_project",
            return_value=project,
        ),
        mock.patch(
            "apps.infra.project_app.services.filesystem.paths.get_user_base_path",
            return_value=Path("/tmp/guard-probe"),
        ),
    ):
        response, seen = _run(request, table=STAFF_TABLE)

    # Assert
    assert response.status_code == 403
    assert seen == {}
    assert b"plugin-mount-readonly" in response.content


def test_post_to_an_allowlisted_route_re_arms_csrf(tmp_path):
    # Arrange — the leaf DM view is csrf_exempt; the host authenticates by
    # session cookie, so without re-armed CSRF this POST would be a working
    # cross-site forgery. A bare RequestFactory POST carries no CSRF token.
    project = SimpleNamespace(
        slug="p1", owner=SimpleNamespace(username="alice"), is_org_owned=False
    )
    request = _request(
        _user(is_staff=True, username="alice"), path="/apps/cards/dm/thread/bob", method="post"
    )

    # Act
    with (
        mock.patch(
            "apps.infra.project_app.services.project_utils.get_current_project",
            return_value=project,
        ),
        mock.patch(
            "apps.infra.project_app.services.filesystem.paths.get_user_base_path",
            return_value=tmp_path,
        ),
    ):
        response, seen = _run(request, table=STAFF_TABLE)

    # Assert — rejected by the re-armed CSRF check, downstream never ran.
    assert response.status_code == 403
    assert seen == {}
    assert b"CSRF" in response.content


def test_open_mount_without_an_allowlist_keeps_raw_mount_behaviour():
    # Arrange — unrestricted plugins with no writable_routes keep no method
    # gate: their behaviour is unchanged from a raw mount.
    request = _request(_user(), path="/apps/agents/worker/action", method="post")

    # Act
    response, seen = _run(request, table=OPEN_TABLE)

    # Assert
    assert (response.status_code, seen.get("called")) == (200, True)


def test_safe_methods_are_never_write_gated():
    # Arrange
    request = _request(_user(is_staff=True), path="/apps/cards/tasks", method="get")

    # Act
    with (
        mock.patch(
            "apps.infra.project_app.services.project_utils.get_current_project",
            return_value=SimpleNamespace(
                slug="p1",
                owner=SimpleNamespace(username="alice"),
                is_org_owned=False,
            ),
        ),
        mock.patch(
            "apps.infra.project_app.services.filesystem.paths.get_user_base_path",
            return_value=Path("/tmp/guard-probe"),
        ),
    ):
        response, seen = _run(request, table=STAFF_TABLE)

    # Assert
    assert (response.status_code, seen.get("called")) == (200, True)


# =====================================================================
# Writable-route patterns: Django converter syntax, anchored full match
# =====================================================================
def test_writable_route_patterns():
    # Arrange
    thread = _compile_route("dm/thread/<str:peer>")
    upload = _compile_route("dm/upload")
    numeric = _compile_route("item/<int:pk>")

    # Act / Assert
    assert thread.match("dm/thread/bob")
    assert not thread.match("dm/thread/bob/reaction-x")
    assert not thread.match("dm/thread/")
    assert not thread.match("other/thread/bob")
    assert upload.match("dm/upload")
    assert not upload.match("dm/upload/extra")
    assert numeric.match("item/42")
    assert not numeric.match("item/abc")


def test_guard_module_exports_its_public_surface():
    # Arrange / Act / Assert
    assert set(plugin_guards.__all__) == {
        "PluginMountGuardMiddleware",
        "can_open_plugin_mount",
        "plugin_access_allowed",
        "plugin_mount_prefixes",
        "resolve_plugin_tenant_store",
    }


# EOF
