"""Nested workspace context uses real native routing and registered targets."""
from pathlib import Path
import json
from django.test import RequestFactory, override_settings
from django.urls import include, path, resolve
from scitex_sdk.app.embed import ScitexAppConfig
from scitex_sdk.ui.project_scope import LocalProjectProvider, ProjectSelection, scoped_project_listing_view
from apps.infra.project_app.scope_capabilities import ScopeCapabilityProjectProvider, request_scope_app

# Include the real native dispatcher, not an imitation route or mocked kwargs.
urlpatterns = [path("apps/workspace/", include(("apps.infra.workspace_app.urls", "workspace_app")))]


class RegisteredLeaf(ScitexAppConfig):
    name = "scitex_sdk.creator"
    label = "test_workspace_target"
    path = str(Path(__file__).resolve().parents[3] / "fixtures" / "workspace_target_scope")


class FilesystemProvider(LocalProjectProvider):
    def current_scope(self, request):
        return None

    def remember_scope(self, request, selection):
        self.remember(request, selection.id)


def nested_request(query=""):
    request = RequestFactory().get("/apps/workspace/content/figrecipe/" + query)
    request.resolver_match = resolve(request.path_info)
    return request


def test_native_embedded_route_resolves_registered_leaf_not_container():
    # Arrange
    with override_settings(ROOT_URLCONF=__name__):
        request = nested_request("?app=scholar&module=writer")
        # Act
        app = request_scope_app(request)
    # Assert
    assert app == "figrecipe"


def test_native_embedded_provider_advertises_target_and_accepts_project(tmp_path):
    # Arrange
    (tmp_path / "paper").mkdir()
    raw = FilesystemProvider(tmp_path)
    provider = ScopeCapabilityProjectProvider(raw)
    with override_settings(ROOT_URLCONF=__name__, INSTALLED_APPS=[f"{__name__}.RegisteredLeaf"], SCITEX_APP_SCOPE_CAPABILITIES={}):
        request = nested_request("?app=scholar")
        view = scoped_project_listing_view(provider)
        # Act
        listing = json.loads(view(request).content)
        provider.remember(request, "paper")
        url = provider.project_provider_url(request, "/api/project/scope/")
    # Assert
    assert (listing["projects"][0].get("disabled", False) is False
            and listing["user_scope_disabled_reason"]
            and raw.last_visited(request) == "paper"
            and url == "/api/project/scope/?app=figrecipe")


def test_unregistered_nested_target_does_not_inherit_query_capability():
    # Arrange
    with override_settings(ROOT_URLCONF=__name__):
        request = RequestFactory().get("/apps/workspace/content/unknown-leaf/?app=scholar")
        request.resolver_match = resolve(request.path_info)
        # Act
        app = request_scope_app(request)
    # Assert
    assert app == "workspace"
