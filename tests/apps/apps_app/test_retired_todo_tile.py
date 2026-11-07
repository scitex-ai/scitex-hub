#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""No second Cards tile from the stale pre-rebrand "todo" catalog row.

Prod DB held a stale public ("todo", "Cards", "fas fa-list-check") row next
to the plugin ("scitex-cards", ...) row, and launcher step 2 re-added it as
a duplicate Work tile. "todo" is tombstoned in _RETIRED_MODULE_IDS and its
row is deleted by migration 0023. Real client, real ORM; no mocks.
"""

from django.contrib.auth.models import User
from django.test import TestCase

from apps.workspace.apps_app.models import AppsModule


class StaleTodoRowNeverTilesTest(TestCase):
    def test_stale_public_todo_row_renders_no_tile(self):
        # Arrange — the exact stale row shape from prod, plus the plugin row.
        AppsModule.objects.create(
            module_name="todo",
            label="Cards",
            icon="fas fa-list-check",
            visibility="public",
        )
        AppsModule.objects.create(
            module_name="scitex-cards",
            label="Cards",
            icon="fas fa-diagram-project",
            visibility="public",
        )
        user = User.objects.create_user(username="todo-dedupe-user")
        self.client.force_login(user)

        # Act
        tiles = self.client.get("/apps/").context["tiles"]

        # Assert
        assert "todo" not in [tile["name"] for tile in tiles]
