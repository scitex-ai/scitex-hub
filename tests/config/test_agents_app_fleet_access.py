"""Agents mount authentication and SAC identity-scope contract."""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory

from apps.workspace.agents_app import views


@pytest.mark.parametrize(
    ("view_name", "kwargs"),
    (("index", {}), ("fleet_api", {}), ("detail", {"name": "worker"})),
)
def test_anonymous_requests_never_reach_sac(monkeypatch, view_name, kwargs):
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

    assert response.status_code == 302


def test_sac_resolves_the_authenticated_hub_identity():
    authorization = pytest.importorskip(
        "scitex_agent_container._django._authorization"
    )
    request = SimpleNamespace(
        user=SimpleNamespace(is_authenticated=True, username="alice")
    )

    assert authorization.resolve_identity(request) == "alice"


def test_sac_scope_hides_cross_host_rows_from_an_ordinary_identity(monkeypatch):
    authorization = pytest.importorskip(
        "scitex_agent_container._django._authorization"
    )
    monkeypatch.delenv("SCITEX_AGENT_CONTAINER_CROSSHOST_OPERATORS", raising=False)
    rows = [
        {"name": "own", "host": "local"},
        {"name": "other-user", "host": "other.example"},
    ]

    scoped = authorization.scope_rows(rows, "alice")

    assert [row["name"] for row in scoped] == ["own"]
    assert scoped[0]["scope"] == "own"
