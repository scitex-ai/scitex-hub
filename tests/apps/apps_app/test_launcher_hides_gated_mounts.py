#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: tests/apps/apps_app/test_launcher_hides_gated_mounts.py
"""A launcher tile is shown only when opening it would not 403.

Operator, 2026-09-14: Cards and Agents are meant to become usable by everyone
(scoped to the user's own data); until then their mounts are gated —
/apps/cards/ is staff-only (JSON 403, todo_app/middleware.py) and /apps/agents/
admits superuser, staff or a listed SAC operator (plain-text 403,
agents_app/views.py). Yet on a development deployment every signed-in user saw
both tiles, because the internal-app release channel lets them see internal
apps. The grid launcher and the header app launcher now apply the mounts' own
predicates.

``SCITEX_HUB_INTERNAL_APPS_RELEASED=True`` reproduces the dev deployment, where
the non-staff user is past the release-channel gate and ONLY the mount gate can
hide the tiles.
"""

import pytest
from django.contrib.auth.models import User
from django.test import RequestFactory, override_settings

from apps.infra.workspace_app.registry import get_all_modules
from apps.workspace.apps_app.views.launcher import launcher_context
from config.context_processors import header_app_launcher

GATED = {"todo", "agents"}

pytestmark = pytest.mark.skipif(
    not GATED <= {mod.name for mod in get_all_modules()},
    reason="Cards (scitex-cards) and Agents (scitex-agent-container) are optional "
    "plugins; without both registered there is no tile to gate.",
)


def _request(username: str, *, is_staff: bool):
    user = User.objects.create_user(username=username, is_staff=is_staff)
    request = RequestFactory().get("/")
    request.user = user
    request.session = {}
    return request


@pytest.mark.django_db
@override_settings(SCITEX_HUB_INTERNAL_APPS_RELEASED=True)
def test_grid_launcher_hides_cards_and_agents_from_a_non_staff_user():
    # Arrange
    request = _request("gate-tiles-member", is_staff=False)
    # Act
    names = {tile["name"] for tile in launcher_context(request)["tiles"]}
    # Assert
    assert names & GATED == set()


@pytest.mark.django_db
@override_settings(SCITEX_HUB_INTERNAL_APPS_RELEASED=True)
def test_grid_launcher_shows_cards_and_agents_to_staff():
    # Arrange
    request = _request("gate-tiles-staff", is_staff=True)
    # Act
    names = {tile["name"] for tile in launcher_context(request)["tiles"]}
    # Assert
    assert names & GATED == GATED


@pytest.mark.django_db
@override_settings(SCITEX_HUB_INTERNAL_APPS_RELEASED=True)
def test_header_launcher_hides_cards_and_agents_from_a_non_staff_user():
    # Arrange
    request = _request("gate-header-member", is_staff=False)
    # Act
    ids = {app["id"] for app in header_app_launcher(request)["header_apps"]}
    # Assert
    assert ids & GATED == set()


@pytest.mark.django_db
@override_settings(SCITEX_HUB_INTERNAL_APPS_RELEASED=True)
def test_header_launcher_shows_cards_and_agents_to_staff():
    # Arrange
    request = _request("gate-header-staff", is_staff=True)
    # Act
    ids = {app["id"] for app in header_app_launcher(request)["header_apps"]}
    # Assert
    assert ids & GATED == GATED


@pytest.mark.django_db
@override_settings(SCITEX_HUB_INTERNAL_APPS_RELEASED=True)
def test_grid_launcher_keeps_the_curated_order_for_the_remaining_tiles():
    # Arrange
    from apps.workspace.apps_app.views.launcher_order import default_order_value

    request = _request("gate-order-member", is_staff=False)
    # Act
    names = [tile["name"] for tile in launcher_context(request)["tiles"]]
    # Assert
    assert names == sorted(names, key=default_order_value)
