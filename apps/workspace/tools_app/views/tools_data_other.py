#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Research Tools data - Video, Rendering, Developer, Research, Document domains.

``name`` : noun-form tool label. ``slug`` : kebab-case hash-URL anchor id.
"""

from __future__ import annotations

# Video tools
VIDEO_TOOLS = [
    {
        "name": "GIF Maker",
        "slug": "gif-maker",
        "description": "Convert image sequences into animated GIF with customizable duration.",
        "use_case": "Create supplementary animations showing temporal changes",
        "bookmarklet_url": "/apps/tools/convert-images-to-gif/",
        "icon": "🎬",
    },
    {
        "name": "Video Editor",
        "slug": "video-editor",
        "description": "Trim videos by time window with browser-based processing.",
        "use_case": "Edit supplementary videos for journal submission",
        "bookmarklet_url": "/apps/tools/edit-video/",
        "icon": "🎬",
    },
]

# Rendering tools
RENDERING_TOOLS = [
    {
        "name": "Color Picker",
        "slug": "color-picker",
        "description": "Advanced color picker with format conversion and palette generation.",
        "use_case": "Design consistent color schemes for figure panels",
        "bookmarklet_url": "/apps/tools/pick-color/",
        "icon": "🎨",
    },
    {
        "name": "CSV Plot Viewer",
        "slug": "csv-plot-viewer",
        "description": "Interactive CSV plot viewer with Nature journal standards.",
        "use_case": "Quick data visualization during analysis",
        "bookmarklet_url": "/apps/tools/view-plot/",
        "icon": "📊",
    },
]

# Developer tools
DEVELOPER_TOOLS = [
    {
        "name": "Repository Concatenator",
        "slug": "repository-concatenator",
        "description": "Concatenate repository files into AI-ready format for code review.",
        "use_case": "Prepare analysis scripts for AI code review",
        "bookmarklet_url": "/apps/tools/concat-repo/",
        "icon": "📦",
    },
    {
        "name": "QR Code Generator",
        "slug": "qr-code-generator",
        "description": "Generate QR codes for URLs, DOIs, posters, and presentations.",
        "use_case": "Add QR codes to conference posters linking to papers",
        "bookmarklet_url": "/apps/tools/generate-qr/",
        "icon": "📱",
    },
    {
        "name": "Element Inspector",
        "slug": "element-inspector",
        "description": "Visual debugging tool with AI-ready output format.",
        "use_case": "Debug web interface issues in research platforms",
        "bookmarklet_url": "/apps/tools/inspect-html-element/",
        "icon": "🔍",
    },
    {
        "name": "SciTeX Plot Tester",
        "slug": "scitex-plot-tester",
        "description": "Test matplotlib/scitex.plt backend with JSON specifications.",
        "use_case": "Design figures with precise journal specifications",
        "bookmarklet_url": "/apps/tools/test-scitex-plot/",
        "icon": "🧪",
    },
]

# Research tools
RESEARCH_TOOLS = [
    {
        "name": "Statistics Calculator",
        "slug": "statistics-calculator",
        "description": "30+ statistical tests with effect sizes, post-hoc comparisons, and APA formatting.",
        "use_case": "Verify experimental results before plotting",
        "bookmarklet_url": "/apps/tools/run-stats/",
        "icon": "📈",
    },
    {
        "name": "Citation Scraper",
        "slug": "citation-scraper",
        "description": "Automatically collect all BibTeX citations from Asta AI search results.",
        "use_case": "Build bibliography from AI literature searches",
        "bookmarklet_url": "/apps/tools/scrape-citations/",
        "icon": "📚",
    },
]


# EOF
