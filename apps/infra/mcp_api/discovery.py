# -*- coding: utf-8 -*-
# File: apps/infra/mcp_api/discovery.py
"""Discover and catalog all MCP tools for REST API exposure.

Introspects the FastMCP server instance to find all registered tools,
filters out dangerous ones, and returns structured ToolInfo objects.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Exclusion rules -- these tools must NEVER be exposed via REST
# ---------------------------------------------------------------------------
EXCLUDED_PREFIXES = frozenset(
    {
        "project_exec_python",
        "project_exec_shell",
        "cloud_onsite_eval_js",
        "onsite_eval_js",
        "browser_",
        "capture_",
        "audio_",
        "social_",
        "notification_",
        "tunnel_",
        "dev_",
        # Host/agent lifecycle and command execution require their dedicated
        # control-plane authorization, not the generic REST "api" scope.
        "agent_",
        "container_",
    }
)

# Tools that can be accessed without authentication
PUBLIC_PREFIXES = frozenset(
    {
        "scholar_search",
        "introspect_",
        "docs_",
    }
)


@dataclass
class ToolInfo:
    """Structured information about a single MCP tool."""

    name: str
    description: str
    parameters: dict[str, Any]
    fn: Callable
    namespace: str
    url_path: str
    is_public: bool = False
    output_schema: Optional[dict[str, Any]] = None
    tags: list[str] = field(default_factory=list)


def _tool_name_to_url_path(name: str) -> str:
    """Convert MCP tool name to a REST URL path segment.

    Examples:
        plt_scatter                    -> plt/scatter
        stats_run_test                 -> stats/run-test
        writer_compile_manuscript      -> writer/compile-manuscript
        cloud_repo_clone               -> cloud/repo-clone
        project_list_files             -> project/list-files
    """
    parts = name.split("_", 1)
    namespace = parts[0]
    if len(parts) == 1:
        return namespace
    rest = parts[1].replace("_", "-")
    return f"{namespace}/{rest}"


def _is_excluded(name: str) -> bool:
    """Return True if this tool should NOT be exposed as REST."""
    names = [name]
    # Current and legacy Hub mount names must retain the same deny rules.
    if name.startswith(("cloud_", "hub_")):
        names.append(name.split("_", 1)[1])
    return any(
        candidate.startswith(prefix)
        for candidate in names
        for prefix in EXCLUDED_PREFIXES
    )


def _is_public(name: str) -> bool:
    """Return True if this tool can be accessed without authentication."""
    for prefix in PUBLIC_PREFIXES:
        if name.startswith(prefix):
            return True
    return False


def _bind_tool(server, name: str) -> Callable:
    """Invoke the public MCP protocol, including mounted tools and middleware."""

    async def invoke(**arguments):
        from fastmcp import Client

        async with Client(server) as client:
            result = await client.call_tool(name, arguments)
        if result.data is not None or not result.content:
            return result.data
        if len(result.content) == 1 and result.content[0].type == "text":
            return result.content[0].text
        return [block.model_dump(mode="json") for block in result.content]

    return invoke


def _resolve_server(mcp_server=None):
    if mcp_server is not None:
        return mcp_server
    try:
        from scitex.mcp_server import FASTMCP_AVAILABLE
        from scitex.mcp_server import mcp as mcp_server
    except ImportError as exc:
        raise RuntimeError(
            "scitex MCP server is not importable. Install the MCP extras."
        ) from exc
    if not FASTMCP_AVAILABLE or mcp_server is None:
        raise RuntimeError("FastMCP is not available or MCP server is not initialized.")
    return mcp_server


def get_tool_metadata(mcp_server=None) -> dict[str, dict[str, Any]]:
    """List protocol metadata without executing tools or relying on private attributes.

    Wire-format field names keep FastMCP 2/3 and MCP 2 SDK objects consistent.
    Missing providers raise an error rather than presenting an empty catalog.
    """
    from asgiref.sync import async_to_sync

    try:
        from fastmcp import Client
    except ImportError as exc:
        raise RuntimeError("FastMCP is not available; install the MCP extras.") from exc
    server = _resolve_server(mcp_server)

    async def list_tools():
        async with Client(server) as client:
            return await client.list_tools()

    return {
        tool.name: tool.model_dump(mode="json", by_alias=True)
        for tool in async_to_sync(list_tools)()
    }


def discover_tools(mcp_server=None) -> dict[str, ToolInfo]:
    """Discover REST-eligible tools; unavailable providers raise RuntimeError."""
    mcp_server = _resolve_server(mcp_server)
    all_tools = get_tool_metadata(mcp_server)
    result: dict[str, ToolInfo] = {}

    for tool_name in sorted(all_tools.keys()):
        if _is_excluded(tool_name):
            logger.debug("Excluding tool from REST API: %s", tool_name)
            continue

        tool_obj = all_tools[tool_name]
        namespace = tool_name.split("_", 1)[0]
        url_path = _tool_name_to_url_path(tool_name)

        result[tool_name] = ToolInfo(
            name=tool_name,
            description=tool_obj.get("description") or "",
            parameters=tool_obj["inputSchema"],
            output_schema=tool_obj.get("outputSchema"),
            fn=_bind_tool(mcp_server, tool_name),
            namespace=namespace,
            url_path=url_path,
            is_public=_is_public(tool_name),
            tags=[namespace],
        )

    logger.info(
        "MCP REST API: discovered %d tools (%d excluded)",
        len(result),
        len(all_tools) - len(result),
    )
    return result


# ---------------------------------------------------------------------------
# Singleton registry (populated once per process)
# ---------------------------------------------------------------------------
_registry: Optional[dict[str, ToolInfo]] = None


def get_tool_registry() -> dict[str, ToolInfo]:
    """Return the singleton tool registry, discovering tools on first call."""
    global _registry
    if _registry is None:
        _registry = discover_tools()
    return _registry


def get_tool_by_url_path(url_path: str) -> Optional[ToolInfo]:
    """Look up a tool by its URL path segment."""
    registry = get_tool_registry()
    for tool_info in registry.values():
        if tool_info.url_path == url_path:
            return tool_info
    return None


# EOF
