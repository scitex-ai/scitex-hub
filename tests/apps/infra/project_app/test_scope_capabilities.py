"""Real SDK dispatch honors host capability flags without changing refused state."""

import json
from pathlib import Path

import pytest
from django.test import RequestFactory, override_settings
from scitex_sdk.app.embed import ScitexAppConfig
from scitex_sdk.ui.project_scope import (
    LocalProjectProvider,
    ProjectSelection,
    scoped_project_listing_view,
)

from apps.infra.project_app.scope_capabilities import (
    ScopeCapabilityProjectProvider,
    request_scope_app,
)

urlpatterns = []


class ScopeFixtureConfig(ScitexAppConfig):
    name = "scitex_sdk.creator"
    label = "scope_capability_fixture"
    path = str(Path(__file__).resolve().parents[3] / "fixtures" / "scope_capabilities")


@pytest.fixture(autouse=True)
def installed_scope_fixture():
    with override_settings(
        INSTALLED_APPS=[f"{__name__}.ScopeFixtureConfig"],
        ROOT_URLCONF=__name__,
        MIDDLEWARE=[],
    ):
        yield


class FilesystemScopedProvider(LocalProjectProvider):
    """A concrete provider whose committed state is observable on disk."""

    def __init__(self, root):
        super().__init__(root)
        self.state = root / ".scope.json"

    def current_scope(self, request):
        if not self.state.exists():
            return None
        return ProjectSelection(**json.loads(self.state.read_text()))

    def remember_scope(self, request, selection):
        self.state.write_text(
            json.dumps({"scope": selection.scope, "id": selection.id})
        )

    def last_visited(self, request=None):
        selection = self.current_scope(request)
        return selection.id if selection else None

    def remember(self, request, project_id):
        self.remember_scope(request, ProjectSelection("project", project_id))


@pytest.mark.parametrize(
    "user,project", [(True, True), (True, False), (False, True), (False, False)]
)
def test_four_capability_combinations_are_visible_and_enforced(tmp_path, user, project):
    # Arrange
    (tmp_path / "paper").mkdir()
    raw = FilesystemScopedProvider(tmp_path)
    provider = ScopeCapabilityProjectProvider(raw)
    view = scoped_project_listing_view(provider)
    factory = RequestFactory()
    policy = {"fixture": {"user": user, "project": project}}
    results = []
    # Act
    with override_settings(SCITEX_APP_SCOPE_CAPABILITIES=policy):
        listing = json.loads(
            view(factory.get("/api/project/scope/?app=fixture")).content
        )
        for payload, allowed in [
            ({"scope": "user", "id": None}, user),
            ({"scope": "project", "id": "paper"}, project),
            ({"id": "paper"}, project),
        ]:
            before = raw.state.read_bytes() if raw.state.exists() else None
            response = view(
                factory.post(
                    "/api/project/scope/?app=fixture",
                    payload,
                    content_type="application/json",
                )
            )
            after = raw.state.read_bytes() if raw.state.exists() else None
            results.append(
                (
                    response.status_code == (200 if allowed else 403),
                    allowed or before == after,
                )
            )
    # Assert
    assert (
        bool(listing.get("user_scope_disabled_reason")) == (not user)
        and listing["projects"][0].get("disabled", False) == (not project)
        and all(status and unchanged for status, unchanged in results)
    )


@pytest.mark.parametrize("scope", ["user", "project"])
def test_direct_provider_refuses_disabled_scope_without_persisting(tmp_path, scope):
    # Arrange
    (tmp_path / "paper").mkdir()
    raw = FilesystemScopedProvider(tmp_path)
    provider = ScopeCapabilityProjectProvider(raw)
    request = RequestFactory().get("/apps/fixture/")
    selection = ProjectSelection(scope, "paper" if scope == "project" else None)
    # Act
    with override_settings(
        SCITEX_APP_SCOPE_CAPABILITIES={"fixture": {"user": False, "project": False}}
    ):
        with pytest.raises(ValueError):
            provider.remember_scope(request, selection)
    # Assert
    assert not raw.state.exists()


def test_mounted_app_wins_over_forged_query():
    # Arrange
    request = RequestFactory().get("/apps/writer/?app=scholar")
    # Act
    app = request_scope_app(request)
    # Assert
    assert app == "writer"


def test_provider_context_preserves_query_and_fragment(tmp_path):
    # Arrange
    provider = ScopeCapabilityProjectProvider(FilesystemScopedProvider(tmp_path))
    request = RequestFactory().get("/apps/writer/?app=scholar")
    # Act
    url = provider.project_provider_url(
        request, "/api/project/scope/?x=1&app=scholar#picker"
    )
    # Assert
    assert url == "/api/project/scope/?x=1&app=writer#picker"


def test_unavailable_stored_scope_is_unselected_without_rewriting(tmp_path):
    # Arrange
    (tmp_path / "paper").mkdir()
    raw = FilesystemScopedProvider(tmp_path)
    raw.remember_scope(None, ProjectSelection("user"))
    before = raw.state.read_bytes()
    view = scoped_project_listing_view(ScopeCapabilityProjectProvider(raw))
    # Act
    with override_settings(
        SCITEX_APP_SCOPE_CAPABILITIES={"fixture": {"user": False, "project": True}}
    ):
        result = json.loads(
            view(RequestFactory().get("/api/project/scope/?app=fixture")).content
        )
    # Assert
    assert (
        result["current"] is None
        and "current_scope" not in result
        and raw.state.read_bytes() == before
    )


def test_unknown_app_fails_closed_without_hiding_choices(tmp_path):
    # Arrange
    (tmp_path / "paper").mkdir()
    view = scoped_project_listing_view(
        ScopeCapabilityProjectProvider(FilesystemScopedProvider(tmp_path))
    )
    # Act
    with override_settings(SCITEX_APP_SCOPE_CAPABILITIES={}):
        result = json.loads(
            view(RequestFactory().get("/api/project/scope/?app=unknown")).content
        )
    # Assert
    assert result["projects"][0]["disabled"] and result["user_scope_disabled_reason"]


class DeniedFixtureConfig(ScopeFixtureConfig):
    path = str(
        Path(__file__).resolve().parents[3] / "fixtures" / "scope_capabilities_denied"
    )


def test_deployment_override_cannot_enable_leaf_unsupported_operations(tmp_path):
    # Arrange
    (tmp_path / "paper").mkdir()
    view = scoped_project_listing_view(
        ScopeCapabilityProjectProvider(FilesystemScopedProvider(tmp_path))
    )
    # Act
    with override_settings(
        INSTALLED_APPS=[f"{__name__}.DeniedFixtureConfig"],
        SCITEX_APP_SCOPE_CAPABILITIES={
            "fixture-denied": {"user": True, "project": True}
        },
    ):
        result = json.loads(
            view(RequestFactory().get("/api/project/scope/?app=fixture-denied")).content
        )
    # Assert
    assert result["projects"][0]["disabled"] and result["user_scope_disabled_reason"]


def test_leaf_manifest_controls_support_without_host_registry(tmp_path):
    # Arrange
    (tmp_path / "paper").mkdir()
    view = scoped_project_listing_view(
        ScopeCapabilityProjectProvider(FilesystemScopedProvider(tmp_path))
    )
    # Act
    with override_settings(SCITEX_APP_SCOPE_CAPABILITIES={}):
        result = json.loads(
            view(RequestFactory().get("/api/project/scope/?app=fixture")).content
        )
    # Assert
    assert (
        not result["projects"][0].get("disabled")
        and "user_scope_disabled_reason" not in result
    )


def test_actual_callback_owner_resolves_host_mounted_alias(tmp_path):
    # Arrange
    from django.urls import path
    from scitex_sdk.creator.views import index

    global urlpatterns
    urlpatterns = [path("apps/sdk/", index)]
    (tmp_path / "paper").mkdir()
    view = scoped_project_listing_view(
        ScopeCapabilityProjectProvider(FilesystemScopedProvider(tmp_path))
    )
    # Act
    with override_settings(ROOT_URLCONF=__name__, SCITEX_APP_SCOPE_CAPABILITIES={}):
        result = json.loads(
            view(RequestFactory().get("/api/project/scope/?app=sdk")).content
        )
    # Assert
    assert (
        not result["projects"][0].get("disabled")
        and "user_scope_disabled_reason" not in result
    )


_page_provider = None
_page_work = []


def _resolved_scope_page(request):
    from django.http import JsonResponse
    from scitex_sdk.ui.project_scope import resolve_project

    project = resolve_project(
        request, _page_provider, explicit=request.GET.get("project")
    )
    _page_work.append(project)
    return JsonResponse({"project": project})


@pytest.mark.parametrize("supported", [False, True])
def test_real_client_disabled_scope_is_403_before_work_and_preferences(
    tmp_path, monkeypatch, supported, caplog
):
    import sys

    from django.core.exceptions import PermissionDenied
    from django.test import Client
    from django.urls import path

    global urlpatterns
    urlpatterns = [path("apps/fixture/", _resolved_scope_page)]
    (tmp_path / "paper").mkdir()
    raw = FilesystemScopedProvider(tmp_path)
    provider = ScopeCapabilityProjectProvider(raw)
    monkeypatch.setattr(sys.modules[__name__], "_page_provider", provider)
    monkeypatch.setattr(sys.modules[__name__], "_page_work", [])
    with override_settings(
        ROOT_URLCONF=__name__,
        MIDDLEWARE=[],
        SCITEX_APP_SCOPE_CAPABILITIES={"fixture": {"user": True, "project": supported}},
    ):
        reason = provider.list_projects(RequestFactory().get("/apps/fixture/"))[
            0
        ].disabled_reason
        response = Client().get("/apps/fixture/?project=paper")
    if supported:
        assert (
            response.status_code,
            _page_work,
            json.loads(raw.state.read_text()),
        ) == (200, ["paper"], {"scope": "project", "id": "paper"})
    else:
        assert (
            response.status_code,
            any(
                isinstance(record.exc_info[1], PermissionDenied)
                and str(record.exc_info[1]) == reason
                for record in caplog.records
                if record.exc_info
            ),
            _page_work,
            raw.state.exists(),
        ) == (403, True, [], False)


@pytest.mark.parametrize("selector", ["unknown", "../foreign"])
def test_unknown_or_unauthorized_project_keeps_value_error_and_state(
    tmp_path, selector
):
    raw = FilesystemScopedProvider(tmp_path)
    provider = ScopeCapabilityProjectProvider(raw)
    request = RequestFactory().get("/apps/fixture/")
    with pytest.raises(ValueError, match="project not accessible"):
        provider.remember(request, selector)
    assert not raw.state.exists()
