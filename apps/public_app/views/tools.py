#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Research Tools views - Re-export wrapper.

This module re-exports all tool views and data for backward compatibility.
Actual implementation is in tools_views.py and tools_data.py.
"""

from __future__ import annotations

from .tools_data import (
    DEVELOPER_TOOLS,
    DOCUMENT_TOOLS,
    IMAGE_TOOLS,
    PDF_TOOLS,
    RENDERING_TOOLS,
    RESEARCH_TOOLS,
    TEXT_TOOLS,
    VIDEO_TOOLS,
    get_tool_domains,
)
from .tools_views import (
    tool_asta_citation_scraper,
    tool_color_picker,
    tool_docx2tex,
    tool_element_inspector,
    tool_image_concatenator,
    tool_image_converter,
    tool_image_resizer,
    tool_image_viewer,
    tool_images_to_gif,
    tool_images_to_pdf,
    tool_json_formatter,
    tool_markdown_renderer,
    tool_mermaid_renderer,
    tool_pdf_compressor,
    tool_pdf_merger,
    tool_pdf_splitter,
    tool_pdf_to_images,
    tool_plot_backend_test,
    tool_plot_viewer,
    tool_qr_code_generator,
    tool_repo_concatenator,
    tool_statistics_calculator,
    tool_text_diff_checker,
    tool_video_editor,
    tools,
)

__all__ = [
    # Main tools page
    "tools",
    # Tool data
    "get_tool_domains",
    "TEXT_TOOLS",
    "IMAGE_TOOLS",
    "PDF_TOOLS",
    "VIDEO_TOOLS",
    "RENDERING_TOOLS",
    "DEVELOPER_TOOLS",
    "RESEARCH_TOOLS",
    "DOCUMENT_TOOLS",
    # Individual tool views
    "tool_asta_citation_scraper",
    "tool_color_picker",
    "tool_docx2tex",
    "tool_element_inspector",
    "tool_image_concatenator",
    "tool_image_converter",
    "tool_image_resizer",
    "tool_image_viewer",
    "tool_images_to_gif",
    "tool_images_to_pdf",
    "tool_json_formatter",
    "tool_markdown_renderer",
    "tool_mermaid_renderer",
    "tool_pdf_compressor",
    "tool_pdf_merger",
    "tool_pdf_splitter",
    "tool_pdf_to_images",
    "tool_plot_backend_test",
    "tool_plot_viewer",
    "tool_qr_code_generator",
    "tool_repo_concatenator",
    "tool_statistics_calculator",
    "tool_text_diff_checker",
    "tool_video_editor",
]


# EOF
