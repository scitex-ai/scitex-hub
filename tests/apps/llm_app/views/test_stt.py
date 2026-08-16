#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for apps/infra/llm_app/views/stt.py

Regression guard for a shipped product bug: the endpoint transcribed every
request as English. Two independent causes, both covered here:

  1. ``--language en`` was hardcoded into the whisper invocation.
  2. The default model was ``ggml-base.en`` — an English-ONLY weight file,
     which cannot transcribe Japanese even once the flag is parameterised.

Cause 1 is gone because hub no longer builds the whisper command at all; it
delegates to ``scitex_audio.transcribe`` and passes ``language`` through.
Cause 2 is what these tests pin, because it is the one a future edit to
``_KNOWN_MODELS`` could silently reintroduce.

No-mock policy: model resolution is pure filesystem work, so these tests
create real files in a real temporary directory and pass that directory in
explicitly. Nothing is patched and no global environment variable is mutated.
"""

from apps.infra.llm_app.views.stt import _DEFAULT_MODEL, _resolve_model


def test_default_model_is_not_english_only():
    # Arrange
    default_model = _DEFAULT_MODEL

    # Act
    is_english_only = default_model.endswith(".en")

    # Assert
    assert is_english_only is False


def test_resolve_model_prefers_multilingual_over_english_only(tmp_path):
    # Arrange
    (tmp_path / "ggml-base.bin").write_bytes(b"weights")
    (tmp_path / "ggml-base.en.bin").write_bytes(b"weights")

    # Act
    resolved = _resolve_model(None, models_dir=str(tmp_path))

    # Assert
    assert resolved.endswith("ggml-base.bin")


def test_resolve_model_honours_explicitly_requested_model(tmp_path):
    # Arrange
    (tmp_path / "ggml-tiny.en.bin").write_bytes(b"weights")

    # Act
    resolved = _resolve_model("ggml-tiny.en", models_dir=str(tmp_path))

    # Assert
    assert resolved.endswith("ggml-tiny.en.bin")


def test_resolve_model_returns_none_for_missing_model(tmp_path):
    # Arrange
    absent_model_name = "ggml-not-installed"

    # Act
    resolved = _resolve_model(absent_model_name, models_dir=str(tmp_path))

    # Assert
    assert resolved is None


def test_resolve_model_returns_none_for_empty_directory(tmp_path):
    # Arrange
    empty_models_dir = str(tmp_path)

    # Act
    resolved = _resolve_model(None, models_dir=empty_models_dir)

    # Assert
    assert resolved is None
