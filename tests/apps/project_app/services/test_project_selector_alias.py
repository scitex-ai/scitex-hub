"""Legacy PK normalization stays inside Hub's current access-scoped queryset."""

from types import SimpleNamespace

import pytest

from apps.infra.project_app.services import project_scope


@pytest.mark.parametrize("pk", [17, 21])
def test_numeric_selector_uses_authorized_scope_and_returns_owner_slug(monkeypatch, pk):
    user = SimpleNamespace(is_authenticated=True)
    project = SimpleNamespace(
        pk=pk, owner=SimpleNamespace(username="fixture-owner"), slug="alpha"
    )
    events = []

    class Scope:
        def filter(self, **lookup):
            events.append(lookup)
            return self

        def first(self):
            return project

    def authorized_scope(selected_user):
        assert selected_user is user
        events.append("access-scope")
        return Scope()

    monkeypatch.setattr(project_scope, "accessible_projects", authorized_scope)
    actual = project_scope.HubProjectProvider().canonical_project_id(
        SimpleNamespace(user=user), str(pk)
    )
    assert actual == "fixture-owner/alpha"
    assert events == ["access-scope", {"pk": pk}]


def test_unlisted_numeric_project_is_not_a_fallback(monkeypatch):
    scoped = SimpleNamespace(
        filter=lambda **lookup: SimpleNamespace(first=lambda: None)
    )
    monkeypatch.setattr(project_scope, "accessible_projects", lambda user: scoped)
    user = SimpleNamespace(is_authenticated=True)
    actual = project_scope.HubProjectProvider().canonical_project_id(
        SimpleNamespace(user=user), "99"
    )
    assert actual is None


@pytest.mark.parametrize(
    "selector",
    [
        None,
        17,
        "",
        "alice/alpha",
        "../17",
        "-17",
        "0",
        "17.0",
        "１７",
        "9" * 20,
        str(2**63),
    ],
)
def test_invalid_selectors_never_query_access_or_storage(monkeypatch, selector):
    monkeypatch.setattr(
        project_scope,
        "accessible_projects",
        lambda user: pytest.fail("invalid selector queried projects"),
    )
    user = SimpleNamespace(is_authenticated=True)
    actual = project_scope.HubProjectProvider().canonical_project_id(
        SimpleNamespace(user=user), selector
    )
    assert actual is None


@pytest.mark.parametrize("user", [None, SimpleNamespace(is_authenticated=False)])
def test_anonymous_alias_resolution_never_queries_projects(monkeypatch, user):
    monkeypatch.setattr(
        project_scope,
        "accessible_projects",
        lambda user: pytest.fail("anonymous queried projects"),
    )
    assert (
        project_scope.HubProjectProvider().canonical_project_id(
            SimpleNamespace(user=user), "17"
        )
        is None
    )
