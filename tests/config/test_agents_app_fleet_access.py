"""Only fleet operators may read or act through the Hub's /apps/agents/ mount.

SAC's own Django views gate lifecycle_action on its operator list but leave
index, fleet_api, healthz and detail open, so the Hub adapter is the only
thing standing between an ordinary signed-in account and the whole agent
fleet. #789 enforced this; #803 briefly shipped login-only. These tests pin
the gate so it cannot silently fall back to login-only again.
"""

from __future__ import annotations

import os
from types import SimpleNamespace

import pytest
from django.http import HttpResponse
from django.test import RequestFactory

from apps.workspace.agents_app import views


def _reached_view(request, *args, **kwargs):
    return HttpResponse("reached")


_GUARDED = views._fleet_access_required(_reached_view)


def _user(**flags):
    base = {"is_authenticated": True, "is_staff": False, "is_superuser": False, "username": "alice"}
    base.update(flags)
    return SimpleNamespace(**base)


def _status_for(user) -> int:
    request = RequestFactory().get("/apps/agents/")
    request.user = user
    return _GUARDED(request).status_code


@pytest.fixture
def operators_env():
    previous = os.environ.get(views.OPERATORS_ENV)
    os.environ[views.OPERATORS_ENV] = " bob , carol "
    yield
    if previous is None:
        os.environ.pop(views.OPERATORS_ENV, None)
    else:
        os.environ[views.OPERATORS_ENV] = previous


@pytest.fixture
def no_operators_env():
    previous = os.environ.pop(views.OPERATORS_ENV, None)
    yield
    if previous is not None:
        os.environ[views.OPERATORS_ENV] = previous


def test_ordinary_signed_in_user_is_refused(no_operators_env):
    # Arrange
    user = _user()

    # Act
    status = _status_for(user)

    # Assert
    assert status == 403


def test_staff_user_reaches_the_view(no_operators_env):
    # Arrange
    user = _user(is_staff=True)

    # Act
    status = _status_for(user)

    # Assert
    assert status == 200


def test_superuser_reaches_the_view(no_operators_env):
    # Arrange
    user = _user(is_superuser=True)

    # Act
    status = _status_for(user)

    # Assert
    assert status == 200


def test_configured_operator_reaches_the_view(operators_env):
    # Arrange
    user = _user(username="carol")

    # Act
    status = _status_for(user)

    # Assert
    assert status == 200


def test_unlisted_user_is_refused_even_when_operators_are_configured(operators_env):
    # Arrange
    user = _user(username="mallory")

    # Act
    status = _status_for(user)

    # Assert
    assert status == 403


@pytest.mark.parametrize(
    ("view_name", "kwargs"),
    (
        ("fleet_api", {}),
        ("healthz", {}),
        ("detail", {"name": "worker"}),
        ("lifecycle_action", {"name": "worker"}),
    ),
)
def test_every_mounted_view_refuses_an_ordinary_user(no_operators_env, view_name, kwargs):
    # Arrange: the real view, so a missing gate would fall through to SAC
    request = RequestFactory().get("/apps/agents/")
    request.user = _user()
    view = getattr(views, view_name)

    # Act
    response = view(request, **kwargs)

    # Assert
    assert response.status_code == 403


def test_root_urlconf_resolves_agents_to_the_sac_index_when_installed():
    # Arrange
    pytest.importorskip("scitex_agent_container._django.urls")
    from django.urls import resolve

    # Act
    match = resolve("/apps/agents/")

    # Assert
    assert match.view_name == "scitex_agent_container:index"


@pytest.mark.django_db
def test_ordinary_user_index_gets_placeholder_page_not_the_fleet(no_operators_env):
    # Operator 2026-09-14: Agents is shown to everyone and only its content is
    # per user, so the index renders the own-scope placeholder instead of 403.
    # Arrange
    from django.contrib.auth.models import User

    request = RequestFactory().get("/apps/agents/")
    request.user = User.objects.create_user(username="plainuser", password="x")
    request.session = {}

    # Act
    response = views.index(request)

    # Assert
    assert b'data-own-scope-app="agents"' in response.content
