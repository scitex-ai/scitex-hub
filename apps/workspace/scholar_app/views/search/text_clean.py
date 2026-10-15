"""Plain-text cleaning for scholarly metadata (JATS/XML tags, HTML entities)."""
from __future__ import annotations

import html as _html
import re as _re

TAGPAT = "<" + "[^>]+" + ">"


def clean_text(text: str | None) -> str:
    """Strip XML/JATS tags, unescape entities, collapse whitespace."""
    if not text:
        return ""
    no_tags = _re.sub(TAGPAT, " ", text)
    clean = _html.unescape(no_tags)
    return _re.sub(r"\s+", " ", clean).strip()


def clean_snippet(text: str | None, limit: int = 200) -> str:
    """Short display snippet; falls back when empty."""
    clean = clean_text(text)
    if not clean:
        return "No abstract available...."
    return clean[:limit] + "..." if len(clean) > limit else clean
