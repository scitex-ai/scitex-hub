#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Static data for information pages.

Contains data definitions for video catalog.
Re-exports keyboard shortcuts from pages_shortcuts module.
"""

from .pages_shortcuts import KEYBOARD_SHORTCUTS_DATA

# Re-export for backward compatibility
__all__ = ["VIDEO_CATALOG", "KEYBOARD_SHORTCUTS_DATA", "OG_BASE_URL"]


# Base URL for OG images (used for absolute URLs in meta tags)
OG_BASE_URL = "https://scitex.ai"

# Video catalog for demo pages
VIDEO_CATALOG = {
    # Local MCP demos
    "figrecipe": {
        "title": "Graphing by AI Agent (figrecipe v0.14.0)",
        "url": "/media/videos/figrecipe-v0.14.0-demo.mp4",
        "thumbnail": "/media/videos/figrecipe-v0.14.0-demo-thumbnail.png",
        "date": "2026-01-22",
        "description": (
            "scitex MCP enables AI agents to create publication-ready scientific "
            "figures. Reproducible recipes for automated plot generation."
        ),
    },
    "crossref-local": {
        "title": "Literature Search by AI Agent (crossref-local v0.3.1)",
        "url": "/media/videos/crossref-local-v0.3.1-demo.mp4",
        "thumbnail": "/media/videos/crossref-local-v0.3.1-demo-thumbnail.png",
        "date": "2026-01-22",
        "description": (
            "scitex MCP enables AI agents to search 167M+ academic works via local "
            "database. No hallucinated citations — real literature data for reliable "
            "research."
        ),
    },
    "scitex-writer": {
        "title": "Manuscript Writing by AI Agent (scitex-writer v2.2.0)",
        "url": "/media/videos/scitex-writer-v2.2.0-demo.mp4",
        "thumbnail": "/media/videos/scitex-writer-v2.2.0-demo-thumbnail.png",
        "date": "2026-01-22",
        "description": (
            "scitex MCP enables AI agents to write scientific manuscripts. Automated "
            "literature integration, LaTeX compilation, and revision tracking."
        ),
    },
    "scitex-automated-research": {
        "title": "Automated Research by AI Agent (scitex v2.10)",
        "url": "/media/videos/scitex-automated-research-demo.mp4",
        "thumbnail": "/media/videos/scitex-automated-research-demo-thumbnail.png",
        "date": "2026-01-22",
        "description": (
            "scitex MCP enables AI agents to conduct full research workflows: "
            "literature search, experiment, analysis, figure generation, manuscript "
            "writing, and revision."
        ),
    },
    # Local Python demos (use default OG image - no specific thumbnails)
    "scholar-module": {
        "title": "scitex.scholar Demo",
        "url": "/static/public_app/videos/landing/scholar-demo.mp4",
        "thumbnail": None,  # Uses default OG image
        "date": "2025-11-06",
        "description": (
            "Literature discovery & enrichment. Search 167M+ academic works via local "
            "database. Automatic PDF download with institutional credentials."
        ),
    },
    "writer-module": {
        "title": "scitex.writer Demo",
        "url": "/static/public_app/videos/landing/writer-demo.mp4",
        "thumbnail": None,  # Uses default OG image
        "date": "2025-11-06",
        "description": (
            "LaTeX manuscript writing with automated compilation. Integrates with "
            "BibTeX for citation management."
        ),
    },
    "console-module": {
        "title": "scitex.{session,plt,io} Demo",
        "url": "/static/public_app/videos/landing/console-demo.mp4",
        "thumbnail": None,  # Uses default OG image
        "date": "2025-11-06",
        "description": (
            "Reproducible experiment tracking with @stx.session decorator. "
            "Publication-ready figures and universal file I/O."
        ),
    },
    "visualizer-module": {
        "title": "scitex.plt Demo",
        "url": "/static/public_app/videos/landing/visualizer-demo.mp4",
        "thumbnail": None,  # Uses default OG image
        "date": "2025-11-06",
        "description": (
            "Publication-ready scientific figures with reproducible recipes. "
            "Auto-exports data CSV alongside plots."
        ),
    },
    # Cloud demos
    "scitex-hub-v0.11.5": {
        "title": "SciTeX Cloud v0.11.5 Demo",
        "url": "/media/videos/scitex-hub-v0.11.5-demo.mp4",
        "thumbnail": "/media/videos/scitex-hub-v0.11.5-demo-thumbnail.png",
        "date": "2026-03-02",
        "description": (
            "SciTeX Cloud v0.11.5 — AI panel redesign with 2-mode layout "
            "(Chat/Console), multi-terminal tabs, flat tab styling, and "
            "hub project about section."
        ),
    },
    "scitex-hub": {
        "title": "SciTeX Cloud v0.9.3 Demo",
        "url": "/media/videos/scitex-hub-v0.9.3-demo.mp4",
        "thumbnail": "/media/videos/scitex-hub-v0.9.3-demo-thumbnail.png",
        "date": "2026-02-16",
        "description": (
            "SciTeX Cloud — self-hosted research platform. Scholar, Writer, "
            "Console, and Visualizer modules in a unified web interface."
        ),
    },
}


# EOF
