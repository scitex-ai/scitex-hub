#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Full compilation must find its script, and say why when it fails.

Measured on live scitex.ai 2026-08-17. Preview compiled fine — HTTP 200,
a real PDF written and fetchable — so the TeX toolchain and the sandbox
were healthy. Full compilation returned, for every user::

    POST .../compile_full/            -> 200 {"job_id": ...}
    GET  .../compilation/status/<id>/ ->
      {"status":"failed",
       "result":{"success":false,"returncode":127},
       "log":"/usr/bin/bash: /workspace/scripts/shell/compile_manuscript.sh:
              No such file or directory"}

Three separate defects, one symptom:

1. ``run_compilation_async`` hardcoded the script path and exec'd
   ``bash /workspace/<that>``, while the apptainer runner binds the
   PROJECT ROOT as ``/workspace`` and the scripts are vendored inside the
   Writer workspace. One segment too high — rc 127.
2. The compiled PDF was looked for under the project root while the
   script writes it inside the workspace, so fixing only (1) would have
   produced a green compile reporting NO PDF FOUND.
3. ``final_result`` was built with no ``error`` key at all, while
   ``compilation-queue.ts::handleFailed`` reads
   ``data.result?.error || "Compilation failed"``. So even once the
   script is found, a real failure would still announce itself with a
   generic four-word string.

These tests assert at the level that failed: the argv actually handed to
the sandbox, and the dict actually handed to the poller. No HTTP, no DB,
no apptainer — those were all working. The workspaces are REAL
directories laid out with the leaf package's own paths, so nothing here
is a fake that could agree with a wrong answer.

Every expected path is COMPUTED from ``scitex_writer.workspace_layout``.
Re-typing the segments to check the segments would pass forever.
"""

from pathlib import Path

import pytest
from scitex_writer.workspace_layout import compile_script, workspace_dir

from apps.workspace.writer_app.views.editor.api.compilation_full_job import (
    CONTAINER_PROJECT_ROOT,
    CompileScriptMissing,
    build_final_result,
    build_inner_cmd,
    locate_compiled_pdf,
    resolve_compile_script,
)

DOC_TYPES = ["manuscript", "supplementary", "revision"]

# The literal argv the sandbox received in production, from the log above.
BROKEN_PROD_ARGV = "/workspace/scripts/shell/compile_manuscript.sh"

# The runner's shape on the measured failure (apptainer_runner merges the
# child's stderr into stdout, which is why the bash message arrived there).
PROD_RC127 = {
    "success": False,
    "returncode": 127,
    "stdout": (
        "/usr/bin/bash: /workspace/scripts/shell/compile_manuscript.sh: "
        "No such file or directory"
    ),
    "stderr": "",
}

# A genuine TeX failure, so the shared precedence is exercised on the
# case it was written for.
PROD_TEX_FAILURE = {
    "success": False,
    "returncode": 12,
    "stdout": (
        "This is pdfTeX, Version 3.141592653\n"
        "! LaTeX Error: Unicode character 」 (U+300D)\n"
        "                not set up for use with LaTeX.\n"
        "\n"
        "! ==> Fatal error occurred, no output PDF file produced!\n"
    ),
    "stderr": "",
}


def _real_workspace(project_root: Path, doc_types=DOC_TYPES) -> Path:
    """Lay out the compile scripts where the leaf package says they live."""
    for doc_type in doc_types:
        script = compile_script(project_root, doc_type)
        script.parent.mkdir(parents=True, exist_ok=True)
        script.write_text("#!/bin/bash\necho compiled\n", encoding="utf-8")
    return project_root


@pytest.fixture
def project_root(tmp_path: Path) -> Path:
    return _real_workspace(tmp_path / "proj")


class TestTheScriptPathReachesTheWorkspace:
    """The argv, which is what bash actually resolved."""

    def test_the_command_targets_the_path_the_library_names(
        self, project_root: Path
    ):
        # Arrange: expectation derived from the leaf package, not re-typed.
        relpath = compile_script(project_root, "manuscript").relative_to(project_root)
        expected = f"{CONTAINER_PROJECT_ROOT}/{relpath.as_posix()}"
        # Act
        argv = build_inner_cmd(project_root, "manuscript", {})
        # Assert
        assert argv[1] == expected, (
            f"full compile execs {argv[1]!r}; scitex_writer says the script "
            f"is at {expected!r} inside the bound project root."
        )

    def test_the_command_is_not_the_path_that_returned_127(
        self, project_root: Path
    ):
        # Arrange: the exact string prod's bash could not find. This is the
        # positive control for the test above — it fails if someone reverts
        # to assembling the path at the project root, which asserting only
        # "starts with /workspace/" would not catch.
        forbidden = BROKEN_PROD_ARGV
        # Act
        argv = build_inner_cmd(project_root, "manuscript", {})
        # Assert
        assert argv[1] != forbidden, (
            "the pre-fix path is back; this is the argv that produced "
            "returncode 127 for every user on scitex.ai."
        )

    def test_bash_is_still_the_interpreter(self, project_root: Path):
        # Arrange
        expected = "bash"
        # Act
        argv = build_inner_cmd(project_root, "manuscript", {})
        # Assert
        assert argv[0] == expected

    @pytest.mark.parametrize("doc_type", DOC_TYPES)
    def test_every_doc_type_resolves_inside_the_workspace(
        self, project_root: Path, doc_type: str
    ):
        # Arrange: the workspace segment as the sandbox sees it, computed.
        relpath = workspace_dir(project_root).relative_to(project_root)
        prefix = f"{CONTAINER_PROJECT_ROOT}/{relpath.as_posix()}/"
        # Act
        argv = build_inner_cmd(project_root, doc_type, {})
        # Assert
        assert argv[1].startswith(prefix)

    def test_the_flags_still_follow_the_script(self, project_root: Path):
        # Arrange: the path fix must not disturb the option plumbing.
        options = {"no_figs": True, "color_mode": "dark"}
        # Act
        argv = build_inner_cmd(project_root, "manuscript", options)
        # Assert
        assert argv[2:] == ["--no-figs", "--color-mode", "dark"]


class TestAMissingScriptFailsLoudly:
    """``compile_script()`` does not existence-check. Hub executes it.

    ``bash: ...: No such file or directory`` names the symptom and hides
    which project root the caller held — the reason this took so long to
    diagnose. Hub must not hand that message to the user again.
    """

    def test_a_missing_script_raises_instead_of_being_exec_d(
        self, tmp_path: Path
    ):
        # Arrange: a project root with no Writer workspace at all.
        bare = tmp_path / "never-initialised"
        bare.mkdir()
        refusal = pytest.raises(CompileScriptMissing)
        # Act / Assert
        with refusal:
            build_inner_cmd(bare, "manuscript", {})

    def test_the_error_names_the_resolved_script_path(self, tmp_path: Path):
        # Arrange
        bare = tmp_path / "never-initialised"
        bare.mkdir()
        expected = str(compile_script(bare, "manuscript"))
        message = ""
        # Act
        try:
            resolve_compile_script(bare, "manuscript")
        except CompileScriptMissing as exc:
            message = str(exc)
        # Assert
        assert expected in message, (
            "the report must name the path that was about to be executed; "
            f"got {message!r}"
        )

    def test_the_error_names_the_project_root_it_came_from(
        self, tmp_path: Path
    ):
        # Arrange: the half `bash` never told anyone.
        bare = tmp_path / "never-initialised"
        bare.mkdir()
        message = ""
        # Act
        try:
            resolve_compile_script(bare, "manuscript")
        except CompileScriptMissing as exc:
            message = str(exc)
        # Assert
        assert str(bare) in message, (
            "the report must name the ROOT the path was derived from — "
            "without it the reader cannot tell which of the two roots the "
            f"caller held. Got {message!r}"
        )

    def test_an_unknown_doc_type_is_refused_by_the_leaf(
        self, project_root: Path
    ):
        # Arrange: no silent fall-back to manuscript, which would compile
        # the wrong document and report success.
        refusal = pytest.raises(ValueError)
        # Act / Assert
        with refusal:
            build_inner_cmd(project_root, "not-a-real-doc-type", {})


class TestAFailureStatesItsReason:
    """The dict the poller returns, which is what the panel renders."""

    def test_a_failed_full_compile_carries_an_error_key(self):
        # Arrange
        runner_result = dict(PROD_RC127)
        # Act
        final = build_final_result(runner_result, pdf_url=None)
        # Assert
        assert final.get("error"), (
            "handleFailed reads result.error and falls back to the generic "
            "'Compilation failed'; without this key the user is never told "
            "why."
        )

    def test_the_error_names_the_exit_code(self):
        # Arrange
        runner_result = dict(PROD_RC127)
        # Act
        final = build_final_result(runner_result, pdf_url=None)
        # Assert
        assert "127" in final["error"]

    def test_the_transcript_still_reaches_the_log_pane(self):
        # Arrange
        runner_result = dict(PROD_RC127)
        # Act
        final = build_final_result(runner_result, pdf_url=None)
        # Assert
        assert "No such file or directory" in final["log"]

    def test_a_tex_failure_headlines_the_engine_error(self):
        # Arrange: same precedence the preview path uses — the engine's
        # own "! ..." line beats the generic exit-code message.
        runner_result = dict(PROD_TEX_FAILURE)
        # Act
        final = build_final_result(runner_result, pdf_url=None)
        # Assert
        assert "Unicode character" in final["error"]

    def test_a_tex_failure_prefers_the_cause_over_the_epilogue(self):
        # Arrange
        runner_result = dict(PROD_TEX_FAILURE)
        # Act
        final = build_final_result(runner_result, pdf_url=None)
        # Assert
        assert "==> Fatal error" not in final["error"]

    def test_a_successful_compile_acquires_no_error(self):
        # Arrange
        runner_result = {
            "success": True,
            "returncode": 0,
            "stdout": "compiled",
            "stderr": "",
        }
        # Act
        final = build_final_result(runner_result, pdf_url="/pdf/manuscript.pdf")
        # Assert
        assert final.get("error") is None

    def test_a_successful_compile_keeps_its_pdf_url(self):
        # Arrange
        runner_result = {
            "success": True,
            "returncode": 0,
            "stdout": "compiled",
            "stderr": "",
        }
        # Act
        final = build_final_result(runner_result, pdf_url="/pdf/manuscript.pdf")
        # Assert
        assert final["output_pdf"] == "/pdf/manuscript.pdf"


class TestThePdfIsLookedForWhereItIsWritten:
    """The compiled PDF lands inside the workspace, not at the project root.

    The compile script resolves its own PROJECT_ROOT from
    ``$(dirname $0)/../..`` — the WORKSPACE — then writes
    ``./01_manuscript/manuscript.pdf`` relative to that
    (``config_manuscript.yaml``, ``paths.compiled_pdf``). So fixing only
    the script path would have produced a green compile with no PDF found.
    """

    def test_a_pdf_written_inside_the_workspace_is_found(
        self, project_root: Path
    ):
        # Arrange: where the script really writes it.
        pdf = workspace_dir(project_root) / "01_manuscript" / "manuscript.pdf"
        pdf.parent.mkdir(parents=True, exist_ok=True)
        pdf.write_bytes(b"%PDF-1.4\n")
        # Act
        found = locate_compiled_pdf(project_root)
        # Assert
        assert found == pdf, (
            "the workspace copy is what the compile script produces; not "
            "finding it turns a successful compile into 'no PDF'."
        )

    def test_nothing_is_found_when_no_pdf_was_written(
        self, project_root: Path
    ):
        # Arrange: control — the lookup must not report a phantom PDF, or
        # the assertion above would pass on an empty tree too.
        expected = None
        # Act
        found = locate_compiled_pdf(project_root)
        # Assert
        assert found is expected

    def test_a_project_root_pdf_is_still_found_for_legacy_projects(
        self, project_root: Path
    ):
        # Arrange: pre-workspace projects kept the PDF at the project root.
        pdf = project_root / "manuscript.pdf"
        pdf.write_bytes(b"%PDF-1.4\n")
        # Act
        found = locate_compiled_pdf(project_root)
        # Assert
        assert found == pdf


if __name__ == "__main__":
    import os

    pytest.main([os.path.abspath(__file__)])

# EOF
