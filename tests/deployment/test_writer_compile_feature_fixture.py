#!/usr/bin/env python3
"""Hub's Writer compile fixture exercises the two PDF-text release gates."""

from __future__ import annotations

import importlib.util
import os
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURE = REPO_ROOT / "tests/deployment/fixtures/writer_compile_features"


def _load_writer_gate():
    candidates = [
        Path(os.environ["SCITEX_WRITER_SOURCE"])
        if "SCITEX_WRITER_SOURCE" in os.environ
        else None,
        REPO_ROOT / ".ci/scitex-writer",
        REPO_ROOT.parent / "scitex-writer",
        Path("/home/ywatanabe/proj/scitex-writer"),
    ]
    for root in candidates:
        if root is None:
            continue
        script = root / "scripts/python/check_compile_artifacts.py"
        if script.is_file():
            spec = importlib.util.spec_from_file_location("writer_compile_gate", script)
            assert spec is not None
            module = importlib.util.module_from_spec(spec)
            assert spec.loader is not None
            spec.loader.exec_module(module)
            return module
    raise AssertionError(
        "scitex-writer source checkout unavailable; set SCITEX_WRITER_SOURCE "
        "or run through the pytest-matrix canonical .ci/scitex-writer checkout"
    )


@pytest.fixture(scope="module")
def gate():
    return _load_writer_gate()


def _text(name: str) -> str:
    return (FIXTURE / "controls" / name).read_text(encoding="utf-8")


def _reports(gate, check, *args):
    reports = []
    check(*args, reports.append)
    return reports


def test_fixture_is_a_real_opted_in_writer_project():
    assert "signature_footer: true" in (FIXTURE / "config.yaml").read_text()
    assert "fixture_claim" in (FIXTURE / "00_shared/claims.json").read_text()
    assert r"\vclaim{fixture_claim}" in (FIXTURE / "01_manuscript/base.tex").read_text()


def test_positive_control_passes_both_feature_checks(gate):
    raw_tex = _text("compiled.tex")
    pdf_text = _text("positive.pdf.txt")

    assert _reports(gate, gate.check_signature_rendered, raw_tex, pdf_text) == []
    assert _reports(gate, gate.check_claim_placeholders, pdf_text) == []


def test_broken_signature_fails_only_signature_check(gate):
    raw_tex = _text("compiled.tex")
    pdf_text = _text("missing_signature.pdf.txt")

    signature_reports = _reports(gate, gate.check_signature_rendered, raw_tex, pdf_text)
    claim_reports = _reports(gate, gate.check_claim_placeholders, pdf_text)

    assert len(signature_reports) == 1
    assert claim_reports == []


def test_broken_claim_fails_only_claim_check(gate):
    raw_tex = _text("compiled.tex")
    pdf_text = _text("claim_placeholder.pdf.txt")

    signature_reports = _reports(gate, gate.check_signature_rendered, raw_tex, pdf_text)
    claim_reports = _reports(gate, gate.check_claim_placeholders, pdf_text)

    assert signature_reports == []
    assert len(claim_reports) == 1
