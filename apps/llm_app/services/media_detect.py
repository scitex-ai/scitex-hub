"""Detect media file references in MCP tool result text."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

MEDIA_EXTENSIONS: dict[str, set[str]] = {
    "image": {".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".bmp"},
    "pdf": {".pdf"},
    "csv": {".csv", ".tsv"},
    "plotly": {".html"},
    "mermaid": {".mmd"},
}

# Build reverse lookup: extension -> media type
_EXT_TO_TYPE: dict[str, str] = {}
for _media_type, _exts in MEDIA_EXTENSIONS.items():
    for _ext in _exts:
        _EXT_TO_TYPE[_ext] = _media_type


def extract_media_refs(
    result_text: str, project_root: str | None
) -> list[dict[str, Any]]:
    """Extract file paths from tool result text and classify by media type.

    Scans for absolute paths starting with project_root, strips the prefix to
    get a relative path, and classifies by file extension.

    Returns:
        List of dicts: [{"type": "image", "path": "figures/plot.png", "ext": ".png"}]
    """
    if not project_root or not result_text:
        return []

    refs: list[dict[str, Any]] = []
    seen: set[str] = set()

    # Match absolute paths: project_root followed by /segments/file.ext
    # Path chars: alphanumeric, underscore, hyphen, dot, forward slash
    # Terminates at space, comma, quote, paren, newline, etc.
    pattern = re.escape(project_root.rstrip("/")) + r"(/[\w.\-/]+)"
    for match in re.finditer(pattern, result_text):
        rel_path = match.group(1).lstrip("/")
        if rel_path in seen:
            continue

        ext = Path(rel_path).suffix.lower()
        media_type = _EXT_TO_TYPE.get(ext)
        if media_type:
            seen.add(rel_path)
            refs.append({"type": media_type, "path": rel_path, "ext": ext})

    return refs


# EOF
