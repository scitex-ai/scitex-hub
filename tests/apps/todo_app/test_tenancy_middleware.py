#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tenancy + phase-1 read-only tests for the /todo/ board mount.

Covers the hub-side contract of
``apps.workspace.todo_app.middleware.TodoBoardTenancyMiddleware``:

- the injected ``store`` is the REQUESTING user's own workspace
  ``<project>/.scitex/todo/tasks.yaml`` (user A never sees user B's),
- a client-supplied ``?store=`` is discarded (path-traversal seam),
- every mutating method under /todo/ is rejected in phase 1 — readonly
  visitors get the structured #308 payload, everyone else the explicit
  ``todo-board-readonly-phase1`` 403,
- non-/todo/ requests pass through untouched.

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
        captured["called"] = True
        return HttpResponse("ok")

    response = TodoBoardTenancyMiddleware(get_response)(request)
    return response, captured


def _request(rf, user, path="/todo/", method="get", data=None):
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


class TodoPhase1ReadOnlyGateTest(TestCase):
    """Every mutating method under /todo/ is rejected in phase 1."""

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
        request = _request(self.rf, self.alice, path="/todo/create", method="post")
        # Act
        response, _ = _run(request)
        # Assert
        assert response.status_code == 403

    def test_post_rejection_carries_phase1_reason(self):
        # Arrange
        request = _request(self.rf, self.alice, path="/todo/create", method="post")
        # Act
        response, _ = _run(request)
        # Assert
        assert json.loads(response.content)["reason"] == (
            "todo-board-readonly-phase1"
        )

    def test_post_never_reaches_the_board_view(self):
        # Arrange
        request = _request(self.rf, self.alice, path="/todo/create", method="post")
        # Act
        _, captured = _run(request)
        # Assert
        assert captured.get("called") is None

    def test_readonly_visitor_post_gets_structured_308_rejection(self):
        # Arrange
        request = _request(
            self.rf, self.readonly_visitor, path="/todo/resolve", method="post"
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
