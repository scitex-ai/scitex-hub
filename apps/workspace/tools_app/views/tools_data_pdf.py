#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Research Tools data - PDF domain tools.

``name`` : noun-form tool label. ``slug`` : kebab-case hash-URL anchor id.
"""

from __future__ import annotations

# PDF tools (shares some with Image)
PDF_TOOLS = [
    {
        "name": "PDF Compressor",
        "slug": "pdf-compressor",
        "description": "Reduce PDF file size while maintaining quality for email and uploads.",
        "use_case": "Compress submission files under journal size limits",
        "bookmarklet_url": "/apps/tools/compress-pdf/",
        "icon": "🗜️",
    },
    {
        "name": "Images to PDF Converter",
        "slug": "images-to-pdf-converter",
        "description": "Convert multiple images into a single PDF with custom page orientation.",
        "use_case": "Create supplementary figures PDF from multiple images",
        "bookmarklet_url": "/apps/tools/convert-images-to-pdf/",
        "icon": "📄",
    },
    {
        "name": "PDF to Images Converter",
        "slug": "pdf-to-images-converter",
        "description": "Extract all pages from PDF as PNG or JPG images with adjustable DPI.",
        "use_case": "Convert PDF figures to images for presentation slides",
        "bookmarklet_url": "/apps/tools/convert-pdf-to-images/",
        "icon": "🖼️",
    },
    {
        "name": "PDF Merger",
        "slug": "pdf-merger",
        "description": "Combine multiple PDF files into a single document with drag-to-reorder.",
        "use_case": "Merge manuscript, figures, and supplements for submission",
        "bookmarklet_url": "/apps/tools/merge-pdf/",
        "icon": "📑",
    },
    {
        "name": "PDF Splitter",
        "slug": "pdf-splitter",
        "description": "Extract specific pages from PDF files using page ranges.",
        "use_case": "Extract figures from compiled manuscript for separate upload",
        "bookmarklet_url": "/apps/tools/split-pdf/",
        "icon": "✂️",
    },
    {
        "name": "Image Viewer",
        "slug": "image-viewer",
        "description": "View dimensions, DPI, and unit conversions (mm/inch) for publication figures.",
        "use_case": "Verify Figure 2 meets journal dimension requirements",
        "bookmarklet_url": "/apps/tools/view-image/",
        "icon": "📐",
    },
]


# EOF
