"""Execute genuine mounted FastMCP tools through their public server API."""

from __future__ import annotations

import inspect

import pytest
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

from apps.infra.mcp_api.discovery import _tool_executor


@pytest.mark.asyncio
async def test_provider_without_function_executes_through_its_server():
    child = FastMCP("child")

    @child.tool
    def sample(value: int) -> dict:
        return {"value": value}

    parent = FastMCP("parent")
    parent.mount(child, namespace="peer")
    tool = await parent.get_tool("peer_sample")
    executor = _tool_executor(parent, tool.name, tool)

    assert (
        hasattr(tool, "fn"),
        inspect.iscoroutinefunction(executor),
        await executor(value=7),
    ) == (
        False,
        True,
        {"value": 7},
    )


@pytest.mark.asyncio
async def test_provider_failure_remains_an_execution_error():
    child = FastMCP("child")

    @child.tool
    def sample(value: int) -> dict:
        raise ValueError("fixture failure")

    parent = FastMCP("parent")
    parent.mount(child, namespace="peer")
    tool = await parent.get_tool("peer_sample")
    executor = _tool_executor(parent, tool.name, tool)

    with pytest.raises(ToolError, match="fixture failure"):
        await executor(value=7)
