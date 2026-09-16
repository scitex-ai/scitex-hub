#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The visitor pool is RETIRED (operator ruling: "drop visitor entirely").

compass-impl-visitor-pool-retirement-20260910. Signup-first: email
verification + card registration starts a 30-day free trial; there is no
card-less sandbox. These tests assert the retirement end-to-end — they
REPLACE the four files that asserted the pool EXISTED (test_visitor_entry_route,
test_visitor_pool_allocatable, test_visitor_heartbeat_contract,
test_visitor_failloud), whose premise is now the opposite.

What "retired" means here, precisely:
  - the three Visitor* middlewares are NO LONGER in settings.MIDDLEWARE, so an
    anonymous browser is never auto-provisioned into visitor-001..N;
  - the sole legacy entry route redirects signed-out users to signup;
  - visitor state and pool API routes are absent from the public URL surface;
  - the visitor-pool management commands remain dormant in this bounded slice;
  - the safety nets that protect real users / pre-retirement readonly rows
    (ReadonlyVisitorWriteGuard, GuestSession, OnSiteAuth, TodoBoardTenancy)
    are still in the chain.

These run WITHOUT a database: they assert on settings, the urlconf, and the
signup redirect; removed route names no longer reverse. The DB-backed
behaviour (anonymous user genuinely stays anonymous, no slot row created) is
the CI arm.
"""

from __future__ import annotations

import importlib.util

import pytest
from django.conf import settings
from django.test import Client
from django.urls import NoReverseMatch, reverse

# The three middlewares the retirement removes from the request chain.
_RETIRED_MIDDLEWARES = (
    "apps.infra.project_app.middleware.VisitorAutoLoginMiddleware",
    "apps.infra.project_app.middleware.VisitorExpirationMiddleware",
    "apps.infra.project_app.middleware.VisitorAppRedirectMiddleware",
)

# The safety nets that must SURVIVE the retirement (protect real users and any
# pre-retirement readonly-visitor row; not provisioners).
_MUST_STAY = (
    "apps.infra.project_app.middleware_readonly_write_guard.ReadonlyVisitorWriteGuardMiddleware",
    "apps.infra.project_app.middleware.GuestSessionMiddleware",
    "apps.infra.project_app.middleware.OnSiteAuthMiddleware",
    "apps.workspace.todo_app.middleware.TodoBoardTenancyMiddleware",
)


class TestVisitorMiddlewareRetired:
    def test_the_three_visitor_middlewares_are_not_in_the_chain(self):
        # Arrange
        chain = settings.MIDDLEWARE
        # Assert — none of the retired provisioners remain.
        for name in _RETIRED_MIDDLEWARES:
            assert name not in chain, (
                f"{name} is still in MIDDLEWARE — the visitor pool was "
                "retired 2026-09-10 and this middleware auto-provisions "
                "anonymous browsers into visitor slots."
            )

    def test_the_safety_nets_survive_the_retirement(self):
        # Arrange
        chain = settings.MIDDLEWARE
        # Assert — the guardrails that protect real users / pre-retirement
        # readonly rows are still wired in.
        for name in _MUST_STAY:
            assert name in chain, (
                f"{name} was removed from MIDDLEWARE — the retirement stops "
                "provisioning; it must not remove the write-guard / guest / "
                "auth / todo-tenancy safety nets."
            )


class TestVisitorRoutesRetired:
    def setup_method(self):
        self.client = Client()

    def test_enter_redirects_signed_out_users_to_signup(self):
        response = self.client.get("/enter/", follow=False)
        assert response.status_code == 301
        assert response.headers["Location"] == "/auth/signup/"

    @pytest.mark.parametrize(
        "name",
        [
            "visitor_status",
            "visitor_expired",
            "visitor_restart",
            "visitor_pool_full",
        ],
    )
    def test_visitor_state_pages_are_not_routed(self, name):
        with pytest.raises(NoReverseMatch):
            reverse(f"public_app:{name}")

    @pytest.mark.parametrize(
        "name",
        [
            "visitor_pool_initialize_api",
            "visitor_fill_slots_api",
            "visitor_free_slots_api",
            "visitor_heartbeat_api",
            "visitor_resources_api",
        ],
    )
    def test_visitor_pool_api_is_not_routed(self, name):
        with pytest.raises(NoReverseMatch):
            reverse(f"public_app:{name}")


class TestVisitorPoolManagementCommandsSurviveAsDormant:
    """The pool's lifecycle commands are NOT deleted — they are now dormant.

    Retiring the visitor pool operationally means removing the middleware that
    FEDS it, not deleting the pool's management surface. The six commands
    (create/reset/reconcile/assert/ready/workspaces) still exist and their own
    test suites (tests/apps/project_app/services/visitor_pool/) still pass;
    after the middleware retirement nothing calls them on the request path, so
    they are dormant utilities. Deleting them would be an unbounded repo-wide
    refactor (the visitor_pool service is imported by ~30 non-middleware
    call sites for ROLE detection), which this bounded change does not do.
    """

    @pytest.mark.parametrize(
        "command",
        [
            "create_visitor_pool",
            "reset_visitor_pool",
            "reconcile_visitor_slots",
            "assert_visitor_pool_ready",
            "visitor_pool_ready",
            "reset_visitor_workspaces",
        ],
    )
    def test_the_pool_management_command_still_exists(self, command):
        spec = importlib.util.find_spec(
            f"apps.infra.project_app.management.commands.{command}"
        )
        assert spec is not None, (
            f"management command {command!r} is missing — it is a dormant "
            "utility of the retired pool and must stay importable; this "
            "change retires provisioning, not the pool's management surface."
        )


class TestRoleDetectionApiSurvives:
    def test_visitor_pool_module_still_importable_for_role_detection(self):
        # ~30 non-middleware call sites still import VisitorPool /
        # is_visitor_session for ROLE detection (is this user a pre-retirement
        # visitor?). The module must stay importable even though provisioning
        # is gone — deleting it would be a repo-wide refactor, not this change.
        from apps.infra.project_app.services.visitor_pool import (  # noqa: F401
            VisitorPool,
        )


class TestAnonymousFunnelAfterRetirement:
    """Item 5 of the operator ruling: anonymous is NOT auto-logged-in; app
    pages funnel to the public surface, and the marketing pages stay public.

    DB-free on purpose: these routes (workspace_shell's redirect, the
    marketing pages) need no ORM. The DB-backed arm — "a browser hitting
    /apps/my-projects/ or /apps/store/ gets 302 to /auth/login/, no visitor-001..N
    row created" — runs in CI where Postgres exists.
    """

    @pytest.mark.parametrize(
        "path", ["/landing/", "/pricing/", "/tokushoho/", "/contact/"]
    )
    def test_marketing_pages_stay_public_for_anonymous(self, path):
        client = Client()
        response = client.get(path, follow=True)
        assert response.status_code == 200, (
            f"{path} must stay publicly reachable for anonymous users "
            f"(got {response.status_code}) — the pre-signup funnel depends on it."
        )

    def test_anonymous_workspace_is_funneled_to_landing_not_a_login_wall(self):
        # workspace_shell deliberately redirects to /landing/ (not login) for
        # anonymous users — the signup-first funnel.
        client = Client()
        response = client.get("/apps/workspace/", follow=False)
        assert response.status_code == 302, response.status_code
        assert response.headers["Location"] == "/landing/"

    def test_anonymous_landing_header_has_no_visitor_badge(self):
        # The visitor badge / popover markup is retired (item 4). An anonymous
        # render of any page must not contain it — and because the whole header
        # is shared, the landing page is the cheapest DB-free surface to check.
        client = Client()
        html = client.get("/landing/", follow=True).content.decode("utf-8")
        for needle in (
            "header-visitor-badge-mobile",
            "header-visitor-badge-popover",
            "visitor-menu-toggle",
            "End Visitor Session",
            "Read-Only Mode",
        ):
            assert needle not in html, (
                f"retired visitor markup {needle!r} is still rendered on the "
                "anonymous landing page."
            )

