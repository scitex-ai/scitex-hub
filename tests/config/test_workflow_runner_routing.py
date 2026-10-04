"""Hub delegates full validation and preserves fail-closed required checks.

The shared CI repository tests the complete job bodies, fork fences,
non-root containers and CPU limits. Hub checks its calls and remaining
inline jobs; no external source is fetched during these tests.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
import yaml

WORKFLOWS = Path(__file__).resolve().parents[2] / ".github" / "workflows"
FORK_PREDICATE = "github.event.pull_request.head.repo.full_name != github.repository"
SHARED_GATES = {
    "pytest-matrix-on-ubuntu-py3-11-3-12-3-13.yml": "hub-pytest-matrix.yml",
    "cli-import-smoke-on-ubuntu-latest.yml": "hub-cli-import-smoke.yml",
    "scitex-hub-quality-audit-on-ubuntu-latest.yml": "hub-quality-audit.yml",
    "check-command-v-args.yml": "hub-command-v-guard.yml",
    "check-absolute-symlinks.yml": "hub-symlink-guard.yml",
    "rtd-sphinx-build-on-ubuntu-latest.yml": "hub-sphinx-build.yml",
    "tests.yml": "hub-custom-tests.yml",
}
REQUIRED_CONTEXTS_KEPT = {
    ("pytest-matrix-on-ubuntu-py3-11-3-12-3-13.yml", "required-pytest"):
        "pytest-matrix-on-ubuntu-py${{ matrix.python-version }}",
    ("cli-import-smoke-on-ubuntu-latest.yml", "required-cli"):
        "cli-import-smoke-on-ubuntu-latest",
    ("scitex-hub-quality-audit-on-ubuntu-latest.yml", "required-audit"): "audit",
}


def _load(path: Path) -> dict:
    return yaml.safe_load(path.read_text())


def _triggers(workflow: dict) -> dict:
    on = workflow.get("on", workflow.get(True)) or {}
    return on if isinstance(on, dict) else dict.fromkeys(on)


def _scan_pr_routing():
    inline, delegated, scanned = [], set(), 0
    for path in sorted(WORKFLOWS.glob("*.y*ml")):
        scanned += 1
        workflow = _load(path)
        if "pull_request" not in _triggers(workflow):
            continue
        for key, job in (workflow.get("jobs") or {}).items():
            if path.name in SHARED_GATES and key == "validation":
                delegated.add(path.name)
            runs_on = str(job.get("runs-on", ""))
            checks_out = any(
                "actions/checkout" in str(step.get("uses", ""))
                for step in (job.get("steps") or [])
            )
            if ("self-hosted" in runs_on or "scitex-docker" in runs_on) and checks_out:
                inline.append((path.name, key, job))
    return inline, delegated, scanned


def test_the_scan_examined_the_workflows_and_all_seven_shared_pr_gates():
    _inline, delegated, scanned = _scan_pr_routing()
    assert scanned >= len(SHARED_GATES)
    assert delegated == set(SHARED_GATES)


@pytest.mark.parametrize("filename,callee", sorted(SHARED_GATES.items()))
def test_validation_reaches_the_fixed_shared_gate_without_arbitrary_inputs(
    filename, callee
):
    job = _load(WORKFLOWS / filename)["jobs"]["validation"]
    expected = {"uses": "scitex-ai/.github/.github/workflows/" + callee + "@main"}
    if filename == "pytest-matrix-on-ubuntu-py3-11-3-12-3-13.yml":
        expected["secrets"] = {"CODECOV_TOKEN": "${{ secrets.CODECOV_TOKEN }}"}
    assert job == expected


def test_remaining_inline_pr_jobs_route_forks_to_hosted_before_checkout():
    inline, _delegated, _scanned = _scan_pr_routing()
    for filename, key, job in inline:
        runs_on = str(job["runs-on"])
        guard_if = str(job["steps"][0].get("if", ""))
        assert FORK_PREDICATE in runs_on and "ubuntu-latest" in runs_on, (filename, key)
        assert FORK_PREDICATE in guard_if, (filename, key)
        assert "runner.environment == 'self-hosted'" in guard_if, (filename, key)


def test_remaining_inline_docker_jobs_preserve_non_root_isolation():
    inline, _delegated, _scanned = _scan_pr_routing()
    for filename, key, job in inline:
        if "scitex-docker" not in str(job["runs-on"]):
            continue
        container = job.get("container") or {}
        assert "buildpack-deps" in str(container.get("image", "")), (filename, key)
        assert "--user 1000:1000" in str(container.get("options", "")), (filename, key)


@pytest.mark.parametrize("filename,key", sorted(REQUIRED_CONTEXTS_KEPT))
@pytest.mark.parametrize(
    "validation_result,expected_exit",
    [("success", 0), ("failure", 1), ("cancelled", 1), ("skipped", 1), ("", 1)],
)
def test_required_context_names_and_actual_success_bridges_are_preserved(
    filename, key, validation_result, expected_exit
):
    job = _load(WORKFLOWS / filename)["jobs"][key]
    assert job["name"] == REQUIRED_CONTEXTS_KEPT[(filename, key)]
    assert job["needs"] == "validation" and job["if"] == "always()"
    assert job["runs-on"] == "ubuntu-latest" and job["permissions"] == {}
    assert len(job["steps"]) == 1
    step = job["steps"][0]
    assert set(step) == {"name", "env", "run"}
    assert step["env"] == {"VALIDATION_RESULT": "${{ needs.validation.result }}"}
    actual = subprocess.run(
        ["/bin/bash", "-c", step["run"]],
        env={"PATH": "/usr/bin:/bin", "VALIDATION_RESULT": validation_result},
        capture_output=True,
        timeout=2,
        check=False,
    )
    assert actual.returncode == expected_exit
