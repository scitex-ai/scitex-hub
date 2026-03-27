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
        "browser_",
        "capture_",
        "audio_",
        "social_",
        "notification_",
        "tunnel_",
        "dev_",
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
    for prefix in EXCLUDED_PREFIXES:
        if name.startswith(prefix):
            return True
    return False


def _is_public(name: str) -> bool:
    """Return True if this tool can be accessed without authentication."""
    for prefix in PUBLIC_PREFIXES:
        if name.startswith(prefix):
            return True
    return False


def discover_tools() -> dict[str, ToolInfo]:
    """Introspect the FastMCP server and return eligible tools.

    Returns
    -------
    dict[str, ToolInfo]
        Mapping of tool name to ToolInfo for all REST-eligible tools.

    Raises
    ------
    RuntimeError
        If the MCP server is not available.  No fallback -- the error
        must be visible.
    """
    try:
        from scitex._mcp_tools._compat import get_tools_sync
        from scitex.mcp_server import FASTMCP_AVAILABLE
        from scitex.mcp_server import mcp as mcp_server
    except ImportError as exc:
        raise RuntimeError(
            "scitex MCP server is not importable.  "
            "Ensure scitex is installed with MCP extras."
        ) from exc

    if not FASTMCP_AVAILABLE or mcp_server is None:
        raise RuntimeError("FastMCP is not available or MCP server is not initialized.")

    all_tools = get_tools_sync(mcp_server)
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
            description=getattr(tool_obj, "description", "") or "",
            parameters=getattr(tool_obj, "parameters", {}) or {},
            output_schema=getattr(tool_obj, "output_schema", None),
            fn=tool_obj.fn,
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
