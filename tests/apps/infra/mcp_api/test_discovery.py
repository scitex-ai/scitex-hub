"""Exercise REST discovery with real local FastMCP servers, without model calls."""

import asyncio
import inspect

import pytest
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from fastmcp.server.middleware import Middleware

from apps.infra.mcp_api.discovery import discover_tools


def _mounted_server(marker):
    server = FastMCP("owned-rest-parent")
    child = FastMCP("owned-rest-child")

    @child.tool
    def sum_values(a: int, b: int = 1) -> dict:
        """Add two numbers without external services."""
        marker.write_text("called")
        return {"sum": a + b}

    mount_keyword = (
        "namespace"
        if "namespace" in inspect.signature(server.mount).parameters
        else "prefix"
    )
    server.mount(child, **{mount_keyword: "stats"})
    return server


def test_mounted_discovery_keeps_input_output_schemas_without_executing(tmp_path):
    marker = tmp_path / "callback"
    registry = discover_tools(_mounted_server(marker))
    tool = registry["stats_sum_values"]
    assert tool.parameters["properties"]["a"]["type"] == "integer"
    assert tool.parameters["required"] == ["a"]
    assert tool.output_schema["type"] == "object"
    assert tool.url_path == "stats/sum-values" and not tool.is_public
    assert not marker.exists()


def test_mounted_execution_returns_original_structured_values(tmp_path):
    marker = tmp_path / "callback"
    tool = discover_tools(_mounted_server(marker))["stats_sum_values"]
    assert asyncio.run(tool.fn(a=2, b=3)) == {"sum": 5}
    assert marker.read_text() == "called"


def test_mounted_execution_retains_protocol_validation(tmp_path):
    marker = tmp_path / "callback"
    tool = discover_tools(_mounted_server(marker))["stats_sum_values"]
    with pytest.raises(ToolError):
        asyncio.run(tool.fn(a="not-an-integer"))
    assert not marker.exists()


@pytest.mark.parametrize(
    "forbidden_name",
    [
        "project_exec_shell",
        "cloud_project_exec_shell",
        "hub_project_exec_python",
        "cloud_onsite_eval_js",
        "hub_onsite_eval_js",
        "agent_container_host_exec",
        "container_exec",
    ],
)
def test_excluded_tools_remain_absent_and_names_do_not_grant_public_execution(
    tmp_path, forbidden_name
):
    server = FastMCP("owned-policy")
    marker = tmp_path / "must-not-exist"

    @server.tool(name=forbidden_name)
    def forbidden() -> str:
        marker.write_text("forbidden")
        return "never executed"

    @server.tool(name="docs_search")
    def documentation() -> str:
        return "local documentation"

    registry = discover_tools(server)
    assert set(registry) == {"docs_search"}
    assert registry["docs_search"].is_public is False
    assert asyncio.run(registry["docs_search"].fn()) == "local documentation"
    assert not marker.exists()


def test_mounted_execution_runs_parent_middleware(tmp_path):
    server = _mounted_server(tmp_path / "callback")
    observed = []

    class ObserveCalls(Middleware):
        async def on_call_tool(self, context, call_next):
            observed.append(context.message.name)
            return await call_next(context)

    server.add_middleware(ObserveCalls())
    tool = discover_tools(server)["stats_sum_values"]
    assert asyncio.run(tool.fn(a=4)) == {"sum": 5}
    assert observed == ["stats_sum_values"]


def test_tool_errors_propagate_instead_of_becoming_success_results():
    server = FastMCP("owned-error")

    @server.tool(name="stats_fail")
    def fail() -> dict:
        raise ValueError("owned tool failure")

    tool = discover_tools(server)["stats_fail"]
    with pytest.raises(ToolError, match="owned tool failure"):
        asyncio.run(tool.fn())


def test_schema_free_text_is_not_discarded():
    server = FastMCP("owned-text")

    @server.tool(name="docs_legacy", output_schema=None)
    def text():
        return "unstructured documentation"

    tool = discover_tools(server)["docs_legacy"]
    assert asyncio.run(tool.fn()) == "unstructured documentation"


def test_docs_catalog_uses_the_same_mounted_protocol_schema(tmp_path):
    from apps.infra.public_app.config.mcp_tools import get_mcp_tools

    marker = tmp_path / "callback"
    catalog = get_mcp_tools(_mounted_server(marker))
    assert len(catalog) == 1 and catalog[0]["prefix"] == "stats_"
    tool = catalog[0]["tools"][0]
    assert tool["name"] == "stats_sum_values"
    assert tool["returns"] == "object"
    assert tool["params"] == [
        {"name": "a", "type": "integer", "default": "required"},
        {"name": "b", "type": "integer", "default": "1"},
    ]
    assert not marker.exists()
