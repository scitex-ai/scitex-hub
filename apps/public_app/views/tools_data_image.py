#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Research Tools data - Image domain tools."""

from __future__ import annotations

# Image tools
IMAGE_TOOLS = [
    {
        "name": "Image & PDF Viewer",
        "description": "View dimensions, DPI, and unit conversions (mm/inch) for publication figures.",
        "use_case": "Verify Figure 2 meets journal dimension requirements",
        "bookmarklet_url": "/tools/image-viewer/",
        "icon": "📐",
    },
    {
        "name": "Image Resizer",
        "description": "Resize and crop images for journal submissions with preset dimensions.",
        "use_case": "Adjust Figure 2 to exact pixel-perfect journal specs",
        "bookmarklet_url": "/tools/image-resizer/",
        "icon": "📏",
    },
    {
        "name": "Image Converter",
        "description": "Convert images between PNG, JPG, WEBP, TIFF formats with batch conversion.",
        "use_case": "Convert PNG figures to TIFF for journal submission",
        "bookmarklet_url": "/tools/image-converter/",
        "icon": "🔄",
    },
    {
        "name": "Image Concatenator",
        "description": "Combine multiple images into a single tiled multi-panel figure.",
        "use_case": "Create Figure 1 panel layouts (A, B, C, D)",
        "bookmarklet_url": "/tools/image-concatenator/",
        "icon": "🖼️",
    },
    {
        "name": "Mermaid Diagram Renderer",
        "description": "Create flowcharts, sequence diagrams, and concept diagrams from text syntax.",
        "use_case": "Design experimental workflow diagrams for Methods section",
        "bookmarklet_url": "/tools/mermaid-renderer/",
        "icon": "🧜‍♀️",
    },
    {
        "name": "Images to GIF",
        "description": "Convert image sequences into animated GIF with customizable duration.",
        "use_case": "Create supplementary animations showing temporal changes",
        "bookmarklet_url": "/tools/images-to-gif/",
        "icon": "🎬",
    },
    {
        "name": "Images to PDF",
        "description": "Convert multiple images into a single PDF with custom page orientation.",
        "use_case": "Create supplementary figures PDF from multiple images",
        "bookmarklet_url": "/tools/images-to-pdf/",
        "icon": "📄",
    },
    {
        "name": "PDF to Images",
        "description": "Extract all pages from PDF as PNG or JPG images with adjustable DPI.",
        "use_case": "Convert PDF figures to images for presentation slides",
        "bookmarklet_url": "/tools/pdf-to-images/",
        "icon": "🖼️",
    },
]


# EOF
