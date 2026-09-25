"""Only fleet operators may ACT through the Hub's /apps/agents/ mount.

Reads are login-only since 2026-09-26: scitex-agent-container >= 0.28
scopes every read by identity (resolve_identity + scope_rows, per-identity
snapshot cache), so an ordinary user only ever sees their own agents. What
these tests pin is the CONTROL boundary: lifecycle_action stays behind
_fleet_access_required, and the decorator itself still refuses ordinary
accounts so it cannot silently weaken.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory

from apps.workspace.agents_app import views


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
    request.user = AnonymousUser()
    monkeypatch.setattr(
        views,
        "_delegate",
        lambda *_a, **_kw: pytest.fail("anonymous request reached SAC"),
    )
    monkeypatch.setattr(
        "django.contrib.auth.decorators.resolve_url", lambda _value: "/auth/login/"
    )

    response = getattr(views, view_name)(request, **kwargs)

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


def test_sac_resolves_the_authenticated_hub_identity():
    authorization = pytest.importorskip(
        "scitex_agent_container._django._authorization"
    )
    request = SimpleNamespace(
        user=SimpleNamespace(is_authenticated=True, username="alice")
    )

    assert authorization.resolve_identity(request) == "alice"


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
