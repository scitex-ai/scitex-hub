#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Research Tools view functions.

Individual tool detail page views. Each renders a specific tool template.
"""

from __future__ import annotations

from django.shortcuts import render

from apps.infra.project_app.models import Project

from .tools_data import get_tool_domains

_EMBED_BASE = "tools_app/tools/tool_embed_base.html"
_GLOBAL_BASE = "global_base.html"


def _tool_context(request):
    """Common context for individual tool views (embed mode support)."""
    embed = request.GET.get("embed") == "1"
    return {
        "embed": embed,
        "base_template": _EMBED_BASE if embed else _GLOBAL_BASE,
    }


def build_tools_context(request, current_project=None):
    """Build tools-specific context for both full page and partial views."""
    domains = get_tool_domains()
    return {
        "domains": domains,
        "total_tools": sum(len(d["tools"]) for d in domains),
        "current_project": current_project,
    }


def tools(request):
    """Research tools page - bookmarklets and utilities for researchers."""
    # Get current project for file tree sidebar
    current_project = None
    if request.user.is_authenticated:
        # Try to get project from session
        project_id = request.session.get("current_project_id")
        if project_id:
            try:
                current_project = Project.objects.get(id=project_id, owner=request.user)
            except Project.DoesNotExist:
                pass

        # Fall back to most recent project if no session project
        if not current_project:
            current_project = (
                Project.objects.filter(owner=request.user)
                .order_by("-updated_at")
                .first()
            )

    context = build_tools_context(request, current_project=current_project)
    return render(request, "tools_app/tools.html", context)


# Text tools
def tool_render_md(request):
    """Markdown Renderer tool detail page."""
    return render(request, "tools_app/tools/render-md.html", _tool_context(request))


def tool_diff_texts(request):
    """Text Diff Checker tool detail page."""
    return render(request, "tools_app/tools/diff-texts.html", _tool_context(request))


def tool_format_json(request):
    """JSON Formatter tool detail page."""
    return render(request, "tools_app/tools/format-json.html", _tool_context(request))


# Image tools
def tool_view_image(request):
    """Image Viewer - Display image with dimension, DPI, and unit conversion info."""
    return render(request, "tools_app/tools/view-image.html", _tool_context(request))


def tool_resize_image(request):
    """Image Resizer tool detail page."""
    return render(request, "tools_app/tools/resize-image.html", _tool_context(request))


def tool_crop_images(request):
    """Image Cropper tool detail page."""
    return render(request, "tools_app/tools/crop-images.html", _tool_context(request))


def tool_convert_image_format(request):
    """Image Converter tool detail page."""
    return render(
        request, "tools_app/tools/convert-image-format.html", _tool_context(request)
    )


def tool_concat_images(request):
    """Image Concatenator tool detail page."""
    return render(request, "tools_app/tools/concat-images.html", _tool_context(request))


def tool_render_mmd(request):
    """Mermaid Diagram Renderer - Create diagrams from text syntax."""
    return render(request, "tools_app/tools/render-mmd.html", _tool_context(request))


def tool_convert_images_to_gif(request):
    """Images to GIF tool detail page."""
    return render(
        request, "tools_app/tools/convert-images-to-gif.html", _tool_context(request)
    )


def tool_convert_images_to_pdf(request):
    """Images to PDF tool detail page."""
    return render(
        request, "tools_app/tools/convert-images-to-pdf.html", _tool_context(request)
    )


def tool_convert_pdf_to_images(request):
    """PDF to Images tool detail page."""
    return render(
        request, "tools_app/tools/convert-pdf-to-images.html", _tool_context(request)
    )


# PDF tools
def tool_merge_pdf(request):
    """PDF Merger tool detail page."""
    return render(request, "tools_app/tools/merge-pdf.html", _tool_context(request))


def tool_compress_pdf(request):
    """PDF Compressor tool detail page."""
    return render(request, "tools_app/tools/compress-pdf.html", _tool_context(request))


def tool_split_pdf(request):
    """PDF Splitter tool detail page."""
    return render(request, "tools_app/tools/split-pdf.html", _tool_context(request))


# Audio tools
def tool_transcribe_audio(request):
    """Audio Transcription tool detail page."""
    return render(
        request, "tools_app/tools/transcribe-audio.html", _tool_context(request)
    )


# Video tools
def tool_edit_video(request):
    """Video Editor tool detail page."""
    return render(request, "tools_app/tools/edit-video.html", _tool_context(request))


# Rendering tools
def tool_view_plot(request):
    """Quick CSV Plot Viewer - renders simple CSV plots using Canvas."""
    return render(request, "tools_app/tools/view-plot.html", _tool_context(request))


def tool_test_scitex_plot(request):
    """Backend Plot Renderer Test - test matplotlib/scitex.plt backend."""
    return render(
        request, "tools_app/tools/test-scitex-plot.html", _tool_context(request)
    )


def tool_pick_color(request):
    """Color Picker tool detail page."""
    return render(request, "tools_app/tools/pick-color.html", _tool_context(request))


# Developer tools
def tool_inspect_html_element(request):
    """Element Inspector tool detail page."""
    return render(
        request, "tools_app/tools/inspect-html-element.html", _tool_context(request)
    )


def tool_concat_repo(request):
    """Repository Concatenator tool detail page."""
    return render(request, "tools_app/tools/concat-repo.html", _tool_context(request))


def tool_generate_qr(request):
    """QR Code Generator tool detail page."""
    return render(request, "tools_app/tools/generate-qr.html", _tool_context(request))


# Research tools
def tool_scrape_citations(request):
    """Asta AI Citation Scraper tool detail page."""
    return render(
        request, "tools_app/tools/scrape-citations.html", _tool_context(request)
    )


def tool_run_stats(request):
    """Statistics Calculator tool detail page."""
    return render(request, "tools_app/tools/run-stats.html", _tool_context(request))


# Document tools
def tool_convert_docx_to_latex(request):
    """DOCX to LaTeX Converter - Convert Word documents to LaTeX."""
    from scitex.msword import list_profiles

    profiles = list_profiles()
    return render(
        request,
        "tools_app/tools/convert-docx-to-latex.html",
        {**_tool_context(request), "profiles": profiles},
    )


# EOF
