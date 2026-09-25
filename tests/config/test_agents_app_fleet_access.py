"""Only fleet operators may ACT through the Hub's /apps/agents/ mount.

Reads are login-only since 2026-09-26: scitex-agent-container >= 0.28
scopes every read by identity (resolve_identity + scope_rows, per-identity
snapshot cache), so an ordinary user only ever sees their own agents. What
these tests pin is the CONTROL boundary: lifecycle_action stays behind
_fleet_access_required, and the decorator itself still refuses ordinary
accounts so it cannot silently weaken.
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
    ),
)
def test_read_views_delegate_for_an_ordinary_user(
    monkeypatch, no_operators_env, view_name, kwargs
):
    # Reads are login-only: the hub passes them to the upstream, which
    # scopes rows to the user's identity. A missing delegate call would
    # mean the hub re-gated reads.
    # Arrange
    seen = {}

    def fake_delegate(view_name, request, *args, **kwargs):
        seen["view"] = view_name
        return HttpResponse("scoped-board")

    monkeypatch.setattr(views, "_delegate", fake_delegate)
    request = RequestFactory().get("/apps/agents/")
    request.user = _user()
    view = getattr(views, view_name)

    # Act
    response = view(request, **kwargs)

    # Assert
    assert response.status_code == 200
    assert seen["view"] == view_name


def test_lifecycle_action_refuses_an_ordinary_user(no_operators_env):
    # Control stays operator-gated at the hub boundary (upstream
    # can_control() gates it a second time).
    # Arrange
    request = RequestFactory().post("/apps/agents/worker/action")
    request.user = _user()

    # Act
    response = views.lifecycle_action(request, name="worker")

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


def test_ordinary_user_index_reaches_their_scoped_board(
    monkeypatch, no_operators_env
):
    # The placeholder era is over: the index delegates and the upstream
    # renders this user's own agents (or the empty state).
    # Arrange
    seen = {}

    def fake_delegate(view_name, request, *args, **kwargs):
        seen["view"] = view_name
        return HttpResponse("scoped-board")

    monkeypatch.setattr(views, "_delegate", fake_delegate)
    request = RequestFactory().get("/apps/agents/")
    request.user = _user()

    # Act
    response = views.index(request)

    # Assert
    assert response.status_code == 200
    assert seen["view"] == "index"
