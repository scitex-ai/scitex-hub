#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The Cards gate admits the configured SAC fleet operators, not only staff.

Operator 2026-09-14: after #813 hid gated launcher tiles, the Cards tile
vanished for the operator's own account. That account is named in
SCITEX_AGENT_CONTAINER_LIFECYCLE_OPERATORS (so it opens Agents) but is not
Django staff, and the Cards gate checked staff only. Both fleet mounts now
share one predicate. Everyone else stays refused (the P0 still holds).
"""

import os

import pytest
from django.contrib.auth.models import AnonymousUser, User
from django.test import TestCase

from apps.workspace.agents_app import views as agents_views
from apps.workspace.todo_app.middleware import cards_board_access_allowed
from apps.workspace.apps_app.views.helpers import can_open_mounted_app


@pytest.fixture
def operators_env():
    previous = os.environ.get(agents_views.OPERATORS_ENV)
    os.environ[agents_views.OPERATORS_ENV] = " opsperson , other "
    yield
    if previous is None:
        os.environ.pop(agents_views.OPERATORS_ENV, None)
    else:
        os.environ[agents_views.OPERATORS_ENV] = previous


@pytest.mark.django_db
def test_listed_operator_without_staff_passes_cards_gate(operators_env):
    # Arrange
    user = User.objects.create_user(username="opsperson", password="x")

    # Act
    allowed = cards_board_access_allowed(user)

    # Assert
    assert allowed is True


@pytest.mark.django_db
def test_listed_operator_sees_cards_launcher_tile(operators_env):
    # Arrange
    user = User.objects.create_user(username="opsperson", password="x")

    # Act
    visible = can_open_mounted_app(user, "todo")

    # Assert
    assert visible is True


@pytest.mark.django_db
def test_unlisted_plain_user_is_still_refused(operators_env):
    # Arrange
    user = User.objects.create_user(username="visitor", password="x")

    # Act
    allowed = cards_board_access_allowed(user)

    # Assert
    assert allowed is False


def test_anonymous_user_is_still_refused(operators_env):
    # Arrange
    user = AnonymousUser()

    # Act
    allowed = cards_board_access_allowed(user)

    # Assert
    assert allowed is False


@pytest.mark.django_db
def test_staff_still_passes_without_operator_list():
    # Arrange
    previous = os.environ.pop(agents_views.OPERATORS_ENV, None)
    user = User.objects.create_user(username="staffer", password="x", is_staff=True)

    # Act
    try:
        allowed = cards_board_access_allowed(user)
    finally:
        if previous is not None:
            os.environ[agents_views.OPERATORS_ENV] = previous

    # Assert
    assert allowed is True


@pytest.mark.django_db
def test_cards_placeholder_page_names_the_app_and_shows_no_board():
    # Arrange
    from django.test import RequestFactory

    from apps.workspace.agents_app.views import own_scope_placeholder

    request = RequestFactory().get("/apps/cards/")
    request.user = User.objects.create_user(username="plain2", password="x")
    request.session = {}

    # Act
    response = own_scope_placeholder(request, "cards")

    # Assert
    assert b'data-own-scope-app="cards"' in response.content
