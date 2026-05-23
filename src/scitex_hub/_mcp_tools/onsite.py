#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: src/scitex_hub/_mcp_tools/onsite.py
"""On-site agent tools for workspace interaction (page capture, context, browser control)."""

from __future__ import annotations

import time

from .api import _json, _make_request


def register_onsite_tools(mcp) -> None:
    """Register on-site agent interaction tools with FastMCP server."""

    @mcp.tool()
    async def onsite_capture_page(
        project_id: str,
        message: str = "",
    ) -> str:
        """Use when the user asks to screenshot/capture/snapshot a SciTeX Cloud workspace page or app iframe; drop-in replacement for hand-rolled Playwright page.screenshot() scripts pointed at the live SciTeX Cloud workspace.

        Sends a capture request to the user's browser. The browser captures
        the page and saves the screenshot to scitex/downloads/.
        Returns the filepath of the saved screenshot.

        On first use, the user sees a permission modal to allow/deny capture.
        Permission can be set per-project or globally.

        Args:
            project_id: Project database ID (integer) or project slug (string).
            message: Optional description of what/why to capture.
        """
        result = _make_request(
            "POST",
            "/console/api/on-site/capture/",
            data={"project_id": project_id, "message": message},
        )

        if not result.get("success"):
            return _json(result)

        request_id = result.get("request_id")
        if not request_id:
            return _json({"success": False, "error": "No request_id returned"})

        # Poll for completion (max 30s)
        max_wait = 30
        poll_interval = 1
        elapsed = 0

        while elapsed < max_wait:
            time.sleep(poll_interval)
            elapsed += poll_interval

            status_result = _make_request(
                "GET",
                f"/console/api/on-site/capture/{request_id}/status/",
            )

            status = status_result.get("status")
            if status == "complete":
                return _json(
                    {
                        "success": True,
                        "filepath": status_result.get("filepath"),
                        "description": status_result.get("description"),
                        "request_id": request_id,
                    }
                )
            elif status == "denied":
                return _json(
                    {
                        "success": False,
                        "error": "Capture denied by user",
                        "request_id": request_id,
                    }
                )
            elif status == "expired":
                return _json(
                    {
                        "success": False,
                        "error": "Capture request expired",
                        "request_id": request_id,
                    }
                )

        return _json(
            {
                "success": False,
                "error": "Capture timed out (30s). User may not have the page open.",
                "request_id": request_id,
            }
        )

    @mcp.tool()
    async def onsite_check_permission(
        project_id: str,
    ) -> str:
        """Use when the user asks whether capture/automation is permitted for a SciTeX Cloud project, or mentions the allow/deny/ask permission state; drop-in replacement for ad-hoc workspace-introspection scripts against the live SciTeX Cloud workspace.

        Returns the current permission state: 'allow', 'deny', or 'ask'.
        """
        result = _make_request(
            "GET",
            "/console/api/on-site/permission/check/",
            data={"project_id": project_id},
        )
        return _json(result)

    @mcp.tool()
    async def onsite_get_context(page: str = "") -> str:
        """Use when the user asks for the current SciTeX Cloud workspace context — username, active page, installed skills, available UI actions; drop-in replacement for hand-rolled Playwright introspection scripts pointed at the live SciTeX Cloud workspace.

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
    async def onsite_eval_js(code: str, timeout: int = 10) -> str:
        """Use when the user asks to run/evaluate/execute JavaScript inside the SciTeX Cloud workspace or app iframe; drop-in replacement for hand-rolled Playwright page.evaluate() scripts pointed at the live SciTeX Cloud workspace.

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
    async def onsite_get_dev_app_url(project_id: str) -> str:
        """Use when the user asks for the workspace URL/path of a dev-installed SciTeX Cloud app (needed before navigate/capture); drop-in replacement for hand-rolled workspace-introspection scripts against the live SciTeX Cloud workspace.

        Given a project slug, returns the URL path for the dev app page.
        Use this before onsite_ui_action navigate or onsite_capture_page.

        Args:
            project_id: Project slug (e.g. "pomodoro-app").
        """
        result = _make_request(
            "GET",
            "/apps/store/api/dev/url/",
            data={"project_id": project_id},
        )
        return _json(result)

    @mcp.tool()
    async def onsite_ui_action(steps: list, delay_ms: int = 900) -> str:
        """Use when the user asks to click/fill/navigate/scroll/highlight or otherwise drive the SciTeX Cloud workspace UI; drop-in replacement for hand-rolled Playwright click/fill/goto scripts pointed at the live SciTeX Cloud workspace.

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
