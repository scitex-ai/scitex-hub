#!/usr/bin/env python3
# File: ./apps/public_app/config/mcp_tools.py
"""Programmatic MCP tool listing from the real scitex MCP server registry.

Introspects the actual FastMCP server to build the tool catalog shown on
the API docs page and exposed via the ``/api/mcp/tools/`` endpoint.
"""

from __future__ import annotations

import inspect
import logging

logger = logging.getLogger(__name__)

# Module prefix -> (display name, FontAwesome icon)
_MODULE_META: dict[str, tuple[str, str]] = {
    "app": ("App Management", "fa-th-large"),
    "audio": ("Audio", "fa-volume-up"),
    "capture": ("Capture", "fa-camera"),
    "clew": ("CLEW Pipelines", "fa-project-diagram"),
    "crossref": ("Crossref", "fa-database"),
    "dataset": ("Datasets", "fa-table"),
    "dev": ("Developer", "fa-code"),
    "introspect": ("Introspect", "fa-search"),
    "linter": ("Linter", "fa-check-circle"),
    "openalex": ("OpenAlex", "fa-university"),
    "plt": ("Plotting", "fa-chart-line"),
    "project": ("Project Files", "fa-folder-open"),
    "scholar": ("Scholar", "fa-graduation-cap"),
    "social": ("Social", "fa-share-alt"),
    "stats": ("Statistics", "fa-calculator"),
    "template": ("Templates", "fa-file-code"),
    "ui": ("UI / Notifications", "fa-bell"),
    "usage": ("Usage", "fa-tachometer-alt"),
    "writer": ("Writer / LaTeX", "fa-file-alt"),
}


def _get_return_type(tool_obj) -> str:
    """Extract return type annotation from the tool's underlying function."""
    if not hasattr(tool_obj, "fn") or tool_obj.fn is None:
        return "str"
    try:
        sig = inspect.signature(tool_obj.fn)
        ann = sig.return_annotation
        if ann != inspect.Parameter.empty:
            return ann.__name__ if hasattr(ann, "__name__") else str(ann)
    except Exception:
        pass
    return "str"


def _extract_first_line(description: str | None) -> str:
    """Get the first meaningful sentence from a tool description."""
    if not description:
        return ""
    # Strip [module] prefix if present
    text = description.strip()
    if text.startswith("["):
        idx = text.find("]")
        if idx != -1:
            text = text[idx + 1 :].strip()
    # Take first line or first sentence
    first_line = text.split("\n")[0].strip()
    if len(first_line) > 120:
        first_line = first_line[:117] + "..."
    return first_line


def _build_params(tool_obj) -> list[dict]:
    """Build parameter list from tool's JSON schema."""
    if not hasattr(tool_obj, "parameters") or not tool_obj.parameters:
        return []
    schema = tool_obj.parameters
    props = schema.get("properties", {})
    required = set(schema.get("required", []))
    params = []
    for name, info in props.items():
        ptype = info.get("type", "any")
        # Handle anyOf (optional types)
        if "anyOf" in info:
            types = [
                t.get("type", "?") for t in info["anyOf"] if t.get("type") != "null"
            ]
            ptype = types[0] if types else "any"
        default = "required" if name in required else repr(info.get("default", "None"))
        params.append({"name": name, "type": ptype, "default": default})
    return params


def get_mcp_tools() -> list[dict]:
    """Introspect the scitex MCP server and return tool catalog.

    Returns a list of category dicts, each with:
    - category: display name
    - icon: FontAwesome class
    - prefix: module prefix (e.g. "plt_")
    - tools: list of tool dicts with name, desc, params, returns
    """
    try:
        from scitex._mcp_tools._compat import get_tools_sync
        from scitex.mcp_server import FASTMCP_AVAILABLE
        from scitex.mcp_server import mcp as mcp_server
    except ImportError:
        logger.warning("scitex MCP server not available")
        return []

    if not FASTMCP_AVAILABLE or mcp_server is None:
        logger.warning("FastMCP not installed or MCP server not initialized")
        return []

    all_tools = get_tools_sync(mcp_server)

    # Group by module prefix
    modules: dict[str, list] = {}
    for tool_name in sorted(all_tools.keys()):
        prefix = tool_name.split("_")[0]
        if prefix not in modules:
            modules[prefix] = []
        modules[prefix].append(all_tools[tool_name])

    categories = []
    for prefix in sorted(modules.keys()):
        display_name, icon = _MODULE_META.get(
            prefix, (prefix.title(), "fa-puzzle-piece")
        )
        tools_list = []
        for tool_obj in modules[prefix]:
            tools_list.append(
                {
                    "name": tool_obj.name,
                    "desc": _extract_first_line(tool_obj.description),
                    "params": _build_params(tool_obj),
                    "returns": _get_return_type(tool_obj),
                }
            )
        categories.append(
            {
                "category": display_name,
                "icon": icon,
                "prefix": f"{prefix}_",
                "count": len(tools_list),
                "tools": tools_list,
            }
        )

    return categories


def get_mcp_tools_json() -> dict:
    """Return full MCP tool catalog as a JSON-serializable dict.

    Used by the ``/api/mcp/tools/`` endpoint.
    """
    categories = get_mcp_tools()
    total = sum(c["count"] for c in categories)
    return {
        "total": total,
        "categories": len(categories),
        "modules": categories,
    }


# Lazy-loaded singleton for the Django template context.
# Computed once per process on first access.
_cached: list[dict] | None = None


def _get_cached() -> list[dict]:
    global _cached
    if _cached is None:
        _cached = get_mcp_tools()
    return _cached


# This is what the view imports: ``from apps.infra.public_app.config.mcp_tools import MCP_TOOLS``
# Using a module-level property via __getattr__ for lazy loading.
def __getattr__(name: str):
    if name == "MCP_TOOLS":
        return _get_cached()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


# EOF
