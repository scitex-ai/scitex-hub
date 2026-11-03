"""The scoped SDK gate must reject crashed, truncated and malformed CLI output."""

import importlib.util
import json
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location(
    "owned_sdk_ui_gate", ROOT / ".github/ci/check_sdk_ui_rules.py"
)
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)
COVERAGE = json.dumps({"kind": "coverage", "not_inspected": []})


def test_real_sdk_cli_proves_the_gate_distinguishes_clean_input_and_authored_headers(
    tmp_path,
):
    source = tmp_path / "native.html"
    source.write_text('<div data-stx-app-header data-app-title="Owned fixture"></div>')
    clean = subprocess.run(
        ["scitex-sdk", "ui", "lint", "--json", str(source)],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert gate.checked_findings(clean.returncode, clean.stdout, clean.stderr) == []
    source.write_text('<header class="owned-header">Owned fixture</header>')
    refused = subprocess.run(
        ["scitex-sdk", "ui", "lint", "--json", str(source)],
        capture_output=True,
        text=True,
        timeout=60,
    )
    rows = gate.checked_findings(refused.returncode, refused.stdout, refused.stderr)
    assert refused.returncode == 1 and any(row["rule"] == "STX-UI108" for row in rows)


@pytest.mark.parametrize(
    "status,stdout,stderr",
    [
        (2, COVERAGE, ""),
        (1, "", ""),
        (1, COVERAGE, ""),
        (0, "not JSON", ""),
        (0, COVERAGE, "Traceback: partial scan"),
        (0, COVERAGE + "\n" + COVERAGE, ""),
        (0, COVERAGE + '\n{"kind":"unexpected"}', ""),
        (0, COVERAGE + '\n{"rule":"STX-UI108","path":"fixture.html","line":1}', ""),
    ],
)
def test_incomplete_or_inconsistent_scans_never_become_green(status, stdout, stderr):
    with pytest.raises(ValueError):
        gate.checked_findings(status, stdout, stderr)
