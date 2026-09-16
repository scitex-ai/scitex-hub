#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The /apps/cards/ mount is staff-only (P0, 2026-09-14).

Under scitex-cards 0.52 the per-project store the tenancy middleware injects
does not scope the read: the board loads the fleet's central store. Measured
on the dev hub, a shared-pool visitor received all 7471 fleet cards from
/apps/cards/tasks. Until upstream honours a per-tenant store, the mount must
refuse every non-staff user — pages and data, reads and writes.

Card: hub-p0-cards-mount-serves-fleet-board-to-any-signed-in-user-20260914

Real Django test DB via django.test.TestCase — no mocks.
"""

import json

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
    not _TODO_INSTALLED, reason="scitex-cards not installed"
)

# The data endpoints that returned the whole fleet board to a visitor.
DATA_PATHS = (
    "/apps/cards/tasks",
    "/apps/cards/graph",
    "/apps/cards/runnable",
    "/apps/cards/timeline",
)


def _run(request):
    """Run the middleware; report (status, reason, reached_downstream)."""
    reached = {"downstream": False}

    def get_response(req):
        reached["downstream"] = True
        return HttpResponse("board")

    response = TodoBoardTenancyMiddleware(get_response)(request)
    reason = None
    if response.get("Content-Type", "").startswith("application/json"):
        reason = json.loads(response.content).get("reason")
    return response.status_code, reason, reached["downstream"]


def _request(rf, user, path, method="get"):
    request = getattr(rf, method)(path)
    request.user = user
    request.session = {}
    return request


class CardsMountStaffOnlyTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.customer = User.objects.create_user(username="customer")
        cls.staff = User.objects.create_user(username="staffer", is_staff=True)
        cls.superuser = User.objects.create_superuser(
            username="root", email="root@example.com", password="x"
        )
        for user, slug in (
            (cls.customer, "c"),
            (cls.staff, "s"),
            (cls.superuser, "r"),
        ):
            Project.objects.create(owner=user, name=slug, slug=slug)

    def setUp(self):
        self.rf = RequestFactory()

    def test_non_staff_is_refused_on_every_fleet_data_path(self):
        # Arrange
        requests = [_request(self.rf, self.customer, p) for p in DATA_PATHS]
        # Act
        results = [_run(r) for r in requests]
        # Assert
        assert results == [(403, "cards-board-staff-only", False)] * len(DATA_PATHS)

    def test_non_staff_board_page_gets_placeholder_without_reaching_the_board(self):
        # Operator 2026-09-14: the app stays visible to everyone, so a page
        # navigation renders the own-scope placeholder (200) instead of a JSON
        # 403, and still never reaches the fleet board downstream.
        # Arrange
        request = _request(self.rf, self.customer, "/apps/cards/")
        # Act
        result = _run(request)
        # Assert
        assert result == (200, None, False)

    def test_non_staff_is_refused_on_an_opened_write_route(self):
        # Arrange
        request = _request(
            self.rf, self.customer, "/apps/cards/dm/thread/operator", "post"
        )
        # Act
        result = _run(request)
        # Assert
        assert result == (403, "cards-board-staff-only", False)

    def test_staff_reaches_the_board(self):
        # Arrange
        request = _request(self.rf, self.staff, "/apps/cards/tasks")
        # Act
        result = _run(request)
        # Assert
        assert result == (200, None, True)

    def test_superuser_reaches_the_board(self):
        # Arrange
        request = _request(self.rf, self.superuser, "/apps/cards/tasks")
        # Act
        result = _run(request)
        # Assert
        assert result == (200, None, True)

    def test_anonymous_data_fetch_still_gets_the_signed_out_401(self):
        # Arrange
        request = _request(self.rf, AnonymousUser(), "/apps/cards/tasks")
        # Act
        status, _reason, reached = _run(request)
        # Assert
        assert (status, reached) == (401, False)

    def test_non_cards_path_is_untouched_for_non_staff(self):
        # Arrange
        request = _request(self.rf, self.customer, "/apps/scholar/")
        # Act
        result = _run(request)
        # Assert
        assert result == (200, None, True)
