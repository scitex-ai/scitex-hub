#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Mechanical barrier against the Writer workspace path drifting again.

The undotted ``scitex/writer`` spelling has now caused two silent
production failures (2026-07-08 visitor-slot quarantine, 2026-07-28
blank Writer editor). Both were found by hand, weeks apart. A written
warning did not prevent the second one — the 2026-07-08 fix left a
comment naming the incident, and writer_app still carried the undotted
spelling in 8 places for three more weeks.

So this is a scan, not a note: it reads the real source tree and fails
if the undotted spelling comes back anywhere under ``apps/``.

The scan carries its own controls, because a source scan that silently
matches nothing is the classic vacuous green: it also passes when the
glob is wrong, the root is misresolved, or the regex is broken.
"""

import re
from pathlib import Path

# tests/apps/writer_app/<this file> -> repo root
REPO_ROOT = Path(__file__).resolve().parents[3]
APPS_DIR = REPO_ROOT / "apps"

# ``project_root / "scitex" / "writer"`` in any quote style/spacing.
UNDOTTED_PATH_JOIN = re.compile(r"""["']scitex["']\s*/\s*["']writer["']""")

# The dotted literal, which only the SSoT module may spell.
DOTTED_LITERAL = re.compile(r"""["']\.scitex/writer["']""")

SSOT_MODULE = "apps/infra/project_app/services/writer_workspace_layout.py"


def _python_sources():
    return [
        path
        for path in APPS_DIR.rglob("*.py")
        if "__pycache__" not in path.parts and "node_modules" not in path.parts
    ]


def _hits(pattern, skip_relpaths=()):
    found = []
    for path in _python_sources():
        rel = path.relative_to(REPO_ROOT).as_posix()
        if rel in skip_relpaths:
            continue
        for lineno, line in enumerate(
            path.read_text(encoding="utf-8", errors="replace").splitlines(), 1
        ):
            if pattern.search(line):
                found.append(f"{rel}:{lineno}: {line.strip()}")
    return found


class TestTheScanCanActuallyFail:
    """Controls. Without these, every assertion below passes for free."""

    def test_the_scan_reads_a_non_trivial_number_of_files(self):
        # Arrange
        minimum_expected = 100
        # Act
        sources = _python_sources()
        # Assert
        assert len(sources) > minimum_expected, (
            f"Only {len(sources)} python files found under {APPS_DIR}. "
            "The scan is not reaching the source tree, so its 'no hits' "
            "result would be meaningless."
        )

    def test_the_undotted_pattern_matches_the_spelling_it_forbids(self):
        # Arrange
        sample = 'writer_dir = project_root / "scitex" / "writer"'
        # Act
        matched = UNDOTTED_PATH_JOIN.search(sample)
        # Assert
        assert matched is not None, "The regex cannot detect the bug it guards."

    def test_the_undotted_pattern_ignores_the_correct_spelling(self):
        # Arrange
        sample = 'writer_dir = get_writer_workspace_path(project_root)'
        dotted = 'RELPATH = ".scitex/writer"'
        # Act
        matched_correct = UNDOTTED_PATH_JOIN.search(sample)
        matched_dotted = UNDOTTED_PATH_JOIN.search(dotted)
        # Assert
        assert matched_correct is None and matched_dotted is None

    def test_the_dotted_pattern_matches_the_literal_it_tracks(self):
        # Arrange
        sample = 'WRITER_WORKSPACE_RELPATH = ".scitex/writer"'
        # Act
        matched = DOTTED_LITERAL.search(sample)
        # Assert
        assert matched is not None


class TestNoUndottedWriterPath:
    def test_the_undotted_spelling_is_absent_from_apps(self):
        # Arrange
        pattern = UNDOTTED_PATH_JOIN
        # Act
        hits = _hits(pattern)
        # Assert
        assert hits == [], (
            "The undotted 'scitex/writer' path is back. scitex_writer "
            "creates '.scitex/writer'; this spelling makes "
            "writer_initialized permanently False and blanks the editor. "
            "Import get_writer_workspace_path from "
            f"{SSOT_MODULE} instead.\nOffending lines:\n" + "\n".join(hits)
        )


class TestTheDottedLiteralHasExactlyOneHome:
    def test_only_the_ssot_module_spells_the_literal(self):
        # Arrange
        pattern = DOTTED_LITERAL
        # Act
        hits = _hits(pattern, skip_relpaths=(SSOT_MODULE,))
        # Assert
        assert hits == [], (
            "The '.scitex/writer' literal is re-typed outside the single "
            f"source of truth ({SSOT_MODULE}). Two spellings of one path "
            "is exactly how this drifted twice — import the constant.\n"
            "Offending lines:\n" + "\n".join(hits)
        )

    def test_the_ssot_module_does_spell_it(self):
        # Arrange: the counterpart to the test above. If the SSoT ever
        # stops containing the literal, the exclusion above would be
        # excluding nothing and the whole guard would be vacuous.
        ssot = REPO_ROOT / SSOT_MODULE
        # Act
        content = ssot.read_text(encoding="utf-8")
        # Assert
        assert DOTTED_LITERAL.search(content) is not None


if __name__ == "__main__":
    import os

    import pytest

    pytest.main([os.path.abspath(__file__)])
