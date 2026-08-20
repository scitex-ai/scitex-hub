#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""A failed preview compile must tell the user WHY it failed.

THE DEFECT, measured on production 2026-08-16. The operator hit

    Starting preview compilation...
    ✗ Preview compilation failed: Preview compilation failed

The doubled string is itself the evidence: compilation-preview.ts does

    throw new Error(result?.error || "Preview compilation failed")

so ``result.error`` was absent and the client fell back to its own literal,
which the catch block then prefixed with the same words. The user is told
that the thing that failed, failed.

The server was never confused. Running the identical compile inside the
production container returned:

    success   = False
    exit_code = 12
    message   = 'Compilation failed with exit code 12'
    error     = None          <- what the UI reads
    log       = <absent>      <- what the UI reads
    stdout    = '... ! LaTeX Error: Unicode character 」 (U+300D)
                       not set up for use with LaTeX. ... l.28 」
                   !  ==> Fatal error occurred, no output PDF file produced!'

The cause was one stray 」 on the last line of abstract.tex, which pdflatex
cannot typeset. A one-character fix, invisible for as long as the reason
could not reach the screen.

So this is a CONTRACT defect, not a LaTeX one: compile_preview() returns
``message``/``errors``/``stderr``/``stdout``/``exit_code``, the front-end
reads ``error``/``log``, and nothing bridged the two. compile_manuscript()
in the same class documents ``{success, output_pdf, log, error}`` as the
return shape, so compile_preview was also breaking its sibling's contract.

WHAT THIS GUARDS. Not the wording of any message — that would assert the
artefact the author edited. It pins the property that matters: for a
failure the engine explained, the explanation is present in the key the UI
actually reads. The fixture below is the real production payload, so these
fail if _ensure_error_and_log is removed, if it stops preferring the
engine's own error line, or if the front-end's key names drift away from it.
"""

from __future__ import annotations

import pytest

from apps.workspace.writer_app.services.writer.compilation import (
    _ensure_error_and_log,
)

# The exact stdout tail captured from scitex-hub-prod-django-1 on 2026-08-16.
PROD_STDOUT = """*geometry* driver: auto-detecting
*geometry* detected driver: pdftex

! LaTeX Error: Unicode character 」 (U+300D)
               not set up for use with LaTeX.

See the LaTeX manual or LaTeX Companion for explanation.
Type  H <return>  for immediate help.
 ...
l.28 」

!  ==> Fatal error occurred, no output PDF file produced!
"""

PROD_STDERR = (
    "Latexmk: ====List of undefined refs and citations:\n"
    "  ! LaTeX Error: Unicode character 」 (U+300D)\n"
    "Latexmk: If appropriate, the -f option can be used to get latexmk\n"
    "  to try to force complete processing.\n"
)


@pytest.fixture
def prod_failure() -> dict:
    """The observed shape: a real reason, and neither key the UI reads."""
    return {
        "success": False,
        "exit_code": 12,
        "message": "Compilation failed with exit code 12",
        "errors": [],
        "warnings": [],
        "output_pdf": None,
        "stdout": PROD_STDOUT,
        "stderr": PROD_STDERR,
    }


class TestCompileErrorReachesTheUser:
    @pytest.mark.guards(
        defect=(
            "compile_preview returns message/stderr/exit_code but the Writer UI "
            "reads result.error, so a failed compile showed 'Preview compilation "
            "failed' with no cause and hid a one-character LaTeX error"
        )
    )
    def test_failure_carries_a_non_empty_error(self, prod_failure):
        # Arrange
        raw = prod_failure

        # Act
        result = _ensure_error_and_log(raw)

        # Assert
        assert result["error"], "a failure must carry a non-empty `error`"

    @pytest.mark.guards(
        defect=(
            "the LaTeX engine named the cause in stdout, but nothing copied it "
            "into result.error, so the user could not see which character broke "
            "the compile"
        )
    )
    def test_engine_error_line_reaches_the_key_the_ui_reads(self, prod_failure):
        # Arrange
        raw = prod_failure

        # Act
        result = _ensure_error_and_log(raw)

        # Assert
        assert "Unicode character" in result["error"], (
            f"the engine named the cause; it must survive into `error`. "
            f"got: {result['error']!r}"
        )

    @pytest.mark.guards(
        defect=(
            "a failed compile returned no `log`, so the Writer log pane rendered "
            "empty even though stdout/stderr held the full LaTeX transcript"
        )
    )
    def test_transcript_reaches_the_log_pane(self, prod_failure):
        # Arrange
        raw = prod_failure

        # Act
        result = _ensure_error_and_log(raw)

        # Assert
        assert "Fatal error occurred" in result["log"]

    @pytest.mark.guards(
        defect=(
            "TeX hard-wraps its diagnostics, so reporting only the first line "
            "cut the message at 'Unicode character 」 (U+300D)' and dropped the "
            "half that says what is actually wrong with it"
        )
    )
    def test_wrapped_continuation_is_folded_back_in(self, prod_failure):
        # Arrange
        raw = prod_failure

        # Act
        result = _ensure_error_and_log(raw)

        # Assert — the sentence finishes, rather than stopping mid-clause.
        assert "not set up for use with LaTeX" in result["error"]

    def test_prefers_the_cause_over_the_epilogue(self, prod_failure):
        """'! ==> Fatal error occurred' says a failure happened, not why."""
        # Arrange
        raw = prod_failure

        # Act
        result = _ensure_error_and_log(raw)

        # Assert
        assert "==> Fatal error" not in result["error"]

    def test_falls_back_to_message_when_the_engine_said_nothing(self):
        # Arrange — a failure with no parseable TeX error at all.
        raw = {
            "success": False,
            "exit_code": 1,
            "message": "Compilation failed with exit code 1",
            "stdout": "",
            "stderr": "",
        }

        # Act
        result = _ensure_error_and_log(raw)

        # Assert — never empty; the user always gets something to act on.
        assert result["error"] == "Compilation failed with exit code 1"

    def test_never_overwrites_an_error_the_caller_already_set(self):
        # Arrange
        raw = {"success": False, "error": "Invalid session", "stdout": PROD_STDOUT}

        # Act
        result = _ensure_error_and_log(raw)

        # Assert
        assert result["error"] == "Invalid session"

    def test_success_acquires_no_error(self):
        # Arrange
        raw = {"success": True, "output_pdf": "/tmp/x.pdf", "stdout": "ok"}

        # Act
        result = _ensure_error_and_log(raw)

        # Assert
        assert result.get("error") is None

    def test_success_still_gets_its_transcript(self):
        # Arrange
        raw = {"success": True, "output_pdf": "/tmp/x.pdf", "stdout": "ok"}

        # Act
        result = _ensure_error_and_log(raw)

        # Assert
        assert result["log"] == "ok"
