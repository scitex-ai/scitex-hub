#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Research Tools data definitions.

Static tool configurations organized by domain: Text, Image, PDF, Video, Rendering, Developer, Research
Re-exports all tool definitions from domain-specific modules.
"""

from __future__ import annotations

from .tools_data_image import IMAGE_TOOLS
from .tools_data_other import (
    DEVELOPER_TOOLS,
    RENDERING_TOOLS,
    RESEARCH_TOOLS,
    VIDEO_TOOLS,
)
from .tools_data_pdf import PDF_TOOLS
from .tools_data_text import TEXT_TOOLS

__all__ = [
    "TEXT_TOOLS",
    "IMAGE_TOOLS",
    "PDF_TOOLS",
    "VIDEO_TOOLS",
    "RENDERING_TOOLS",
    "DEVELOPER_TOOLS",
    "RESEARCH_TOOLS",
    "get_tool_domains",
]


def get_tool_domains():
    """Get all tool domains with their configurations."""
    return [
        {
            "name": "Text",
            "slug": "text",
            "icon": "📝",
            "description": "Format, compare, and process text content",
            "tools": TEXT_TOOLS,
        },
        {
            "name": "Image",
            "slug": "image",
            "icon": "🖼️",
            "description": "Manipulate and convert images for publications",
            "tools": IMAGE_TOOLS,
        },
        {
            "name": "PDF",
            "slug": "pdf",
            "icon": "📄",
            "description": "Manage and process PDF documents",
            "tools": PDF_TOOLS,
        },
        {
            "name": "Video",
            "slug": "video",
            "icon": "🎬",
            "description": "Video and animation processing",
            "tools": VIDEO_TOOLS,
        },
        {
            "name": "Rendering",
            "slug": "rendering",
            "icon": "📈",
            "description": "Create publication-quality plots and diagrams",
            "tools": RENDERING_TOOLS,
        },
        {
            "name": "Developer",
            "slug": "development",
            "icon": "💻",
            "description": "Web development and debugging utilities",
            "tools": DEVELOPER_TOOLS,
        },
        {
            "name": "Research",
            "slug": "research",
            "icon": "🔬",
            "description": "Literature management and citation tools",
            "tools": RESEARCH_TOOLS,
        },
    ]


# EOF
