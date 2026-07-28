#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tenancy + phase-1 read-only tests for the /apps/cards/ board mount.

Covers the hub-side contract of
``apps.workspace.todo_app.middleware.TodoBoardTenancyMiddleware``:

- the injected ``store`` is the REQUESTING user's own workspace
  ``<project>/.scitex/todo/tasks.yaml`` (user A never sees user B's),
- a client-supplied ``?store=`` is discarded (path-traversal seam),
- every mutating method under /apps/cards/ is rejected in phase 1 —
  readonly visitors get the structured #308 payload, everyone else the
  explicit ``todo-board-readonly-phase1`` 403,
- anonymous PAGE navigations 302 to login, anonymous DATA fetches get
  the shaped ``signed-out`` 401 JSON (the board JS renders a signed-out
  panel from it instead of choking on login-page HTML),
- non-board requests pass through untouched.

Real Django test DB via django.test.TestCase — no mocks.
"""

import json
from pathlib import Path

import pytest
from django.contrib.auth.models import AnonymousUser, User
from django.http import HttpResponse
from django.test import RequestFactory, TestCase

from apps.infra.project_app.models import Project
from apps.workspace.todo_app.middleware import (
    _TODO_INSTALLED,
    TodoBoardTenancyMiddleware,
)

pytestmark = pytest.mark.skipif(
    not _TODO_INSTALLED, reason="scitex-todo not installed"
)


def _run(request):
    """Run the middleware with a capturing downstream view."""
    captured = {}

    def get_response(req):
        captured["store"] = req.GET.get("store")
        # The PRIMARY channel. Captured separately from the query so a test
        # can prove the two agree — and, once the legacy query injection is
        # removed, so the query-based assertions fail loudly instead of
        # silently reading None.
        captured["store_attr"] = getattr(req, "scitex_store", None)
        captured["called"] = True
        return HttpResponse("ok")

    response = TodoBoardTenancyMiddleware(get_response)(request)
    return response, captured


def _request(rf, user, path="/apps/cards/", method="get", data=None):
    request = getattr(rf, method)(path, data or {})
    request.user = user
    request.session = {}
    return request


class TodoTenancyStoreResolutionTest(TestCase):
    """The injected store is the requester's own workspace file, always."""

    @classmethod
    def setUpTestData(cls):
        cls.alice = User.objects.create_user(username="alice")
        cls.bob = User.objects.create_user(username="bob")
        cls.project_a = Project.objects.create(
            owner=cls.alice, name="Proj A", slug="proj-a"
        )
        cls.project_b = Project.objects.create(
            owner=cls.bob, name="Proj B", slug="proj-b"
        )

    def setUp(self):
        self.rf = RequestFactory()

    def test_store_resolves_inside_requesting_users_workspace(self):
        # Arrange — the active project may be any of alice's own (user
        # signals auto-create a "dotfiles" repo), so assert containment
        # in HER workspace base, not a specific slug.
        from django.conf import settings

        request = _request(self.rf, self.alice)
        alice_base = Path(settings.BASE_DIR) / "data" / "users" / "alice" / "proj"
        # Act
        response, captured = _run(request)
        # Assert
        assert Path(captured["store"]).is_relative_to(alice_base)

    def test_store_points_at_the_project_todo_tasks_yaml(self):
        # Arrange
        request = _request(self.rf, self.alice)
        # Act
        response, captured = _run(request)
        # Assert
        assert captured["store"].endswith("/.scitex/todo/tasks.yaml")

    def test_user_b_request_never_resolves_user_a_store(self):
        # Arrange
        request = _request(self.rf, self.bob)
        # Act
        response, captured = _run(request)
        # Assert
        assert "/users/alice/" not in captured["store"]

    def test_store_is_published_on_the_request_attribute(self):
        # Arrange — the attribute is the channel a client CANNOT forge, and
        # is what upstream scitex-cards will honour instead of ?store=.
        request = _request(self.rf, self.alice)
        # Act
        response, captured = _run(request)
        # Assert
        assert captured["store_attr"] is not None

    def test_request_attribute_is_an_absolute_path(self):
        # Arrange — upstream must not have to guess whether to resolve it.
        request = _request(self.rf, self.alice)
        # Act
        response, captured = _run(request)
        # Assert
        assert Path(captured["store_attr"]).is_absolute()

    def test_request_attribute_agrees_with_the_legacy_query_store(self):
        # Arrange — during the migration window both channels are written;
        # a divergence would mean the two consumers see different tenants.
        request = _request(self.rf, self.alice)
        # Act
        response, captured = _run(request)
        # Assert
        assert str(captured["store_attr"]) == captured["store"]

    def test_hostile_store_param_never_reaches_the_request_attribute(self):
        # Arrange — the whole point of the attribute: a client-supplied
        # ?store= must not be able to impersonate a server-resolved one.
        request = _request(
            self.rf, self.alice, data={"store": "/etc/passwd"}
        )
        # Act
        response, captured = _run(request)
        # Assert
        assert "/etc/passwd" not in str(captured["store_attr"])

    def test_request_attribute_stays_inside_the_requesting_users_workspace(self):
        # Arrange
        from django.conf import settings

        request = _request(self.rf, self.bob)
        bob_base = Path(settings.BASE_DIR) / "data" / "users" / "bob" / "proj"
        # Act
        response, captured = _run(request)
        # Assert
        assert Path(captured["store_attr"]).is_relative_to(bob_base)

    def test_client_supplied_store_param_is_discarded(self):
        # Arrange
        request = _request(
            self.rf, self.alice, data={"store": "/etc/passwd"}
        )
        # Act
        response, captured = _run(request)
        # Assert
        assert captured["store"] != "/etc/passwd"

    def test_client_supplied_store_is_replaced_by_workspace_path(self):
        # Arrange
        request = _request(
            self.rf, self.alice, data={"store": "/etc/passwd"}
        )
        # Act
        response, captured = _run(request)
        # Assert
        assert "/users/alice/proj/" in captured["store"]

    def test_user_without_project_gets_explicit_404(self):
        # Arrange — user signals auto-create a "dotfiles" project, so
        # strip every project (and the dangling last_active pointer) to
        # arrange a genuinely project-less user.
        loner = User.objects.create_user(username="loner")
        Project.objects.filter(owner=loner).delete()
        loner = User.objects.get(username="loner")
        request = _request(self.rf, loner)
        # Act
        response, _ = _run(request)
        # Assert
        assert response.status_code == 404

    def test_anonymous_request_is_redirected_to_login(self):
        # Arrange
        request = _request(self.rf, AnonymousUser())
        # Act
        response, _ = _run(request)
        # Assert
        assert response.status_code == 302

    def test_non_todo_path_passes_through_untouched(self):
        # Arrange
        request = _request(self.rf, self.alice, path="/apps/")
        # Act
        response, captured = _run(request)
        # Assert
        assert captured["store"] is None


class TodoAnonymousResponseShapeTest(TestCase):
    """Anonymous: page navigations 302 to login, data fetches get 401 JSON.

    The board's JS follows a redirect and then chokes parsing the login
    page's HTML as JSON — data endpoints must answer with the shaped
    ``signed-out`` 401 payload the frontend turns into a signed-out panel.
    """

    def setUp(self):
        self.rf = RequestFactory()

    def test_anonymous_board_root_navigation_redirects_to_login(self):
        # Arrange
        request = _request(self.rf, AnonymousUser(), path="/apps/cards/")
        # Act
        response, _ = _run(request)
        # Assert
        assert (response.status_code, response["Location"]) == (
            302,
            "/auth/login/?next=/apps/cards/",
        )

    def test_anonymous_chat_page_navigation_redirects_to_login(self):
        # Arrange
        request = _request(self.rf, AnonymousUser(), path="/apps/cards/chat")
        # Act
        response, _ = _run(request)
        # Assert
        assert response.status_code == 302

    def test_anonymous_data_fetch_gets_401(self):
        # Arrange — /timeline is a named JSON endpoint upstream.
        request = _request(
            self.rf, AnonymousUser(), path="/apps/cards/timeline"
        )
        # Act
        response, _ = _run(request)
        # Assert
        assert response.status_code == 401

    def test_anonymous_data_fetch_payload_is_signed_out_shaped(self):
        # Arrange
        request = _request(
            self.rf, AnonymousUser(), path="/apps/cards/timeline"
        )
        # Act
        response, _ = _run(request)
        # Assert
        assert json.loads(response.content)["error"] == "signed-out"

    def test_anonymous_data_fetch_payload_carries_login_url(self):
        # Arrange
        request = _request(
            self.rf, AnonymousUser(), path="/apps/cards/timeline"
        )
        # Act
        response, _ = _run(request)
        # Assert
        assert json.loads(response.content)["login_url"] == (
            "/auth/login/?next=/apps/cards/"
        )

    def test_anonymous_api_dispatch_subpath_gets_401_json(self):
        # Arrange — /graph rides the api_dispatch catch-all upstream.
        request = _request(self.rf, AnonymousUser(), path="/apps/cards/graph")
        # Act
        response, _ = _run(request)
        # Assert
        assert response["Content-Type"].startswith("application/json")

    def test_anonymous_data_fetch_never_reaches_the_board_view(self):
        # Arrange
        request = _request(
            self.rf, AnonymousUser(), path="/apps/cards/timeline"
        )
        # Act
        _, captured = _run(request)
        # Assert
        assert captured.get("called") is None


class TodoPhase1ReadOnlyGateTest(TestCase):
    """Every mutating method under /apps/cards/ is rejected in phase 1."""

    @classmethod
    def setUpTestData(cls):
        cls.alice = User.objects.create_user(username="alice")
        Project.objects.create(owner=cls.alice, name="Proj A", slug="proj-a")
        cls.readonly_visitor = User.objects.create_user(
            username="readonly-visitor"
        )

    def setUp(self):
        self.rf = RequestFactory()

    def test_post_by_regular_user_is_rejected(self):
        # Arrange
        request = _request(self.rf, self.alice, path="/apps/cards/create", method="post")
        # Act
        response, _ = _run(request)
        # Assert
        assert response.status_code == 403

    def test_post_rejection_carries_phase1_reason(self):
        # Arrange
        request = _request(self.rf, self.alice, path="/apps/cards/create", method="post")
        # Act
        response, _ = _run(request)
        # Assert
        assert json.loads(response.content)["reason"] == (
            "todo-board-readonly-phase1"
        )

    def test_post_never_reaches_the_board_view(self):
        # Arrange
        request = _request(self.rf, self.alice, path="/apps/cards/create", method="post")
        # Act
        _, captured = _run(request)
        # Assert
        assert captured.get("called") is None

    def test_readonly_visitor_post_gets_structured_308_rejection(self):
        # Arrange
        request = _request(
            self.rf, self.readonly_visitor, path="/apps/cards/resolve", method="post"
        )
        # Act
        response, _ = _run(request)
        # Assert
        assert json.loads(response.content)["reason"] == "readonly-visitor"

    def test_readonly_visitor_get_is_never_blocked(self):
        # Arrange — fail-loud doctrine: views always render for readonly.
        Project.objects.create(
            owner=self.readonly_visitor, name="Tour", slug="tour"
        )
        request = _request(self.rf, self.readonly_visitor)
        # Act
        response, _ = _run(request)
        # Assert
        assert response.status_code == 200
