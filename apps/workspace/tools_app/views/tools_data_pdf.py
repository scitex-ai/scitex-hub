#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Research Tools data - PDF domain tools."""

from __future__ import annotations

# PDF tools (alphabetical by name, shares some with Image)
PDF_TOOLS = [
    {
        "name": "Compress PDF",
        "description": "Reduce PDF file size while maintaining quality for email and uploads.",
        "use_case": "Compress submission files under journal size limits",
        "bookmarklet_url": "/apps/tools/compress-pdf/",
        "icon": "🗜️",
    },
    {
        "name": "Convert Images to PDF",
        "description": "Convert multiple images into a single PDF with custom page orientation.",
        "use_case": "Create supplementary figures PDF from multiple images",
        "bookmarklet_url": "/apps/tools/convert-images-to-pdf/",
        "icon": "📄",
    },
    {
        "name": "Convert PDF to Images",
        "description": "Extract all pages from PDF as PNG or JPG images with adjustable DPI.",
        "use_case": "Convert PDF figures to images for presentation slides",
        "bookmarklet_url": "/apps/tools/convert-pdf-to-images/",
        "icon": "🖼️",
    },
    {
        "name": "Merge PDF",
        "description": "Combine multiple PDF files into a single document with drag-to-reorder.",
        "use_case": "Merge manuscript, figures, and supplements for submission",
        "bookmarklet_url": "/apps/tools/merge-pdf/",
        "icon": "📑",
    },
    {
        "name": "Split PDF",
        "description": "Extract specific pages from PDF files using page ranges.",
        "use_case": "Extract figures from compiled manuscript for separate upload",
        "bookmarklet_url": "/apps/tools/split-pdf/",
        "icon": "✂️",
    },
    {
        "name": "View Image",
        "description": "View dimensions, DPI, and unit conversions (mm/inch) for publication figures.",
        "use_case": "Verify Figure 2 meets journal dimension requirements",
        "bookmarklet_url": "/apps/tools/view-image/",
        "icon": "📐",
    },
]


# EOF
