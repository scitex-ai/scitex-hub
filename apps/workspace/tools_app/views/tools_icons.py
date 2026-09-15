#!/usr/bin/env python3
"""Font Awesome icons for the Tools list (one icon set instead of mixed emoji)."""

from __future__ import annotations

DOMAIN_ICONS = {
    "research": "fa-flask",
    "text": "fa-font",
    "image": "fa-image",
    "pdf": "fa-file-pdf",
    "rendering": "fa-chart-line",
    "audio": "fa-microphone",
    "video": "fa-film",
    "development": "fa-code",
}

TOOL_ICONS = {
    "transcribe-audio": "fa-microphone-lines",
    "image-cropper": "fa-crop-simple",
    "image-concatenator": "fa-table-cells-large",
    "image-format-converter": "fa-arrows-rotate",
    "gif-maker": "fa-photo-film",
    "images-to-pdf-converter": "fa-file-pdf",
    "pdf-to-images-converter": "fa-file-image",
    "mermaid-renderer": "fa-diagram-project",
    "image-resizer": "fa-up-right-and-down-left-from-center",
    "image-viewer": "fa-ruler-combined",
    "video-editor": "fa-scissors",
    "color-picker": "fa-palette",
    "csv-plot-viewer": "fa-chart-column",
    "repository-concatenator": "fa-box-archive",
    "qr-code-generator": "fa-qrcode",
    "element-inspector": "fa-magnifying-glass",
    "scitex-plot-tester": "fa-vial",
    "statistics-calculator": "fa-calculator",
    "citation-scraper": "fa-quote-right",
    "pdf-text-figure-extractor": "fa-file-export",
    "pdf-compressor": "fa-file-zipper",
    "pdf-merger": "fa-object-group",
    "pdf-splitter": "fa-object-ungroup",
    "docx-to-latex-converter": "fa-file-word",
    "json-formatter": "fa-code",
    "text-diff-checker": "fa-code-compare",
    "markdown-renderer": "fa-file-lines",
}


def with_icons(domains):
    """Copies of the domain/tool dicts with an ``fa_icon`` class added."""
    return [
        {
            **domain,
            "fa_icon": DOMAIN_ICONS.get(domain["slug"], "fa-wrench"),
            "tools": [
                {**tool, "fa_icon": TOOL_ICONS.get(tool["slug"], "fa-wrench")}
                for tool in domain["tools"]
            ],
        }
        for domain in domains
    ]
