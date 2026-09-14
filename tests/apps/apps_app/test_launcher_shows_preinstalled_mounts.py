#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: tests/apps/apps_app/test_launcher_shows_preinstalled_mounts.py
"""Cards and Agents tiles are shown to EVERY signed-in user.

History. Earlier on 2026-09-14 the grid hid the Cards and Agents tiles from
users their mounts refuse (``can_open_mounted_app``), and this file (then
``test_launcher_hides_gated_mounts.py``) asserted they were hidden.

Operator ruling, 2026-09-14 15:48Z, reverses that: Cards and Agents are
PRE-INSTALLED apps shown to everyone, and only their CONTENT depends on the
user. "Removing the whole app is wrong." The mounts keep their own per-user
handling (the Cards mount is getting a friendly per-user empty page instead of
the JSON 403 in a separate change); the launcher no longer hides the tiles.

``SCITEX_HUB_INTERNAL_APPS_RELEASED=True`` reproduces the dev deployment, where
the non-staff user is past the release-channel gate (both manifests are still
``visibility: internal``), so a hidden tile could only come from a mount gate.
"""

import pytest
from django.contrib.auth.models import User
from django.test import RequestFactory, override_settings

from apps.infra.workspace_app.registry import get_all_modules
from apps.workspace.apps_app.views.launcher import launcher_context

PREINSTALLED = {"todo", "agents"}

pytestmark = pytest.mark.skipif(
    not PREINSTALLED <= {mod.name for mod in get_all_modules()},
    reason="Cards (scitex-cards) and Agents (scitex-agent-container) are optional "
    "plugins; without both registered there is no tile to show.",
)


def _tile_names(username: str, *, is_staff: bool) -> list[str]:
    user = User.objects.create_user(username=username, is_staff=is_staff)
    request = RequestFactory().get("/apps/")
    request.user = user
    request.session = {}
    return [tile["name"] for tile in launcher_context(request)["tiles"]]


@pytest.mark.django_db
@override_settings(SCITEX_HUB_INTERNAL_APPS_RELEASED=True)
def test_grid_shows_cards_and_agents_to_a_plain_user():
    # Arrange
    username = "preinstalled-member"
    # Act
    names = set(_tile_names(username, is_staff=False))
    # Assert
    assert names & PREINSTALLED == PREINSTALLED


@pytest.mark.django_db
@override_settings(SCITEX_HUB_INTERNAL_APPS_RELEASED=True)
def test_grid_shows_cards_and_agents_to_staff():
    # Arrange
    username = "preinstalled-staff"
    # Act
    names = set(_tile_names(username, is_staff=True))
    # Assert
    assert names & PREINSTALLED == PREINSTALLED


@pytest.mark.django_db
@override_settings(SCITEX_HUB_INTERNAL_APPS_RELEASED=True)
def test_a_plain_users_first_row_is_the_infrastructure_row():
    # Arrange
    username = "preinstalled-row"
    # Act
    first_row = _tile_names(username, is_staff=False)[:4]
    # Assert
    assert first_row == ["home", "discovery", "agents", "todo"]


# EOF
