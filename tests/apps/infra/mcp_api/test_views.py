"""REST responses retain validation and anonymous-access policy."""

import inspect
import json

import pytest
from fastmcp import FastMCP
from rest_framework.test import APIRequestFactory

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
