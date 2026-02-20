#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MCP tools data for API docs - assembled from category modules."""

from ._introspect import INTROSPECT_TOOLS, PROJECT_TOOLS
from ._misc import AUDIO_UI_TOOLS, CLEW_TOOLS, DEV_TOOLS, TEMPLATE_TOOLS, USAGE_TOOLS
from ._plt import DIAGRAM_TOOLS, PLT_TOOLS
from ._scholar import SCHOLAR_TOOLS
from ._stats import STATS_TOOLS

MCP_TOOLS = [
    PLT_TOOLS,
    DIAGRAM_TOOLS,
    STATS_TOOLS,
    SCHOLAR_TOOLS,
    INTROSPECT_TOOLS,
    PROJECT_TOOLS,
    CLEW_TOOLS,
    TEMPLATE_TOOLS,
    DEV_TOOLS,
    AUDIO_UI_TOOLS,
    USAGE_TOOLS,
]

__all__ = ["MCP_TOOLS"]

# EOF
