#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for apps/workspace/writer_app/services/writer/compilation.py

Focused on ``_coerce_compile_result_to_dict``, the helper introduced by
the scitex-writer 2.17.5 pin-bump to translate the upstream return type
change (raw ``dict`` -> ``CompilationResult`` dataclass, G1) back into a
JSON-serialisable ``dict`` for the Django view + UI contract.

The wider ``CompilationMixin.compile_preview`` itself drives latex
subprocesses against a real project directory; that path is exercised
by the E2E browser suite. Here we pin the small, deterministic helper
that sits between scitex-writer and the JsonResponse boundary.
"""

from __future__ import annotations

import dataclasses
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Fixtures — real dataclasses + plain dicts; no mocks per repo no-mock policy.
# ---------------------------------------------------------------------------


@dataclasses.dataclass
class _FakeCompilationResult:
    """Minimal stand-in for scitex_writer 2.17.5 ``CompilationResult``.

    Hand-rolled (rather than imported from scitex-writer) so the test
    survives independent of the installed scitex-writer version.
    """

    success: bool
    exit_code: int
    stdout: str = ""
    stderr: str = ""
    output_pdf: Path | None = None
    diff_pdf: Path | None = None
    log_file: Path | None = None
    duration: float = 0.0


@pytest.fixture
def dataclass_result():
    return _FakeCompilationResult(
        success=True,
        exit_code=0,
        stdout="latexmk OK",
        stderr="",
        output_pdf=Path("/tmp/preview/abstract-light.pdf"),
        log_file=Path("/tmp/preview/abstract-light.log"),
        duration=1.25,
    )


@pytest.fixture
def legacy_dict_result():
    return {
        "success": True,
        "output_pdf": "/tmp/preview/abstract-light.pdf",
        "temp_dir": "/tmp/preview",
        "color_mode": "light",
        "log": "ok",
        "message": "Content compiled successfully",
    }


# ---------------------------------------------------------------------------
# Behaviour tests — one assertion per test (STX-TQ007).
# ---------------------------------------------------------------------------


class TestCoerceCompileResultDataclass:
    """When the upstream returns a CompilationResult dataclass."""

    def test_dataclass_input_returns_dict(self, dataclass_result):
        # Arrange
        from apps.workspace.writer_app.services.writer.compilation import (
            _coerce_compile_result_to_dict,
        )

        # Act
        result = _coerce_compile_result_to_dict(dataclass_result)

        # Assert
        assert isinstance(result, dict)

    def test_dataclass_success_field_preserved(self, dataclass_result):
        # Arrange
        from apps.workspace.writer_app.services.writer.compilation import (
            _coerce_compile_result_to_dict,
        )

        # Act
        result = _coerce_compile_result_to_dict(dataclass_result)

        # Assert
        assert result["success"] is True

    def test_dataclass_exit_code_field_preserved(self, dataclass_result):
        # Arrange
        from apps.workspace.writer_app.services.writer.compilation import (
            _coerce_compile_result_to_dict,
        )

        # Act
        result = _coerce_compile_result_to_dict(dataclass_result)

        # Assert
        assert result["exit_code"] == 0

    def test_dataclass_output_pdf_coerced_to_str(self, dataclass_result):
        # Arrange
        from apps.workspace.writer_app.services.writer.compilation import (
            _coerce_compile_result_to_dict,
        )

        # Act
        result = _coerce_compile_result_to_dict(dataclass_result)

        # Assert
        assert result["output_pdf"] == "/tmp/preview/abstract-light.pdf"

    def test_dataclass_log_file_coerced_to_str(self, dataclass_result):
        # Arrange
        from apps.workspace.writer_app.services.writer.compilation import (
            _coerce_compile_result_to_dict,
        )

        # Act
        result = _coerce_compile_result_to_dict(dataclass_result)

        # Assert
        assert result["log_file"] == "/tmp/preview/abstract-light.log"

    def test_dataclass_unset_optional_path_stays_none(self, dataclass_result):
        # Arrange — ``diff_pdf`` defaults to None in the fixture; the helper
        # must not turn None into the string "None".
        from apps.workspace.writer_app.services.writer.compilation import (
            _coerce_compile_result_to_dict,
        )

        # Act
        result = _coerce_compile_result_to_dict(dataclass_result)

        # Assert
        assert result["diff_pdf"] is None


class TestCoerceCompileResultDict:
    """When the upstream returns a raw dict (pre-2.17.5 shape)."""

    def test_dict_input_returns_dict(self, legacy_dict_result):
        # Arrange
        from apps.workspace.writer_app.services.writer.compilation import (
            _coerce_compile_result_to_dict,
        )

        # Act
        result = _coerce_compile_result_to_dict(legacy_dict_result)

        # Assert
        assert isinstance(result, dict)

    def test_dict_input_preserves_existing_fields(self, legacy_dict_result):
        # Arrange
        from apps.workspace.writer_app.services.writer.compilation import (
            _coerce_compile_result_to_dict,
        )

        # Act
        result = _coerce_compile_result_to_dict(legacy_dict_result)

        # Assert
        assert result["success"] is True

    def test_dict_input_is_a_copy_not_the_same_instance(self, legacy_dict_result):
        # Arrange — mutating ``result`` inside compile_api (e.g. rewriting
        # output_pdf to a served URL) must not mutate caller-side state.
        from apps.workspace.writer_app.services.writer.compilation import (
            _coerce_compile_result_to_dict,
        )

        # Act
        result = _coerce_compile_result_to_dict(legacy_dict_result)

        # Assert
        assert result is not legacy_dict_result


if __name__ == "__main__":
    import os

    pytest.main([os.path.abspath(__file__)])

# EOF
