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
from django.conf import settings
from django.contrib.auth.models import AnonymousUser, User
from django.http import HttpResponse
from django.middleware.csrf import get_token
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


def _csrf_post(rf, user, path, valid_token=True):
    """A POST carrying a real CSRF token, as a browser would send it.

    ``RequestFactory`` (unlike the test ``Client``) does not set
    ``_dont_enforce_csrf_checks``, so the middleware's re-armed CSRF check
    genuinely runs against these requests.

    BOTH halves are required and it is easy to supply only one. Django takes
    the SECRET from the ``csrftoken`` COOKIE and the presented token from the
    ``X-CSRFToken`` HEADER, then compares them; a header alone fails with
    "CSRF cookie not set" — which is what a browser that never received the
    cookie would also hit, so the omission looks like a middleware bug rather
    than a test bug. Writing the same masked token to both is valid:
    ``CsrfViewMiddleware._get_secret`` unmasks a 64-char cookie back to the
    secret, and the header unmasks to the same one.
    """
    request = rf.post(path, {})
    request.user = user
    request.session = {}
    token = get_token(request)
    request.COOKIES[settings.CSRF_COOKIE_NAME] = token
    request.META["HTTP_X_CSRFTOKEN"] = token if valid_token else "x" * 64
    return request


class TodoOpenedWriteSubsetTest(TestCase):
    """H1: DM send / react / upload are open; nothing else is.

    The operator's acceptance test for phone parity is sending a DM with an
    attachment, so these three routes must ADMIT an authenticated write —
    and every other mutating route must still be refused.
    """

    @classmethod
    def setUpTestData(cls):
        cls.alice = User.objects.create_user(username="alice")
        Project.objects.create(owner=cls.alice, name="Proj A", slug="proj-a")
        cls.readonly_visitor = User.objects.create_user(
            username="readonly-visitor"
        )

    def setUp(self):
        self.rf = RequestFactory()

    # --- the POSITIVE control: these three actually go through ---------
    # Without these, every "is rejected" assertion below would also pass on
    # a middleware that rejects EVERYTHING — the vacuous-green failure mode.

    def test_dm_send_reaches_the_board(self):
        # Arrange
        request = _csrf_post(
            self.rf, self.alice, "/apps/cards/dm/thread/operator"
        )
        # Act
        _, captured = _run(request)
        # Assert
        assert captured.get("called") is True

    def test_dm_send_is_not_rejected(self):
        # Arrange
        request = _csrf_post(
            self.rf, self.alice, "/apps/cards/dm/thread/operator"
        )
        # Act
        response, _ = _run(request)
        # Assert
        assert response.status_code == 200

    def test_dm_reaction_reaches_the_board(self):
        # Arrange
        request = _csrf_post(
            self.rf, self.alice, "/apps/cards/dm/thread/operator/reaction"
        )
        # Act
        _, captured = _run(request)
        # Assert
        assert captured.get("called") is True

    def test_dm_upload_reaches_the_board(self):
        # Arrange
        request = _csrf_post(self.rf, self.alice, "/apps/cards/dm/upload")
        # Act
        _, captured = _run(request)
        # Assert
        assert captured.get("called") is True

    def test_opened_write_carries_the_server_resolved_store(self):
        # Arrange — an admitted write must carry the store attribute: the
        # upstream honours ONLY the attribute and would otherwise fail closed.
        request = _csrf_post(
            self.rf, self.alice, "/apps/cards/dm/thread/operator"
        )
        # Act
        _, captured = _run(request)
        # Assert
        assert captured["store_attr"] is not None

    def test_opened_write_is_scoped_to_the_writing_user(self):
        # Arrange
        request = _csrf_post(
            self.rf, self.alice, "/apps/cards/dm/thread/operator"
        )
        # Act
        _, captured = _run(request)
        # Assert
        assert "alice" in str(captured["store_attr"])

    # --- the allowlist is an allowlist -------------------------------

    def test_api_dispatch_catchall_stays_closed(self):
        # Arrange — the upstream <path:endpoint> route would expose every
        # board mutation at once; it must NOT be reachable.
        request = _csrf_post(self.rf, self.alice, "/apps/cards/anything")
        # Act
        response, _ = _run(request)
        # Assert
        assert response.status_code == 403

    def test_api_dispatch_catchall_never_reaches_the_board(self):
        # Arrange
        request = _csrf_post(self.rf, self.alice, "/apps/cards/anything")
        # Act
        _, captured = _run(request)
        # Assert
        assert captured.get("called") is None

    def test_hooks_endpoints_stay_closed(self):
        # Arrange
        request = _csrf_post(self.rf, self.alice, "/apps/cards/hooks/push")
        # Act
        response, _ = _run(request)
        # Assert
        assert response.status_code == 403

    def test_peer_segment_cannot_smuggle_a_second_route(self):
        # Arrange — <str:peer> matches one segment; a nested path must not
        # match the anchored pattern.
        request = _csrf_post(
            self.rf, self.alice, "/apps/cards/dm/thread/a/b/hooks/push"
        )
        # Act
        response, _ = _run(request)
        # Assert
        assert response.status_code == 403

    # --- an opened route is not an unguarded one ----------------------

    def test_anonymous_cannot_write_to_an_opened_route(self):
        # Arrange
        request = _csrf_post(self.rf, AnonymousUser(), "/apps/cards/dm/upload")
        # Act
        response, _ = _run(request)
        # Assert
        assert response.status_code == 401

    def test_anonymous_write_never_reaches_the_board(self):
        # Arrange — an opened route is not an unauthenticated one.
        request = _csrf_post(self.rf, AnonymousUser(), "/apps/cards/dm/upload")
        # Act
        _, captured = _run(request)
        # Assert
        assert captured.get("called") is None

    def test_readonly_visitor_cannot_write_to_an_opened_route(self):
        # Arrange
        Project.objects.create(
            owner=self.readonly_visitor, name="Tour", slug="tour"
        )
        request = _csrf_post(
            self.rf, self.readonly_visitor, "/apps/cards/dm/thread/operator"
        )
        # Act
        response, _ = _run(request)
        # Assert
        assert json.loads(response.content)["reason"] == "readonly-visitor"

    def test_readonly_visitor_write_never_reaches_the_board(self):
        # Arrange
        Project.objects.create(
            owner=self.readonly_visitor, name="Tour2", slug="tour2"
        )
        request = _csrf_post(
            self.rf, self.readonly_visitor, "/apps/cards/dm/thread/operator"
        )
        # Act
        _, captured = _run(request)
        # Assert
        assert captured.get("called") is None

    def test_opened_route_without_csrf_token_is_refused(self):
        # Arrange — the upstream dm_thread_view is @csrf_exempt and the hub
        # authenticates by session cookie, so without this check any site
        # the operator visits could post a DM as them.
        request = self.rf.post("/apps/cards/dm/thread/operator", {})
        request.user = self.alice
        request.session = {}
        # Act
        response, _ = _run(request)
        # Assert
        assert response.status_code == 403

    def test_opened_route_without_csrf_never_reaches_the_board(self):
        # Arrange
        request = self.rf.post("/apps/cards/dm/thread/operator", {})
        request.user = self.alice
        request.session = {}
        # Act
        _, captured = _run(request)
        # Assert
        assert captured.get("called") is None

    def test_opened_route_with_wrong_csrf_token_is_refused(self):
        # Arrange
        request = _csrf_post(
            self.rf,
            self.alice,
            "/apps/cards/dm/thread/operator",
            valid_token=False,
        )
        # Act
        response, _ = _run(request)
        # Assert
        assert response.status_code == 403

    def test_opened_route_with_wrong_csrf_never_reaches_the_board(self):
        # Arrange
        request = _csrf_post(
            self.rf,
            self.alice,
            "/apps/cards/dm/thread/operator",
            valid_token=False,
        )
        # Act
        _, captured = _run(request)
        # Assert
        assert captured.get("called") is None
