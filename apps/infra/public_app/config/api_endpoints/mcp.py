#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MCP (Model Context Protocol) endpoint definitions."""

MCP_CATEGORY = {
    "name": "MCP Server",
    "description": (
        "SciTeX Model Context Protocol server — connect Claude Desktop, Claude Code, "
        "or any MCP-compatible AI client. Requires a Bearer API key with 'mcp' or "
        "full-access ('*') scope."
    ),
    "base_path": "/mcp",
    "auth_required": True,
    "endpoints": [
        {
            "method": "POST",
            "path": "",
            "name": "MCP Streamable-HTTP",
            "description": (
                "Streamable-HTTP transport for the FastMCP server. "
                "Exposes all SciTeX tools (plt, stats, scholar, io, diagram, …). "
                "Add Authorization: Bearer <key> header. "
                "Configure your MCP client to connect to https://scitex.ai/mcp."
            ),
            "params": [],
            "response_fields": [],
            "response_example": {},
        },
    ],
}
