"""Contract for bounded, fail-fast product screenshot capture."""

from pathlib import Path

import yaml

WORKFLOW = Path(".github/workflows/screenshots.yml")


def _capture_script():
    workflow = yaml.safe_load(WORKFLOW.read_text())
    steps = workflow["jobs"]["screenshots"]["steps"]
    return next(step["run"] for step in steps if step["name"] == "Capture screenshots")


def test_capture_process_has_external_hard_deadline():
    script = _capture_script()

    assert "timeout --signal=TERM --kill-after=30s 12m python -m pytest" in script


def test_capture_stops_after_first_failure():
    assert "--maxfail=1" in _capture_script()
