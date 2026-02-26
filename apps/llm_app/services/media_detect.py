"""Media detection for AI chat tool results.

Delegates regex-based detection to ``scitex.media.render.detect``.
Adds JSON-parsing fallback for structured MCP tool results.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from scitex.media.render import (
    MEDIA_EXTENSIONS,  # noqa: F401
    classify,
)
from scitex.media.render import detect as extract_media_refs  # noqa: F401

# Keys in MCP tool JSON results that may contain file paths
_PATH_KEYS = frozenset(
    {"output_path", "image_path", "recipe_path", "file_path", "path"}
)


def extract_media_from_json(
    result_text: str, project_root: str
) -> list[dict[str, Any]]:
    """Extract media refs from structured JSON tool results.

    Fallback for when ``extract_media_refs`` regex doesn't match —
    handles relative paths and paths returned as JSON values.
    """
    try:
        data = json.loads(result_text)
    except (json.JSONDecodeError, TypeError):
        return []

    if not isinstance(data, dict):
        return []

    root = Path(project_root)
    refs: list[dict[str, Any]] = []
    seen: set[str] = set()

    for key in _PATH_KEYS:
        val = data.get(key)
        if not val or not isinstance(val, str):
            continue

        p = Path(val)

        if p.is_absolute():
            try:
                rel = str(p.relative_to(root))
            except ValueError:
                continue  # outside project root, can't serve via blob URL
        else:
            rel = val

        if rel in seen:
            continue

        ref = classify(rel)
        if ref is not None:
            seen.add(rel)
            refs.append(ref)

    return refs


# EOF
