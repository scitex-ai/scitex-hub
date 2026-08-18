#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Full compilation must find its script, and say why when it fails.

Measured on live scitex.ai 2026-08-17 (operator report, Telegram 3465
「full compilation も走らない」). Preview compiled fine — HTTP 200 in
3.05s, a real 5094-byte PDF written and fetchable — so the TeX toolchain
and the sandbox were healthy. Full compilation returned, for every
user::

    POST .../compile_full/            -> 200 {"job_id": ...}
    GET  .../compilation/status/<id>/ ->
      {"status":"failed",
       "result":{"success":false,"returncode":127},
       "log":"/usr/bin/bash: /workspace/scripts/shell/compile_manuscript.sh:
              No such file or directory"}

Two separate defects, one symptom:

1. ``run_compilation_async`` hardcoded ``scripts/shell/…`` and exec'd
   ``bash /workspace/<that>``, while the apptainer runner binds the
   PROJECT ROOT as ``/workspace`` and the scripts are vendored inside
   ``<project>/.scitex/writer/``. One level too high — rc 127.

2. ``final_result`` was built with no ``error`` key at all, while
   ``compilation-queue.ts::handleFailed`` reads
   ``data.result?.error || "Compilation failed"``. So even once the
   script is found, a real failure would still announce itself with a
   generic four-word string.

These tests assert both at the level that failed: the argv actually
handed to the sandbox, and the dict actually handed to the poller.
No HTTP, no DB, no apptainer — those were all working.
"""

from pathlib import Path

import pytest

from apps.infra.project_app.services.writer_workspace_layout import (
    WRITER_WORKSPACE_RELPATH,
    get_compile_script_relpath,
)
from apps.workspace.writer_app.views.editor.api.compilation_full_job import (
    build_final_result,
    build_inner_cmd,
)

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


class TestTheScriptPathReachesTheWorkspace:
    """The argv, which is what bash actually resolved."""

    def test_the_command_targets_the_writer_workspace(self):
        # Arrange
        expected = f"/workspace/{get_compile_script_relpath('manuscript')}"
        # Act
        argv = build_inner_cmd("manuscript", {})
        # Assert
        assert argv[1] == expected, (
            f"full compile execs {argv[1]!r}; the script lives under "
            f"{WRITER_WORKSPACE_RELPATH}/ inside the bound project root."
        )

    def test_the_command_is_not_the_path_that_returned_127(self):
        # Arrange: the exact string prod's bash could not find. This is
        # the positive control for the test above — it fails if someone
        # reverts to assembling the path at the project root, which
        # asserting only "starts with /workspace/" would not catch.
        forbidden = BROKEN_PROD_ARGV
        # Act
        argv = build_inner_cmd("manuscript", {})
        # Assert
        assert argv[1] != forbidden, (
            "the pre-fix path is back; this is the argv that produced "
            "returncode 127 for every user on scitex.ai."
        )

    def test_bash_is_still_the_interpreter(self):
        # Arrange
        expected = "bash"
        # Act
        argv = build_inner_cmd("manuscript", {})
        # Assert
        assert argv[0] == expected

    @pytest.mark.parametrize("doc_type", ["manuscript", "supplementary", "revision"])
    def test_every_doc_type_resolves_inside_the_workspace(self, doc_type):
        # Arrange
        prefix = f"/workspace/{WRITER_WORKSPACE_RELPATH}/"
        # Act
        argv = build_inner_cmd(doc_type, {})
        # Assert
        assert argv[1].startswith(prefix)

    def test_the_flags_still_follow_the_script(self):
        # Arrange: the path fix must not disturb the option plumbing.
        options = {"no_figs": True, "color_mode": "dark"}
        # Act
        argv = build_inner_cmd("manuscript", options)
        # Assert
        assert argv[2:] == ["--no-figs", "--color-mode", "dark"]


class TestTheScriptPathIsRealOnDisk:
    """Reality control: the value must address a file that can exist.

    A path assertion that only compares two strings passes even when both
    are wrong. This lays out the directory scitex-writer actually vendors
    and checks the resolved path lands on the script.
    """

    def test_the_relative_path_hits_a_real_file(self, tmp_path: Path):
        # Arrange: the layout ensure_workspace() creates.
        script = (
            tmp_path
            / WRITER_WORKSPACE_RELPATH
            / "scripts"
            / "shell"
            / "compile_manuscript.sh"
        )
        script.parent.mkdir(parents=True)
        script.write_text("#!/bin/bash\necho compiled\n", encoding="utf-8")
        # Act
        resolved = tmp_path / get_compile_script_relpath("manuscript")
        # Assert
        assert resolved.is_file(), (
            f"{resolved} does not exist under a REAL workspace layout — "
            "the constant and the vendored tree disagree."
        )

    def test_the_broken_prod_path_does_not_hit_that_file(self, tmp_path: Path):
        # Arrange: same tree, positive control for the check above.
        script = (
            tmp_path
            / WRITER_WORKSPACE_RELPATH
            / "scripts"
            / "shell"
            / "compile_manuscript.sh"
        )
        script.parent.mkdir(parents=True)
        script.write_text("#!/bin/bash\necho compiled\n", encoding="utf-8")
        # Act
        broken = tmp_path / BROKEN_PROD_ARGV.removeprefix("/workspace/")
        # Assert
        assert not broken.exists(), (
            "the pre-fix path resolves under a real workspace layout, so "
            "this control proves nothing — check the fixture."
        )


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
    ``./01_manuscript/manuscript.pdf`` relative to that. So fixing only
    the script path would have produced a green compile with no PDF found.
    """

    def test_the_compiled_pdf_path_is_inside_the_workspace(self, tmp_path: Path):
        # Arrange
        from apps.infra.project_app.services.writer_workspace_layout import (
            get_compiled_pdf_path,
        )

        expected = (
            tmp_path / WRITER_WORKSPACE_RELPATH / "01_manuscript" / "manuscript.pdf"
        )
        # Act
        resolved = get_compiled_pdf_path(tmp_path)
        # Assert
        assert resolved == expected


if __name__ == "__main__":
    import os

    pytest.main([os.path.abspath(__file__)])

# EOF
