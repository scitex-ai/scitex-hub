#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: tests/apps/apps_app/test_home_dock_customizable.py
"""The dock is customisable like an iPhone's (card
hub-dock-customizable-single-placement-20260914): each app is in the dock or on
the grid, never both, and the dock is saved per user on the server.

Real client, real ORM, real templates; no mocks.
"""

import json
import re

from django.contrib.auth.models import User
from django.test import TestCase

from apps.workspace.apps_app.services.launcher_dock import (
    DEFAULT_DOCK_APPS,
    DOCK_CAPACITY,
    get_dock_apps,
)

DOCK_API = "/apps/store/api/dock/"


def _post_dock(client, dock):
    return client.post(
        DOCK_API, data=json.dumps({"dock": dock}), content_type="application/json"
    )


def _grid_apps(response) -> list[str]:
    return [
        cell["name"]
        for group in response.context["groups"]
        for cell in group["cells"]
        if not cell.get("is_slot")
    ]


def _rendered_dock_apps(response) -> list[str]:
    html = response.content.decode("utf-8")
    start = html.index('<nav class="site-dock"')
    dock = html[start : html.index("</nav>", start)]
    return re.findall(r'data-dock-item="([^"]+)"', dock)


class CustomisableDockTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username="dock-owner",
            password="TestPass123!",  # pragma: allowlist secret
        )
        cls.other_user = User.objects.create_user(
            username="dock-neighbour",
            password="TestPass123!",  # pragma: allowlist secret
        )

    def setUp(self):
        self.client.force_login(self.user)
        # Loading Home seeds the app catalogue the dock is saved beside.
        self.client.get("/apps/")

    def test_a_new_user_gets_the_default_dock(self):
        # Arrange
        user = self.other_user
        # Act
        dock = get_dock_apps(user)
        # Assert
        assert dock == ["launcher", "my_projects", "chat", "store"]

    def test_the_default_dock_is_what_the_dock_renders(self):
        # Arrange
        url = "/apps/public-projects/"
        # Act
        response = self.client.get(url)
        # Assert
        assert _rendered_dock_apps(response) == list(DEFAULT_DOCK_APPS)

    def test_an_app_in_the_dock_is_absent_from_the_grid(self):
        # Arrange
        url = "/apps/"
        # Act
        response = self.client.get(url)
        # Assert
        assert "chat" not in _grid_apps(response)

    def test_a_docked_app_keeps_its_tile_for_dragging_out(self):
        # Arrange
        url = "/apps/"
        # Act
        dock_tiles = self.client.get(url).context["dock_tiles"]
        # Assert
        assert "store" in {tile["name"] for tile in dock_tiles}

    def test_the_dock_order_persists_through_the_api(self):
        # Arrange
        dock = ["scholar", "launcher", "my_projects"]
        _post_dock(self.client, dock)
        # Act
        response = self.client.get("/apps/my-projects/")
        # Assert
        assert _rendered_dock_apps(response) == dock

    def test_a_saved_dock_belongs_to_its_user_only(self):
        # Arrange
        _post_dock(self.client, ["launcher", "scholar"])
        # Act
        self.client.force_login(self.other_user)
        response = self.client.get("/apps/my-projects/")
        # Assert
        assert _rendered_dock_apps(response) == list(DEFAULT_DOCK_APPS)

    def test_an_app_dragged_into_the_dock_leaves_the_grid(self):
        # Arrange
        _post_dock(self.client, ["launcher", "my_projects", "scholar"])
        # Act
        response = self.client.get("/apps/")
        # Assert
        assert "scholar" not in _grid_apps(response)

    def test_an_app_dragged_out_of_the_dock_returns_to_the_grid(self):
        # Arrange
        _post_dock(self.client, ["launcher", "my_projects", "store"])
        # Act
        response = self.client.get("/apps/")
        # Assert
        assert "chat" in _grid_apps(response)

    def test_the_api_refuses_more_apps_than_the_dock_holds(self):
        # Arrange
        too_many = ["launcher", "my_projects", "chat", "store", "scholar", "writer"]
        # Act
        response = _post_dock(self.client, too_many[: DOCK_CAPACITY + 1])
        # Assert
        assert response.status_code == 400

    def test_a_dock_at_capacity_is_accepted(self):
        # Arrange
        full = ["launcher", "my_projects", "chat", "store", "scholar", "writer"]
        # Act
        response = _post_dock(self.client, full[:DOCK_CAPACITY])
        # Assert
        assert response.status_code == 200

    def test_a_refused_dock_is_not_saved(self):
        # Arrange
        too_many = ["launcher", "my_projects", "chat", "store", "scholar", "writer"]
        # Act
        _post_dock(self.client, too_many[: DOCK_CAPACITY + 1])
        # Assert
        assert get_dock_apps(self.user) == list(DEFAULT_DOCK_APPS)

    def test_the_api_refuses_unknown_app_ids(self):
        # Arrange
        dock = ["launcher", "no-such-app"]
        # Act
        response = _post_dock(self.client, dock)
        # Assert
        assert response.status_code == 400

    def test_the_api_refuses_an_app_listed_twice(self):
        # Arrange
        dock = ["launcher", "my_projects", "my_projects"]
        # Act
        response = _post_dock(self.client, dock)
        # Assert
        assert response.status_code == 400

    def test_the_api_keeps_home_in_the_dock(self):
        # Arrange
        dock = ["my_projects", "chat"]
        # Act
        response = _post_dock(self.client, dock)
        # Assert
        assert response.status_code == 400


# EOF
