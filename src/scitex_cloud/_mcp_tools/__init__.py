#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: src/scitex_cloud/_mcp_tools/__init__.py
"""FastMCP tool registration for scitex-cloud server."""

from __future__ import annotations

from .api import register_api_tools
from .app import register_app_tools
from .gitea import register_gitea_tools
from .on_site import register_on_site_tools

__all__ = ["register_all_tools"]


def register_all_tools(mcp) -> None:
    """Register all module tools with the FastMCP server."""
    register_gitea_tools(mcp)
    register_api_tools(mcp)
    register_on_site_tools(mcp)
    register_app_tools(mcp)


# EOF
