"""Genuine FastMCP regression for the REST registry's unconditional .fn access.

Only pure local fixture functions run. The SciTeX registry ingress is isolated
so this suite does not import the umbrella or contact external providers.
"""

import asyncio
import importlib
import inspect
import json
import sys
from types import ModuleType

import pytest
from fastmcp import FastMCP
from fastmcp.server.providers.fastmcp_provider import FastMCPProviderTool
from fastmcp.tools import FunctionTool, ToolResult
from mcp.types import ImageContent, TextContent

pytestmark = pytest.mark.guards(
    defect="Provider-backed FastMCP tools have no fn and abort all REST discovery"
)


@pytest.fixture
def discovery():
    return importlib.import_module("apps.infra.mcp_api.discovery")


@pytest.fixture
def catalog(monkeypatch):
    """Replace only the umbrella ingress with an exact supplied tools mapping."""
    scitex = ModuleType("scitex")
    scitex.__path__ = []
    tools_package = ModuleType("scitex._mcp_tools")
    tools_package.__path__ = []
    compat = ModuleType("scitex._mcp_tools._compat")
    server_module = ModuleType("scitex.mcp_server")
    server_module.FASTMCP_AVAILABLE = True
    server_module.mcp = object()
    modules = {
        "scitex": scitex,
        "scitex._mcp_tools": tools_package,
        "scitex._mcp_tools._compat": compat,
        "scitex.mcp_server": server_module,
    }
    for name, module in modules.items():
        monkeypatch.setitem(sys.modules, name, module)

    def provide(tools):
        compat.get_tools_sync = lambda server: tools

    return provide


def _provider(fn, name):
    server = FastMCP("pure-rest-regression")
    tool = FunctionTool.from_function(fn, name=name)
    server.add_tool(tool)
    return FastMCPProviderTool.wrap(server, tool)


def test_function_tools_keep_native_callable_and_schema(discovery, catalog):
    # Arrange: construct the genuine pure local fixture and catalog.
    def stats_sum(value: int = 2) -> dict:
        """Return a pure fixture value."""
        return {"value": value}

    tool = FunctionTool.from_function(stats_sum, name="stats_sum")
    catalog({tool.name: tool})
    # Act: discover the catalog and execute the pure tool where required.
    info = discovery.discover_tools()[tool.name]
    # Assert: preserve every original oracle in its original order.
    assert (
        (info.fn is stats_sum)
        and (info.fn(value=7) == {"value": 7})
        and (info.parameters == tool.parameters)
        and (info.output_schema == tool.output_schema)
        and (info.description == tool.description)
        and (info.namespace == "stats")
        and (info.url_path == "stats/sum")
        and (info.is_public is False)
    )


def test_async_function_tools_keep_native_callable(discovery, catalog):
    # Arrange: construct the genuine pure local fixture and catalog.
    async def stats_async(value: int) -> dict:
        return {"value": value}

    tool = FunctionTool.from_function(stats_async, name="stats_async")
    catalog({tool.name: tool})
    # Act: discover the catalog and execute the pure tool where required.
    info = discovery.discover_tools()[tool.name]
    # Assert: preserve every original oracle in its original order.
    assert (
        (info.fn is stats_async)
        and (asyncio.run(info.fn(value=8)) == {"value": 8})
    )


def test_provider_tools_discover_and_run_genuine_local_server(discovery, catalog):
    # Arrange: construct the genuine pure local fixture and catalog.
    def stats_provider(value: int) -> dict:
        return {"value": value, "native": True}

    tool = _provider(stats_provider, "stats_provider")
    catalog({tool.name: tool})
    # Act: discover the catalog and execute the pure tool where required.
    info = discovery.discover_tools()[tool.name]
    result = asyncio.run(info.fn(value=9))
    # Assert: preserve every original oracle in its original order.
    assert (
        (not hasattr(tool, "fn"))
        and (inspect.iscoroutinefunction(info.fn))
        and (info.returns_tool_result is True)
        and (info.parameters == tool.parameters)
        and (info.output_schema == tool.output_schema)
        and (info.url_path == "stats/provider")
        and (info.is_public is False)
        and (isinstance(result, ToolResult))
        and (result.structured_content == {"value": 9, "native": True})
    )


def test_provider_in_mixed_catalog_does_not_abort_other_tools(discovery, catalog):
    # Arrange: construct the genuine pure local fixture and catalog.
    def pure(value: int = 1) -> dict:
        return {"value": value}

    native = FunctionTool.from_function(pure, name="docs_fixture")
    provider = _provider(pure, "stats_provider")
    catalog({provider.name: provider, native.name: native})
    # Act: discover the catalog and execute the pure tool where required.
    registry = discovery.discover_tools()
    # Assert: preserve every original oracle in its original order.
    assert (
        (list(registry) == ["docs_fixture", "stats_provider"])
        and (registry[native.name].is_public is True)
        and (registry[provider.name].is_public is False)
    )


def test_excluded_provider_is_filtered_before_callable_resolution(discovery, catalog):
    # Arrange: construct the genuine pure local fixture and catalog.
    def browser_fixture() -> dict:
        return {"should_not_run": True}

    provider = _provider(browser_fixture, "browser_fixture")
    catalog({provider.name: provider})
    # Act: exercise discovery once after the excluded provider is cataloged.
    registry = discovery.discover_tools()
    # Assert: preserve every original oracle in its original order.
    assert registry == {}


def test_structured_provider_result_preserves_content_metadata_and_aliases(
    discovery, catalog
):
    # Arrange: construct the genuine pure local fixture and catalog.
    content = [
        TextContent(type="text", text="fixture report", _meta={"origin": "fixture"}),
        ImageContent(type="image", data="AQ==", mimeType="image/png"),
    ]
    expected = {"value": [1, 2], "empty": {}}
    def stats_result() -> ToolResult:
        return ToolResult(content=content, structured_content=expected, meta={"trace": 3})

    provider = _provider(stats_result, "stats_result")
    catalog({provider.name: provider})
    # Act: discover the catalog and execute the pure tool where required.
    info = discovery.discover_tools()[provider.name]
    adapter = importlib.import_module("apps.infra.mcp_api._tool_adapter")
    response = adapter.tool_result_to_rest(asyncio.run(info.fn()))
    # Assert: preserve every original oracle in its original order.
    assert (
        (response["success"] is True)
        and (response["data"] == expected)
        and (response["meta"] == {"trace": 3})
        and (response["content"][0]["_meta"] == {"origin": "fixture"})
        and (response["content"][1]["mimeType"] == "image/png")
        and (json.loads(json.dumps(response)) == response)
    )


def test_empty_structured_result_is_not_replaced_by_content(discovery, catalog):
    # Arrange: construct the genuine pure local fixture and catalog.
    def stats_empty() -> ToolResult:
        return ToolResult(content="fixture text", structured_content={})

    provider = _provider(stats_empty, "stats_empty")
    catalog({provider.name: provider})
    # Act: discover the catalog and execute the pure tool where required.
    info = discovery.discover_tools()[provider.name]
    adapter = importlib.import_module("apps.infra.mcp_api._tool_adapter")
    response = adapter.tool_result_to_rest(asyncio.run(info.fn()))
    # Assert: preserve every original oracle in its original order.
    assert (
        (response["data"] == {})
        and (response["content"][0]["text"] == "fixture text")
    )


def test_content_only_provider_result_stays_native_content(discovery, catalog):
    # Arrange: construct the genuine pure local fixture and catalog.
    def stats_content() -> ToolResult:
        return ToolResult(content=[TextContent(type="text", text="native fixture")])

    provider = _provider(stats_content, "stats_content")
    catalog({provider.name: provider})
    # Act: discover the catalog and execute the pure tool where required.
    info = discovery.discover_tools()[provider.name]
    adapter = importlib.import_module("apps.infra.mcp_api._tool_adapter")
    response = adapter.tool_result_to_rest(asyncio.run(info.fn()))
    # Assert: preserve every original oracle in its original order.
    assert (
        (response["success"] is True)
        and (response["data"] == response["content"])
        and (response["data"][0]["text"] == "native fixture")
    )


def test_provider_error_result_is_not_reported_as_success(discovery, catalog):
    # Arrange: construct the genuine pure local fixture and catalog.
    def stats_error() -> ToolResult:
        return ToolResult(
            content="fixture failure",
            structured_content={"reason": "fixture"},
            meta={"trace": 4},
            is_error=True,
        )

    provider = _provider(stats_error, "stats_error")
    catalog({provider.name: provider})
    # Act: discover the catalog and execute the pure tool where required.
    info = discovery.discover_tools()[provider.name]
    adapter = importlib.import_module("apps.infra.mcp_api._tool_adapter")
    response = adapter.tool_result_to_rest(asyncio.run(info.fn()))
    # Assert: preserve every original oracle in its original order.
    assert (
        (response["success"] is False)
        and (response["error"] == "fixture failure")
        and (response["error_code"] == "EXECUTION_ERROR")
        and (response["data"] == {"reason": "fixture"})
        and (response["content"][0]["text"] == "fixture failure")
        and (response["meta"] == {"trace": 4})
    )


def test_provider_exception_propagates_to_existing_view_error_path(discovery, catalog):
    # Arrange: construct the genuine pure local fixture and catalog.
    def stats_raise() -> dict:
        raise ValueError("pure fixture exception")

    provider = _provider(stats_raise, "stats_raise")
    catalog({provider.name: provider})
    # Act: discover the catalog and execute the pure tool where required.
    info = discovery.discover_tools()[provider.name]
    # Assert: the genuine runner must preserve the exception oracle.
    with pytest.raises(Exception, match="pure fixture exception"):
        asyncio.run(info.fn())
