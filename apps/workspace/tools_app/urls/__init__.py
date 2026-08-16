#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tools App URL Configuration

Research tool page views:
- Tool index/hub
- Image tools (concat, convert, resize, crop, view)
- PDF tools (merge, split, compress, convert)
- Text/markup tools (render-md, render-mmd, diff-texts, format-json)
- Video tools (edit-video, convert-to-gif)
- Citation and QR tools
- Stats runner
- Plot viewer
- Repo concat
- HTML inspector
- DOCX to LaTeX converter
"""

from django.urls import path

from apps.workspace.tools_app import views

app_name = "tools_app"

urlpatterns = [
    # Research Tools index
    path("tools/", views.tools, name="tools"),
    # HTML inspection
    path(
        "tools/inspect-html-element/",
        views.tool_inspect_html_element,
        name="tool_inspect_html_element",
    ),
    # Citation scraping
    path(
        "tools/scrape-citations/",
        views.tool_scrape_citations,
        name="tool_scrape_citations",
    ),
    # Image tools
    path(
        "tools/concat-images/",
        views.tool_concat_images,
        name="tool_concat_images",
    ),
    path(
        "tools/generate-qr/",
        views.tool_generate_qr,
        name="tool_generate_qr",
    ),
    path(
        "tools/pick-color/",
        views.tool_pick_color,
        name="tool_pick_color",
    ),
    path(
        "tools/view-image/",
        views.tool_view_image,
        name="tool_view_image",
    ),
    path(
        "tools/resize-image/",
        views.tool_resize_image,
        name="tool_resize_image",
    ),
    path(
        "tools/crop-images/",
        views.tool_crop_images,
        name="tool_crop_images",
    ),
    path(
        "tools/convert-images-to-gif/",
        views.tool_convert_images_to_gif,
        name="tool_convert_images_to_gif",
    ),
    path(
        "tools/convert-image-format/",
        views.tool_convert_image_format,
        name="tool_convert_image_format",
    ),
    # PDF tools
    path(
        "tools/merge-pdf/",
        views.tool_merge_pdf,
        name="tool_merge_pdf",
    ),
    path(
        "tools/split-pdf/",
        views.tool_split_pdf,
        name="tool_split_pdf",
    ),
    path(
        "tools/compress-pdf/",
        views.tool_compress_pdf,
        name="tool_compress_pdf",
    ),
    path(
        "tools/convert-images-to-pdf/",
        views.tool_convert_images_to_pdf,
        name="tool_convert_images_to_pdf",
    ),
    path(
        "tools/convert-pdf-to-images/",
        views.tool_convert_pdf_to_images,
        name="tool_convert_pdf_to_images",
    ),
    # Text/markup tools
    path(
        "tools/render-md/",
        views.tool_render_md,
        name="tool_render_md",
    ),
    path(
        "tools/diff-texts/",
        views.tool_diff_texts,
        name="tool_diff_texts",
    ),
    path(
        "tools/format-json/",
        views.tool_format_json,
        name="tool_format_json",
    ),
    path(
        "tools/render-mmd/",
        views.tool_render_mmd,
        name="tool_render_mmd",
    ),
    # Audio tools
    path(
        "tools/transcribe-audio/",
        views.tool_transcribe_audio,
        name="tool_transcribe_audio",
    ),
    # Video tools
    path(
        "tools/edit-video/",
        views.tool_edit_video,
        name="tool_edit_video",
    ),
    # Plot viewer
    path(
        "tools/view-plot/",
        views.tool_view_plot,
        name="tool_view_plot",
    ),
    path(
        "tools/test-scitex-plot/",
        views.tool_test_scitex_plot,
        name="tool_test_scitex_plot",
    ),
    # Stats runner
    path(
        "tools/run-stats/",
        views.tool_run_stats,
        name="tool_run_stats",
    ),
    # Repository tools
    path(
        "tools/concat-repo/",
        views.tool_concat_repo,
        name="tool_concat_repo",
    ),
    # Document conversion
    path(
        "tools/convert-docx-to-latex/",
        views.tool_convert_docx_to_latex,
        name="tool_convert_docx_to_latex",
    ),
]

# EOF
