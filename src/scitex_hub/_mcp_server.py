#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: src/scitex_hub/mcp_server.py
"""
SciTeX Hub MCP Server - Git and Cloud API Operations.

Provides MCP tools for:
- Gitea operations (via tea CLI wrapper)
- Django API operations (scholar, writer, project)

Usage:
    scitex-hub serve                      # stdio (Claude Desktop)
    scitex-hub serve -t sse --port 8086   # SSE (remote)
    scitex-hub serve -t http --port 8086  # HTTP (streamable)
"""

from __future__ import annotations

import json

from scitex_dev import try_import_optional

FastMCP = try_import_optional("fastmcp", "FastMCP", extra="mcp", pkg="scitex-hub")
FASTMCP_AVAILABLE = FastMCP is not None

__all__ = ["mcp", "run_server", "main", "FASTMCP_AVAILABLE"]

if FASTMCP_AVAILABLE:
    mcp = FastMCP(
        name="scitex-hub",
        instructions="""\
SciTeX Hub: Git and Cloud API Operations (https://scitex.ai)

## Gitea Tools (Local Git Operations):
- cloud_login: Login to SciTeX Hub (Gitea)
- cloud_clone: Clone a repository
- cloud_create: Create a new repository
- cloud_list: List repositories
- cloud_search: Search for repositories
- cloud_delete: Delete a repository
- cloud_fork: Fork a repository
- cloud_pr_create: Create a pull request
- cloud_pr_list: List pull requests
- cloud_issue_create: Create an issue
- cloud_issue_list: List issues
- cloud_push: Push local changes to workspace
- cloud_pull: Pull workspace changes to local
- cloud_status: Show repository status

## Cloud API Tools (Remote Operations):
- api_scholar_search: Search papers via cloud API
- api_crossref_search: Search CrossRef database
- api_writer_compile: Compile LaTeX manuscript
- api_writer_list_sections: List manuscript sections
- api_project_list_files: List project files
- api_project_commit: Commit changes to project
- api_enrich_bibtex: Enrich BibTeX with metadata

## App Management Tools:
- app_get_current: Get currently active app
- app_switch_to: Switch active app
- app_list_all: List all available apps
- app_get_info: Get app details from manifest
- app_check_deps: Check app dependencies
- app_get_prefs: Get user app preferences
- app_set_prefs: Set user app preferences

## Configuration:
- SCITEX_CLOUD_API_KEY: API key for authenticated endpoints
- SCITEX_CLOUD_URL: Cloud server URL (default: https://scitex.cloud)
""",
    )
else:
    mcp = None


def _json(data: dict) -> str:
    return json.dumps(data, indent=2, default=str)


# Register tools from each module
if FASTMCP_AVAILABLE:
    from scitex_hub._mcp_tools import register_all_tools

    register_all_tools(mcp)


def run_server(transport: str = "stdio", host: str = "0.0.0.0", port: int = 8086):
    """Run the MCP server with transport selection."""
    if not FASTMCP_AVAILABLE:
        import sys

        print("=" * 60)
        print("Requires 'fastmcp' package: pip install fastmcp")
        print("=" * 60)
        sys.exit(1)

    if transport == "stdio":
        mcp.run(transport="stdio")
    elif transport == "sse":
        print(f"Starting scitex-hub MCP (SSE) on {host}:{port}")
        print(f"Remote: ssh -R {port}:localhost:{port} remote-host")
        mcp.run(transport="sse", host=host, port=port)
    elif transport == "http":
        print(f"Starting scitex-hub MCP (HTTP) on {host}:{port}")
        mcp.run(transport="streamable-http", host=host, port=port)
    else:
        raise ValueError(f"Unknown transport: {transport}")


def main():
    """Entry point for scitex-hub-mcp command."""
    run_server(transport="stdio")


if __name__ == "__main__":
    main()

# EOF
