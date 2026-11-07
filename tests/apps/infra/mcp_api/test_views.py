"""REST responses retain validation and anonymous-access policy."""

import inspect
import json

import pytest
from fastmcp import FastMCP
from rest_framework.test import APIRequestFactory
from rest_framework.test import force_authenticate

from apps.infra.mcp_api import discovery
from apps.infra.mcp_api.views import ToolExecuteView


@pytest.fixture
def owned_registry(tmp_path):
    marker = tmp_path / "callback"
    server = FastMCP("owned-http-parent")
    child = FastMCP("owned-http-child")

    @child.tool
    def echo(value: int) -> dict:
        marker.write_text("called")
        return {"value": value}

    mount_key = (
        "namespace"
        if "namespace" in inspect.signature(server.mount).parameters
        else "prefix"
    )
    server.mount(child, **{mount_key: "docs"})

    @server.tool(name="stats_private")
    def private() -> str:
        marker.write_text("private")
        return "private result"

    previous = discovery._registry
    discovery._registry = discovery.discover_tools(server)
    try:
        yield marker
    finally:
        discovery._registry = previous


def test_public_mounted_tool_returns_the_native_json_payload(owned_registry):
    request = APIRequestFactory().post(
        "/api/v1/tools/docs/echo/", {"value": 7}, format="json"
    )
    response = ToolExecuteView.as_view()(request, tool_path="docs/echo")
    payload = json.loads(response.content)
    assert response.status_code == 200
    assert payload["success"] is True and payload["data"] == {"value": 7}
    assert owned_registry.read_text() == "called"


def test_invalid_rest_parameters_do_not_execute_the_tool(owned_registry):
    request = APIRequestFactory().post(
        "/api/v1/tools/docs/echo/", {"value": "bad"}, format="json"
    )
    response = ToolExecuteView.as_view()(request, tool_path="docs/echo")
    assert response.status_code == 400
    assert json.loads(response.content)["error_code"] == "VALIDATION_ERROR"
    assert not owned_registry.exists()


def test_anonymous_requests_cannot_execute_private_tools(owned_registry):
    request = APIRequestFactory().post(
        "/api/v1/tools/stats/private/", {}, format="json"
    )
    response = ToolExecuteView.as_view()(request, tool_path="stats/private")
    assert response.status_code in {401, 403}
    assert not owned_registry.exists()


@pytest.mark.parametrize(
    "is_staff,is_superuser,is_active,allowed",
    [
        (False, False, True, False),
        (True, False, True, False),
        (True, True, False, False),
        (True, True, True, True),
    ],
)
def test_private_tool_requires_an_active_platform_operator(
    owned_registry, is_staff, is_superuser, is_active, allowed
):
    from django.contrib.auth import get_user_model

    user = get_user_model()(
        username="owned-rest-identity",
        is_staff=is_staff,
        is_superuser=is_superuser,
        is_active=is_active,
    )
    request = APIRequestFactory().post(
        "/api/v1/tools/stats/private/", {}, format="json"
    )
    force_authenticate(request, user=user)
    response = ToolExecuteView.as_view()(request, tool_path="stats/private")
    assert response.status_code == (200 if allowed else 403)
    assert owned_registry.exists() is allowed


def test_catalog_declares_operator_access_for_private_tools(owned_registry):
    from apps.infra.mcp_api.views import list_tools

    response = list_tools(APIRequestFactory().get("/api/v1/tools/"))
    payload = json.loads(response.content)
    tools = {
        t["name"]: t for category in payload["namespaces"] for t in category["tools"]
    }
    assert tools["stats_private"]["access"] == "operator"
    assert tools["docs_echo"]["access"] == "public"
    assert "superuser" in payload["private_tool_access"]
    assert not owned_registry.exists()


@pytest.mark.django_db
@pytest.mark.parametrize(
    "superuser,active,scopes,expected",
    [
        (False, True, ["api"], 403),
        (False, True, ["*"], 403),
        (True, True, [], 403),
        (True, True, ["api"], 200),
        (True, True, ["*"], 200),
        (True, False, ["api"], 401),
    ],
)
def test_real_api_key_requires_operator_identity_and_scope(
    owned_registry, superuser, active, scopes, expected
):
    from django.contrib.auth import get_user_model
    from apps.infra.accounts_app.models.api_key import APIKey

    # Real auth rows; bulk creation leaves unrelated OS/Gitea provisioning
    # signals outside this authentication regression.
    user = get_user_model()(
        username="test_user_generic_rest",
        is_superuser=superuser,
        is_staff=superuser,
        is_active=active,
        password="!",
    )
    get_user_model().objects.bulk_create([user])
    _, token = APIKey.create_key(user, "owned-rest-key", scopes=scopes)
    request = APIRequestFactory().post(
        "/api/v1/tools/stats/private/",
        {},
        format="json",
        HTTP_AUTHORIZATION=f"Bearer {token}",
    )
    response = ToolExecuteView.as_view()(request, tool_path="stats/private")
    assert response.status_code == expected
    assert owned_registry.exists() is (expected == 200)
