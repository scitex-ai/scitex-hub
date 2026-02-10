#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Research Tools view functions.

Individual tool detail page views. Each renders a specific tool template.
"""

from __future__ import annotations

from django.shortcuts import render

from apps.project_app.models import Project

from .tools_data import get_tool_domains

_EMBED_BASE = "public_app/tools/tool_embed_base.html"
_GLOBAL_BASE = "global_base.html"


def _tool_context(request):
    """Common context for individual tool views (embed mode support)."""
    embed = request.GET.get("embed") == "1"
    return {
        "embed": embed,
        "base_template": _EMBED_BASE if embed else _GLOBAL_BASE,
    }


def tools(request):
    """Research tools page - bookmarklets and utilities for researchers."""
    domains = get_tool_domains()
    total_tools = sum(len(domain["tools"]) for domain in domains)

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

    context = {
        "domains": domains,
        "total_tools": total_tools,
        "current_project": current_project,
    }
    return render(request, "public_app/pages/tools.html", context)


# Text tools
def tool_markdown_renderer(request):
    """Markdown Renderer tool detail page."""
    return render(
        request, "public_app/tools/markdown-renderer.html", _tool_context(request)
    )


def tool_text_diff_checker(request):
    """Text Diff Checker tool detail page."""
    return render(
        request, "public_app/tools/text-diff-checker.html", _tool_context(request)
    )


def tool_json_formatter(request):
    """JSON Formatter tool detail page."""
    return render(
        request, "public_app/tools/json-formatter.html", _tool_context(request)
    )


# Image tools
def tool_image_viewer(request):
    """Image Viewer - Display image with dimension, DPI, and unit conversion info."""
    return render(request, "public_app/tools/image-viewer.html", _tool_context(request))


def tool_image_resizer(request):
    """Image Resizer tool detail page."""
    return render(
        request, "public_app/tools/image-resizer.html", _tool_context(request)
    )


def tool_image_cropper(request):
    """Image Cropper tool detail page."""
    return render(
        request, "public_app/tools/image-cropper.html", _tool_context(request)
    )


def tool_image_converter(request):
    """Image Converter tool detail page."""
    return render(
        request, "public_app/tools/image-converter.html", _tool_context(request)
    )


def tool_image_concatenator(request):
    """Image Concatenator tool detail page."""
    return render(
        request, "public_app/tools/image-concatenator.html", _tool_context(request)
    )


def tool_mermaid_renderer(request):
    """Mermaid Diagram Renderer - Create diagrams from text syntax."""
    return render(
        request, "public_app/tools/mermaid-renderer.html", _tool_context(request)
    )


def tool_images_to_gif(request):
    """Images to GIF tool detail page."""
    return render(
        request, "public_app/tools/images-to-gif.html", _tool_context(request)
    )


def tool_images_to_pdf(request):
    """Images to PDF tool detail page."""
    return render(
        request, "public_app/tools/images-to-pdf.html", _tool_context(request)
    )


def tool_pdf_to_images(request):
    """PDF to Images tool detail page."""
    return render(
        request, "public_app/tools/pdf-to-images.html", _tool_context(request)
    )


# PDF tools
def tool_pdf_merger(request):
    """PDF Merger tool detail page."""
    return render(request, "public_app/tools/pdf-merger.html", _tool_context(request))


def tool_pdf_compressor(request):
    """PDF Compressor tool detail page."""
    return render(
        request, "public_app/tools/pdf-compressor.html", _tool_context(request)
    )


def tool_pdf_splitter(request):
    """PDF Splitter tool detail page."""
    return render(request, "public_app/tools/pdf-splitter.html", _tool_context(request))


# Video tools
def tool_video_editor(request):
    """Video Editor tool detail page."""
    return render(request, "public_app/tools/video-editor.html", _tool_context(request))


# Rendering tools
def tool_plot_viewer(request):
    """Quick CSV Plot Viewer - renders simple CSV plots using Canvas."""
    return render(request, "public_app/tools/plot-viewer.html", _tool_context(request))


def tool_plot_backend_test(request):
    """Backend Plot Renderer Test - test matplotlib/scitex.plt backend."""
    return render(
        request, "public_app/tools/plot-backend-test.html", _tool_context(request)
    )


def tool_color_picker(request):
    """Color Picker tool detail page."""
    return render(request, "public_app/tools/color-picker.html", _tool_context(request))


# Developer tools
def tool_element_inspector(request):
    """Element Inspector tool detail page."""
    return render(
        request, "public_app/tools/element-inspector.html", _tool_context(request)
    )


def tool_repo_concatenator(request):
    """Repository Concatenator tool detail page."""
    return render(
        request, "public_app/tools/repo-concatenator.html", _tool_context(request)
    )


def tool_qr_code_generator(request):
    """QR Code Generator tool detail page."""
    return render(
        request, "public_app/tools/qr-code-generator.html", _tool_context(request)
    )


# Research tools
def tool_asta_citation_scraper(request):
    """Asta AI Citation Scraper tool detail page."""
    return render(
        request, "public_app/tools/asta-citation-scraper.html", _tool_context(request)
    )


def tool_statistics_calculator(request):
    """Statistics Calculator tool detail page."""
    return render(
        request, "public_app/tools/statistics-calculator.html", _tool_context(request)
    )


# Document tools
def tool_docx2tex(request):
    """DOCX to LaTeX Converter - Convert Word documents to LaTeX."""
    from scitex.msword import list_profiles

    profiles = list_profiles()
    return render(
        request,
        "public_app/tools/docx2tex.html",
        {**_tool_context(request), "profiles": profiles},
    )


# EOF
