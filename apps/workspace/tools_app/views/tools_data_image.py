#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Research Tools data - Image domain tools.

``name`` : noun-form tool label. ``slug`` : kebab-case hash-URL anchor id.
"""

from __future__ import annotations

# Image tools
IMAGE_TOOLS = [
    {
        "name": "Image Cropper",
        "slug": "image-cropper",
        "description": "Batch crop images with same ROI coordinates for consistent figure panels.",
        "use_case": "Apply same crop region across all condition panels",
        "bookmarklet_url": "/apps/tools/crop-images/",
        "icon": "✂️",
    },
    {
        "name": "Image Concatenator",
        "slug": "image-concatenator",
        "description": "Combine multiple images into a single tiled multi-panel figure.",
        "use_case": "Create Figure 1 panel layouts (A, B, C, D)",
        "bookmarklet_url": "/apps/tools/concat-images/",
        "icon": "🖼️",
    },
    {
        "name": "Image Format Converter",
        "slug": "image-format-converter",
        "description": "Convert images between PNG, JPG, WEBP, TIFF formats with batch conversion.",
        "use_case": "Convert PNG figures to TIFF for journal submission",
        "bookmarklet_url": "/apps/tools/convert-image-format/",
        "icon": "🔄",
    },
    {
        "name": "GIF Maker",
        "slug": "gif-maker",
        "description": "Convert image sequences into animated GIF with customizable duration.",
        "use_case": "Create supplementary animations showing temporal changes",
        "bookmarklet_url": "/apps/tools/convert-images-to-gif/",
        "icon": "🎬",
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
        "name": "Mermaid Renderer",
        "slug": "mermaid-renderer",
        "description": "Create flowcharts, sequence diagrams, and concept diagrams from text syntax.",
        "use_case": "Design experimental workflow diagrams for Methods section",
        "bookmarklet_url": "/apps/tools/render-mmd/",
        "icon": "🧜‍♀️",
    },
    {
        "name": "Image Resizer",
        "slug": "image-resizer",
        "description": "Resize and crop images for journal submissions with preset dimensions.",
        "use_case": "Adjust Figure 2 to exact pixel-perfect journal specs",
        "bookmarklet_url": "/apps/tools/resize-image/",
        "icon": "📏",
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
