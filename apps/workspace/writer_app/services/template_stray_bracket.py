"""Remove the stray 「」」 line the old writer template left after ``%%%% EOF``.

scitex-writer #393 fixed the template, but workspaces created from the old
one still carry it in their contents/*.tex, and it breaks every compile.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)

_STRAY_AFTER_EOF = re.compile(r"(%%%% EOF[ \t]*\r?\n)[ \t]*」[ \t]*(\r?\n)?\s*\Z")
_MAX_BYTES = 1_000_000


def strip_stray_bracket_text(text: str) -> str:
    return _STRAY_AFTER_EOF.sub(r"\1", text)


def strip_stray_brackets(writer_dir: Path) -> list[Path]:
    """Fix every ``*/contents/**/*.tex`` under ``writer_dir``; return the files changed."""
    changed = []
    if not writer_dir.is_dir():
        return changed
    for path in writer_dir.glob("*/contents/**/*.tex"):
        try:
            if path.is_symlink() or path.stat().st_size > _MAX_BYTES:
                continue
            text = path.read_text(encoding="utf-8")
            if "」" not in text:
                continue
            fixed = strip_stray_bracket_text(text)
            if fixed != text:
                path.write_text(fixed, encoding="utf-8")
                changed.append(path)
        except (OSError, UnicodeDecodeError) as exc:
            logger.warning("stray-bracket cleanup skipped %s: %s", path, exc)
    if changed:
        logger.info("Removed stray template bracket from %d file(s) in %s", len(changed), writer_dir)
    return changed
