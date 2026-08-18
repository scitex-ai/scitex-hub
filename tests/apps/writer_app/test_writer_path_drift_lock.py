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

THIRD INCIDENT, 2026-08-17 — and the guard above did not catch it,
because the third drift was not a re-typing but an OMISSION.
``writer_app/views/editor/api/compilation.py`` spelled the compile
script as ``"scripts/shell/compile_manuscript.sh"`` and exec'd
``bash /workspace/<that>``. The apptainer runner binds the PROJECT ROOT
as ``/workspace``; the scripts live one level down, inside
``.scitex/writer/``. So the workspace segment was simply absent, no
literal was re-typed, every scan above stayed green, and full
compilation returned ``127 / No such file or directory`` for EVERY user
on scitex.ai until it was measured by hand.

The lesson is that "don't re-type the constant" only guards half of it.
The other half is: the ``scripts/shell`` segment must also have exactly
one home, so nobody can assemble a script path by hand and get the
prefix wrong. Hence :data:`SCRIPT_DIR_LITERAL` below.
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

# The compile-script directory, which only the SSoT module may spell.
# Matches both the bare segment and a full script path built from it, in
# any quote style — e.g. "scripts/shell", 'scripts/shell/compile_x.sh',
# f"/workspace/scripts/shell/{name}".
SCRIPT_DIR_LITERAL = re.compile(r"""["'][^"']*\bscripts/shell\b""")

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

    def test_the_script_dir_pattern_matches_the_line_that_shipped_broken(self):
        # Arrange — the EXACT line that killed full compilation in prod.
        shipped = '"manuscript": "scripts/shell/compile_manuscript.sh",'
        # Act
        matched = SCRIPT_DIR_LITERAL.search(shipped)
        # Assert
        assert matched is not None, "The regex cannot detect the bug it guards."

    def test_the_script_dir_pattern_matches_the_bare_segment(self):
        # Arrange
        bare = 'COMPILE_SCRIPT_DIRNAME = "scripts/shell"'
        # Act
        matched = SCRIPT_DIR_LITERAL.search(bare)
        # Assert
        assert matched is not None

    def test_the_script_dir_pattern_ignores_the_correct_call(self):
        # Arrange — resolving through the SSoT must NOT trip the scan,
        # otherwise the guard punishes the very fix it is asking for.
        sample = "script_rel = get_compile_script_relpath(doc_type)"
        # Act
        matched = SCRIPT_DIR_LITERAL.search(sample)
        # Assert
        assert matched is None


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


class TestTheScriptDirLiteralHasExactlyOneHome:
    """The half the 2026-08-02 guard did not cover: OMISSION.

    Re-typing ``.scitex/writer`` was already forbidden. Leaving it OUT
    was not — and that is the shape the third incident took. Forcing the
    ``scripts/shell`` segment to have one home closes it: a caller that
    cannot spell the segment cannot assemble the wrong prefix in front of
    it either, and must call ``get_compile_script_relpath()``.
    """

    def test_only_the_ssot_module_spells_the_script_dir(self):
        # Arrange
        pattern = SCRIPT_DIR_LITERAL
        # Act
        hits = _hits(pattern, skip_relpaths=(SSOT_MODULE,))
        # Assert
        assert hits == [], (
            "A compile-script path is being assembled by hand outside the "
            f"single source of truth ({SSOT_MODULE}). That is how full "
            "compilation shipped pointing at /workspace/scripts/shell/... "
            "— one level above the Writer workspace — and returned 127 for "
            "every user. Call get_compile_script_relpath(doc_type) "
            "instead.\nOffending lines:\n" + "\n".join(hits)
        )

    def test_the_ssot_module_does_spell_the_script_dir(self):
        # Arrange: counterpart to the exclusion above — if the SSoT stops
        # containing the segment, the skip excludes nothing and the guard
        # is vacuous.
        ssot = REPO_ROOT / SSOT_MODULE
        # Act
        content = ssot.read_text(encoding="utf-8")
        # Assert
        assert SCRIPT_DIR_LITERAL.search(content) is not None


class TestTheResolvedScriptPathIsInsideTheWorkspace:
    """The behaviour, not just the spelling.

    A scan can only see text. This asserts the value the SSoT actually
    returns, so the guard survives someone satisfying the scan with a
    differently-spelled wrong answer.
    """

    def test_the_script_path_starts_at_the_writer_workspace(self):
        # Arrange
        from apps.infra.project_app.services.writer_workspace_layout import (
            WRITER_WORKSPACE_RELPATH,
            get_compile_script_relpath,
        )

        # Act
        relpath = get_compile_script_relpath("manuscript")
        # Assert
        assert relpath.startswith(f"{WRITER_WORKSPACE_RELPATH}/"), (
            f"{relpath!r} does not start inside the Writer workspace. "
            "This is the exact defect: the apptainer runner binds the "
            "PROJECT ROOT as /workspace, so a path missing the "
            f"{WRITER_WORKSPACE_RELPATH} segment resolves one level too "
            "high and bash answers 127."
        )

    def test_an_unknown_doc_type_still_lands_in_the_workspace(self):
        # Arrange
        from apps.infra.project_app.services.writer_workspace_layout import (
            WRITER_WORKSPACE_RELPATH,
            get_compile_script_relpath,
        )

        # Act
        relpath = get_compile_script_relpath("not-a-real-doc-type")
        # Assert
        assert relpath.startswith(f"{WRITER_WORKSPACE_RELPATH}/")


if __name__ == "__main__":
    import os

    import pytest

    pytest.main([os.path.abspath(__file__)])
