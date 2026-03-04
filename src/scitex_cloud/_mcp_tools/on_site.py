#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: src/scitex_cloud/_mcp_tools/on_site.py
"""On-site agent tools for workspace interaction (page capture, etc.)."""

from __future__ import annotations

import json
import os
import time
from typing import Optional


def _json(data: dict) -> str:
    return json.dumps(data, indent=2, default=str)


def _get_config() -> dict:
    """Get API configuration from environment."""
    return {
        "api_key": os.environ.get("SCITEX_CLOUD_API_KEY"),
        "base_url": os.environ.get("SCITEX_CLOUD_URL", "https://scitex.cloud"),
    }


def _make_request(
    method: str,
    endpoint: str,
    data: Optional[dict] = None,
    auth_required: bool = True,
) -> dict:
    """Make HTTP request to SciTeX Cloud API."""
    import requests

    config = _get_config()
    url = f"{config['base_url']}{endpoint}"

    headers = {
        "Content-Type": "application/json",
        "X-Requested-With": "XMLHttpRequest",
    }
    if auth_required:
        if not config["api_key"]:
            return {
                "success": False,
                "error": "API key required",
                "hint": "Set SCITEX_CLOUD_API_KEY environment variable",
            }
        headers["Authorization"] = f"Bearer {config['api_key']}"

    try:
        if method.upper() == "GET":
            response = requests.get(url, headers=headers, params=data, timeout=60)
        elif method.upper() == "POST":
            response = requests.post(url, headers=headers, json=data, timeout=60)
        else:
            return {"success": False, "error": f"Unknown method: {method}"}

        if response.status_code >= 400:
            return {
                "success": False,
                "error": f"HTTP {response.status_code}",
                "detail": response.text[:500],
            }

        try:
            return response.json()
        except json.JSONDecodeError:
            return {"success": True, "content": response.text}

    except requests.Timeout:
        return {"success": False, "error": "Request timed out"}
    except requests.ConnectionError:
        return {"success": False, "error": "Connection failed"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def register_on_site_tools(mcp) -> None:
    """Register on-site agent interaction tools with FastMCP server."""

    @mcp.tool()
    async def on_site_capture_page(
        project_id: int,
        message: str = "",
    ) -> str:
        """[on_site] Capture screenshot of current workspace page.

        Sends a capture request to the user's browser. The browser captures
        the page and saves the screenshot to scitex/downloads/.
        Returns the filepath of the saved screenshot.

        On first use, the user sees a permission modal to allow/deny capture.
        Permission can be set per-project or globally.

        Args:
            project_id: The project ID to associate the capture with.
            message: Optional description of what/why to capture.
        """
        # Create capture request
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
    async def on_site_check_permission(
        project_id: int,
    ) -> str:
        """[on_site] Check if page capture is allowed for a project.

        Returns the current permission state: 'allow', 'deny', or 'ask'.
        """
        result = _make_request(
            "GET",
            "/console/api/on-site/permission/check/",
            data={"project_id": project_id},
        )
        return _json(result)


# EOF
