# -*- coding: utf-8 -*-
# File: apps/infra/mcp_api/urls.py
"""Auto-generate URL patterns from discovered MCP tools.

URL patterns are built once at startup by _build_urlpatterns(),
called from McpApiConfig.ready().  Each MCP tool gets a dedicated
URL pattern that dispatches to ToolExecuteView.

URL mapping:
    plt_scatter                -> plt/scatter/
    stats_run_test             -> stats/run-test/
    writer_compile_manuscript  -> writer/compile-manuscript/
"""

from __future__ import annotations

import logging

from django.urls import path

from .views import ToolExecuteView, list_tools

logger = logging.getLogger(__name__)

app_name = "mcp_api"

# The listing endpoint is always present
urlpatterns = [
    path("", list_tools, name="tool-list"),
]


def _build_urlpatterns():
    """Discover MCP tools and register a URL pattern for each.

    Called from McpApiConfig.ready().  Appends to the module-level
    urlpatterns list so Django's URL resolver picks them up.
    """
    try:
        from .discovery import get_tool_registry
    except Exception as exc:
        logger.error("Failed to import MCP tool discovery: %s", exc)
        return

    try:
        registry = get_tool_registry()
    except Exception as exc:
        logger.error("Failed to discover MCP tools for REST API: %s", exc)
        return

    count = 0
    for tool_name, tool_info in registry.items():
        url_path = tool_info.url_path
        # Create a view instance with the tool info baked in
        view = ToolExecuteView.as_view()
        pattern = path(
            f"{url_path}/",
            view,
            kwargs={"tool_path": url_path},
            name=f"tool-{tool_name}",
        )
        urlpatterns.append(pattern)
        count += 1

    logger.info("MCP REST API: registered %d tool URL patterns", count)


# EOF
