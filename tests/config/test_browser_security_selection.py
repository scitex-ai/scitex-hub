"""Keep real renderer security controls in the admitted browser execution gate."""

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]


def test_browser_gate_executes_real_diagram_and_monaco_security_controls():
    workflow = yaml.safe_load((ROOT / ".github/workflows/e2e-mobile.yml").read_text())
    jobs = workflow["jobs"]
    steps = next(
        job["steps"]
        for job in jobs.values()
        if any(
            step.get("name") == "Run Playwright mobile tests"
            for step in job.get("steps", [])
        )
    )
    position = next(
        index
        for index, step in enumerate(steps)
        if step.get("name") == "Run Playwright mobile tests"
    )
    command = steps[position]["run"]
    for name in (
        "test_page_readiness_contract.py",
        "test_diagram_rendering_boundary.py",
        "test_monaco_sanitizer_boundary.py",
    ):
        relative = "tests/e2e/playwright/" + name
        assert command.count(relative) == 1 and (ROOT / relative).is_file()
    assert "--browser chromium" in command and "--timeout=120" in command
    before = "\n".join(step.get("run", "") for step in steps[:position])
    assert "npm install" in before and "npm run build" in before
    assert "playwright install --with-deps chromium" in before
