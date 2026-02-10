#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Research Tools data - Image domain tools."""

from __future__ import annotations

# Image tools (alphabetical by name)
IMAGE_TOOLS = [
    {
        "name": "Crop Image",
        "description": "Crop images with visual selection for precise publication-ready figures.",
        "use_case": "Crop whitespace or select regions from figure panels",
        "bookmarklet_url": "/tools/image-cropper/",
        "icon": "✂️",
    },
    {
        "name": "Concat Images",
        "description": "Combine multiple images into a single tiled multi-panel figure.",
        "use_case": "Create Figure 1 panel layouts (A, B, C, D)",
        "bookmarklet_url": "/tools/image-concatenator/",
        "icon": "🖼️",
    },
    {
        "name": "Convert Image Format",
        "description": "Convert images between PNG, JPG, WEBP, TIFF formats with batch conversion.",
        "use_case": "Convert PNG figures to TIFF for journal submission",
        "bookmarklet_url": "/tools/image-converter/",
        "icon": "🔄",
    },
    {
        "name": "Convert Images to GIF",
        "description": "Convert image sequences into animated GIF with customizable duration.",
        "use_case": "Create supplementary animations showing temporal changes",
        "bookmarklet_url": "/tools/images-to-gif/",
        "icon": "🎬",
    },
    {
        "name": "Convert Images to PDF",
        "description": "Convert multiple images into a single PDF with custom page orientation.",
        "use_case": "Create supplementary figures PDF from multiple images",
        "bookmarklet_url": "/tools/images-to-pdf/",
        "icon": "📄",
    },
    {
        "name": "Convert PDF to Images",
        "description": "Extract all pages from PDF as PNG or JPG images with adjustable DPI.",
        "use_case": "Convert PDF figures to images for presentation slides",
        "bookmarklet_url": "/tools/pdf-to-images/",
        "icon": "🖼️",
    },
    {
        "name": "Render MMD",
        "description": "Create flowcharts, sequence diagrams, and concept diagrams from text syntax.",
        "use_case": "Design experimental workflow diagrams for Methods section",
        "bookmarklet_url": "/tools/mermaid-renderer/",
        "icon": "🧜‍♀️",
    },
    {
        "name": "Resize Image",
        "description": "Resize and crop images for journal submissions with preset dimensions.",
        "use_case": "Adjust Figure 2 to exact pixel-perfect journal specs",
        "bookmarklet_url": "/tools/image-resizer/",
        "icon": "📏",
    },
    {
        "name": "View Image",
        "description": "View dimensions, DPI, and unit conversions (mm/inch) for publication figures.",
        "use_case": "Verify Figure 2 meets journal dimension requirements",
        "bookmarklet_url": "/tools/image-viewer/",
        "icon": "📐",
    },
]


# EOF
