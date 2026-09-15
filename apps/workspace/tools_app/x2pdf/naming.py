"""Pick a readable, filesystem-safe PDF name from what we know about the source."""

from __future__ import annotations

import datetime as _dt
import re
import unicodedata
from pathlib import PurePosixPath
from urllib.parse import unquote, urlsplit

_MAX_STEM = 80
# \w is Unicode-aware, so Japanese and other scripts survive.
_UNSAFE = re.compile(r"[^\w\-.()]+")
_RUNS = re.compile(r"_{2,}")


def slugify_filename(text: str | None, max_len: int = _MAX_STEM) -> str:
    if not text:
        return ""
    text = unicodedata.normalize("NFKC", str(text))
    text = "".join(ch for ch in text if unicodedata.category(ch)[0] != "C")
    text = _UNSAFE.sub("_", text)
    text = _RUNS.sub("_", text).strip("._- ")
    text = text[:max_len].rstrip("._- ")
    return text


def _url_stem(url: str) -> str:
    parts = urlsplit(url)
    host = (parts.hostname or "").removeprefix("www.")
    path = unquote(parts.path or "").strip("/")
    last = PurePosixPath(path).stem if path else ""
    return slugify_filename(f"{host}_{last}" if last else host)


def derive_pdf_filename(
    *,
    title: str | None = None,
    original_name: str | None = None,
    url: str | None = None,
    today: _dt.date | None = None,
) -> str:
    """Title first, then the uploaded file's name, then the URL; web sources get a date."""
    date = (today or _dt.date.today()).isoformat()
    stem = slugify_filename(title)
    if not stem and original_name:
        stem = slugify_filename(PurePosixPath(original_name.replace("\\", "/")).stem)
    if not stem and url:
        stem = _url_stem(url)
    if url and stem:
        stem = f"{stem}_{date}"
    if not stem:
        stem = f"converted_{date}"
    return f"{stem}.pdf"
