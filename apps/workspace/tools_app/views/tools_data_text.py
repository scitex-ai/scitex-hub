#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Research Tools data - Text domain tools.

``name`` : noun-form tool label shown on the tools page.
``slug`` : kebab-case anchor id / hash-URL deep-link target, e.g.
           /apps/tools/#json-formatter. Keep stable across renames.
"""

from __future__ import annotations

# Text tools
TEXT_TOOLS = [
    {
        "name": "DOCX to LaTeX Converter",
        "slug": "docx-to-latex-converter",
        "description": "Convert Microsoft Word documents to LaTeX format with figure extraction.",
        "use_case": "Convert Word manuscript to LaTeX for journal submission",
        "bookmarklet_url": "/apps/tools/convert-docx-to-latex/",
        "icon": "📝",
    },
    {
        "name": "JSON Formatter",
        "slug": "json-formatter",
        "description": "Format, validate, and beautify JSON data with syntax highlighting.",
        "use_case": "Validate plot specifications and configuration files",
        "bookmarklet_url": "/apps/tools/format-json/",
        "icon": "{ }",
    },
    {
        "name": "Text Diff Checker",
        "slug": "text-diff-checker",
        "description": "Compare two text blocks side-by-side with highlighted differences.",
        "use_case": "Compare dataset versions or track changes in results",
        "bookmarklet_url": "/apps/tools/diff-texts/",
        "icon": "🔄",
    },
    {
        "name": "Markdown Renderer",
        "slug": "markdown-renderer",
        "description": "Real-time Markdown preview with syntax highlighting and table support.",
        "use_case": "Format README files and documentation for data repositories",
        "bookmarklet_url": "/apps/tools/render-md/",
        "icon": "📝",
    },
    {
        "name": "Mermaid Renderer",
        "slug": "mermaid-renderer",
        "description": "Create flowcharts, sequence diagrams, and concept diagrams from text syntax.",
        "use_case": "Design experimental workflow diagrams for Methods section",
        "bookmarklet_url": "/apps/tools/render-mmd/",
        "icon": "🧜‍♀️",
    },
]


# EOF
