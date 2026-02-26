#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: src/scitex_cloud/_mcp_tools/context.py
"""Web app context tools for FastMCP server.

Expose web app state (page, skills, actions) and browser interaction
(JS eval, UI actions) as MCP tools for AI agents.
"""

from .api import _json, _make_request


def register_context_tools(mcp) -> None:
    """Register context/UI tools with FastMCP server."""

    @mcp.tool()
    async def cloud_get_context(page: str = "") -> str:
        """[cloud] Get web app context: username, page, skills, available actions.

        Returns the current user, active skill for the page, all registered
        app skills, available UI actions, and media rendering capabilities.
        """
        result = _make_request(
            "GET",
            "/llm/api/context/",
            data={"page": page},
        )
        return _json(result)

    @mcp.tool()
    async def cloud_eval_js(code: str, timeout: int = 10) -> str:
        """[cloud] Evaluate JavaScript in user's browser and return result.

        Sends JS code to the user's browser via WebSocket relay,
        waits for the evaluation result, and returns it.
        Timeout is capped at 30 seconds server-side.
        """
        result = _make_request(
            "POST",
            "/llm/api/eval-js/",
            data={"code": code, "timeout": timeout},
        )
        return _json(result)

    @mcp.tool()
    async def cloud_ui_action(steps: list, delay_ms: int = 900) -> str:
        """[cloud] Drive browser UI: navigate, highlight, click, fill, scroll.

        Steps is a list of action dicts, e.g.:
        [{"action": "navigate", "url": "/writer/"},
         {"action": "click", "selector": "#save-btn"}]
        """
        result = _make_request(
            "POST",
            "/llm/api/ui-action/",
            data={"steps": steps, "delay_ms": delay_ms},
        )
        return _json(result)


# EOF
