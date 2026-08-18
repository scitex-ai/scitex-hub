#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Mechanical barrier against the Writer workspace path drifting again.

Three silent production failures, one defect:

- 2026-07-08: visitor-pool verification checked the UNDOTTED
  ``scitex/writer`` while the real package created ``.scitex`` + writer.
  Verification never passed, so EVERY visitor slot was quarantined — and
  the security suite stayed green because its fakes fabricated the same
  wrong layout.
- 2026-07-28 -> 2026-08-02: ``writer_app`` still resolved the undotted
  path in 8 places, so ``writer_initialized`` was always False and every
  visitor saw an empty editor under a permanent "Loading...".
- 2026-08-17: the third drift was not a RE-TYPING but an OMISSION.
  ``views/editor/api/compilation.py`` spelled the compile script as
  ``scripts/shell/compile_manuscript.sh`` and exec'd
  ``bash /workspace/<that>``. The apptainer runner binds the PROJECT ROOT
  as ``/workspace``; the scripts live one segment down, inside the Writer
  workspace. No literal was re-typed, so the 2026-08-02 scan stayed green,
  and full compilation returned ``127 / No such file or directory`` for
  every user on scitex.ai.

The lesson of the third one is that "hub owns exactly one copy of the
string" is still one copy too many — hub is not the package that decides
the layout. scitex-writer publishes it now
(``scitex_writer.workspace_layout``, 2.42.0+), so the rule this file
enforces is stronger than before: **NO source under ``apps/`` may spell
either segment, including the hub module that used to be allowed to.**

Two independent mechanisms, because either alone is defeatable:

1. A SCAN of the real source tree (text). Catches a literal coming back.
2. VALUE assertions that cross hub's own outputs with the LIBRARY's
   values (behaviour). Catches a differently-spelled wrong answer, which
   a scan cannot see. Every expected value here is COMPUTED from
   ``scitex_writer.workspace_layout``; none is re-typed. A guard that
   hardcodes the segment in order to verify the segment passes forever
   and merely moves the duplication into the test.

The scan carries its own controls, because a source scan that silently
matches nothing is the classic vacuous green: it also passes when the
glob is wrong, the root is misresolved, or the regex is broken.
"""

import re
from pathlib import Path

import pytest
from scitex_writer.workspace_layout import (
    compile_script,
    compile_script_relpath,
    workspace_dir,
)

# tests/apps/writer_app/<this file> -> repo root
REPO_ROOT = Path(__file__).resolve().parents[3]
APPS_DIR = REPO_ROOT / "apps"

# ``project_root / "scitex" / "writer"`` in any quote style/spacing.
UNDOTTED_PATH_JOIN = re.compile(r"""["']scitex["']\s*/\s*["']writer["']""")

# The dotted workspace literal. Built from the library's own value so this
# guard cannot drift away from what it is guarding.
DOTTED_LITERAL = re.compile(
    r"""["']""" + re.escape(Path(workspace_dir("")).as_posix().lstrip("/")) + r"""["']"""
)

# The compile-script directory, likewise derived. Matches both the bare
# segment and any full script path built from it, in any quote style.
SCRIPT_DIR_LITERAL = re.compile(
    r"""["'][^"']*\b"""
    + re.escape(Path(compile_script_relpath("manuscript")).parent.as_posix())
    + r"""\b"""
)

SSOT_MODULE = "apps/infra/project_app/services/writer_workspace_layout.py"
LEAF_MODULE = "scitex_writer.workspace_layout"


def _python_sources(root=None):
    root = APPS_DIR if root is None else Path(root)
    return [
        path
        for path in root.rglob("*.py")
        if "__pycache__" not in path.parts and "node_modules" not in path.parts
    ]


def _hits(pattern, root=None, rel_to=None, skip_relpaths=()):
    rel_to = REPO_ROOT if rel_to is None else Path(rel_to)
    found = []
    for path in _python_sources(root):
        rel = path.relative_to(rel_to).as_posix()
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

    def test_the_scanner_reports_a_planted_violation_with_file_and_line(
        self, tmp_path: Path
    ):
        # Arrange: the end-to-end control the per-regex checks below cannot
        # give. A real file, on disk, containing the exact line that shipped
        # broken — walked by the same _hits() the real assertions use.
        planted = tmp_path / "regression.py"
        planted.write_text(
            "SCRIPT = '/workspace/"
            + Path(compile_script("", "manuscript")).as_posix().lstrip("/")
            + "'\n",
            encoding="utf-8",
        )
        # Act
        hits = _hits(SCRIPT_DIR_LITERAL, root=tmp_path, rel_to=tmp_path)
        # Assert
        assert hits and hits[0].startswith("regression.py:1:"), (
            "The scanner cannot find a violation planted in a real file, so "
            "an empty result over apps/ proves nothing. Got: " + repr(hits)
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
        sample = "writer_dir = get_writer_workspace_path(project_root)"
        # Act
        matched = UNDOTTED_PATH_JOIN.search(sample)
        # Assert
        assert matched is None

    def test_the_dotted_pattern_matches_the_literal_it_tracks(self):
        # Arrange: composed from the library, not typed out.
        segment = Path(workspace_dir("")).as_posix().lstrip("/")
        sample = f'WRITER_WORKSPACE_RELPATH = "{segment}"'
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

    def test_the_script_dir_pattern_ignores_the_correct_call(self):
        # Arrange — resolving through the leaf package must NOT trip the
        # scan, otherwise the guard punishes the very fix it asks for.
        sample = "script_path = compile_script(project_dir, doc_type)"
        # Act
        matched = SCRIPT_DIR_LITERAL.search(sample)
        # Assert
        assert matched is None


class TestNoSourceUnderAppsSpellsTheLayout:
    """The scan. Text only — see the value assertions for the other half."""

    def test_the_undotted_spelling_is_absent(self):
        # Arrange
        pattern = UNDOTTED_PATH_JOIN
        # Act
        hits = _hits(pattern)
        # Assert
        assert hits == [], (
            "The undotted 'scitex/writer' path is back. scitex_writer "
            "creates the DOTTED workspace; this spelling makes "
            "writer_initialized permanently False and blanks the editor. "
            f"Import get_writer_workspace_path from {SSOT_MODULE} "
            "instead.\nOffending lines:\n" + "\n".join(hits)
        )

    def test_the_workspace_literal_is_absent(self):
        # Arrange: NO skip list. Since 2.42.0 the value is published by the
        # leaf package, so not even the hub SSoT may re-type it.
        pattern = DOTTED_LITERAL
        # Act
        hits = _hits(pattern)
        # Assert
        assert hits == [], (
            "The Writer workspace path is spelled out in hub. It is "
            f"published by {LEAF_MODULE} — import it. Two spellings of one "
            "path is how this drifted three times.\nOffending lines:\n"
            + "\n".join(hits)
        )

    def test_the_script_dir_literal_is_absent(self):
        # Arrange
        pattern = SCRIPT_DIR_LITERAL
        # Act
        hits = _hits(pattern)
        # Assert
        assert hits == [], (
            "A compile-script path is being assembled by hand. That is how "
            "full compilation shipped pointing one segment above the Writer "
            "workspace and returned 127 for every user. Call "
            f"{LEAF_MODULE}.compile_script(project_root, doc_type) "
            "instead.\nOffending lines:\n" + "\n".join(hits)
        )

    def test_the_ssot_module_imports_the_value_instead_of_spelling_it(self):
        # Arrange: counterpart to the three scans above. They would also
        # pass if hub had simply DELETED the constant, leaving callers to
        # invent their own. This asserts the replacement is the import.
        ssot = REPO_ROOT / SSOT_MODULE
        # Act
        content = ssot.read_text(encoding="utf-8")
        # Assert
        assert LEAF_MODULE in content, (
            f"{SSOT_MODULE} no longer imports from {LEAF_MODULE}, so the "
            "scans above are guarding an empty room."
        )


class TestTheValuesAgreeWithTheLibrary:
    """The behaviour, not the spelling.

    Every expectation is COMPUTED from ``scitex_writer.workspace_layout``.
    Re-typing the segment here to check the segment would pass forever.
    """

    def test_hubs_workspace_constant_is_the_librarys_value(self):
        # Arrange
        from apps.infra.project_app.services.writer_workspace_layout import (
            WRITER_WORKSPACE_RELPATH,
        )

        expected = Path(workspace_dir("")).as_posix().lstrip("/")
        # Act
        actual = WRITER_WORKSPACE_RELPATH
        # Assert
        assert actual == expected

    def test_hubs_workspace_path_is_the_librarys_path(self, tmp_path: Path):
        # Arrange
        from apps.infra.project_app.services.writer_workspace_layout import (
            get_writer_workspace_path,
        )

        expected = workspace_dir(tmp_path)
        # Act
        actual = get_writer_workspace_path(tmp_path)
        # Assert
        assert actual == expected

    @pytest.mark.parametrize("doc_type", ["manuscript", "supplementary", "revision"])
    def test_the_script_resolves_inside_the_workspace(
        self, tmp_path: Path, doc_type: str
    ):
        # Arrange: both sides from the library — this asserts the CONTRACT
        # hub relies on (the script is under the workspace, not the project
        # root), which is exactly what the 127 proved was not being honoured
        # by hub's hand-built path.
        expected_parent = workspace_dir(tmp_path)
        # Act
        resolved = compile_script(tmp_path, doc_type)
        # Assert
        assert resolved.is_relative_to(expected_parent)

    def test_the_script_is_not_at_the_project_root(self, tmp_path: Path):
        # Arrange: the positive control for the test above. "Under the
        # project root" is true of BOTH the correct path and the one that
        # returned 127; only "not directly under it" separates them.
        # Act
        resolved = compile_script(tmp_path, "manuscript")
        # Assert
        assert resolved.parent.parent.parent != tmp_path, (
            f"{resolved} sits at the project root. The apptainer runner "
            "binds the project root as /workspace, so this is the shape "
            "that produced 'bash: ...: No such file or directory'."
        )

    def test_an_unknown_doc_type_is_refused(self, tmp_path: Path):
        # Arrange: the leaf refuses rather than silently compiling the
        # manuscript when the caller asked for something else.
        refusal = pytest.raises(ValueError)
        # Act / Assert
        with refusal:
            compile_script(tmp_path, "not-a-real-doc-type")

    def test_the_refusal_names_the_valid_set(self, tmp_path: Path):
        # Arrange
        message = ""
        # Act
        try:
            compile_script(tmp_path, "not-a-real-doc-type")
        except ValueError as exc:
            message = str(exc)
        # Assert
        assert "manuscript" in message, (
            "the caller cannot see the doc_type table; the refusal has to "
            f"name it. Got: {message!r}"
        )


if __name__ == "__main__":
    import os

    pytest.main([os.path.abspath(__file__)])

# EOF
