#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Research Tools views - Re-export wrapper.

This module re-exports all tool views and data for backward compatibility.
Actual implementation is in tools_views.py and tools_data.py.
"""

from __future__ import annotations

from .tools_data import (
    DEVELOPER_TOOLS,
    IMAGE_TOOLS,
    PDF_TOOLS,
    RENDERING_TOOLS,
    RESEARCH_TOOLS,
    TEXT_TOOLS,
    VIDEO_TOOLS,
    get_tool_domains,
)
from .tools_views import (
    build_tools_context,
    tool_compress_pdf,
    tool_concat_images,
    tool_concat_repo,
    tool_convert_docx_to_latex,
    tool_convert_image_format,
    tool_convert_images_to_gif,
    tool_convert_images_to_pdf,
    tool_convert_pdf_to_images,
    tool_crop_images,
    tool_diff_texts,
    tool_edit_video,
    tool_format_json,
    tool_generate_qr,
    tool_inspect_html_element,
    tool_merge_pdf,
    tool_pick_color,
    tool_render_md,
    tool_render_mmd,
    tool_resize_image,
    tool_run_stats,
    tool_scrape_citations,
    tool_split_pdf,
    tool_test_scitex_plot,
    tool_view_image,
    tool_view_plot,
    tools,
)

__all__ = [
    # Main tools page
    "tools",
    "build_tools_context",
    # Tool data
    "get_tool_domains",
    "TEXT_TOOLS",
    "IMAGE_TOOLS",
    "PDF_TOOLS",
    "VIDEO_TOOLS",
    "RENDERING_TOOLS",
    "DEVELOPER_TOOLS",
    "RESEARCH_TOOLS",
    # Individual tool views
    "tool_compress_pdf",
    "tool_concat_images",
    "tool_concat_repo",
    "tool_convert_docx_to_latex",
    "tool_convert_image_format",
    "tool_convert_images_to_gif",
    "tool_convert_images_to_pdf",
    "tool_convert_pdf_to_images",
    "tool_crop_images",
    "tool_diff_texts",
    "tool_edit_video",
    "tool_format_json",
    "tool_generate_qr",
    "tool_inspect_html_element",
    "tool_merge_pdf",
    "tool_pick_color",
    "tool_render_md",
    "tool_render_mmd",
    "tool_resize_image",
    "tool_run_stats",
    "tool_scrape_citations",
    "tool_split_pdf",
    "tool_test_scitex_plot",
    "tool_view_image",
    "tool_view_plot",
]


# EOF
