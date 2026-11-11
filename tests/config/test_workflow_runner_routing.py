#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: tests/config/test_workflow_runner_routing.py
"""Fork-authored pull requests never execute on our self-hosted runners.

Organization CPU jobs use shared authorization with explicit registered
runner destinations. Other native jobs retain explicit fork routing. Any job
that checks out pull-request code on persistent hardware must send forks to
hosted CI and refuse before checkout if a fork still lands self-hosted.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

WORKFLOWS = Path(__file__).resolve().parents[2] / ".github" / "workflows"
FORK_PREDICATE = "github.event.pull_request.head.repo.full_name != github.repository"
REQUIRED_CONTEXTS_KEPT = {
    (
        "pytest-matrix-on-ubuntu-py3-11-3-12-3-13.yml",
        "test",
    ): "pytest-matrix-on-ubuntu-py${{ matrix.python-version }}",
    (
        "cli-import-smoke-on-ubuntu-latest.yml",
        "cli-import-smoke",
    ): "cli-import-smoke-on-ubuntu-latest",
    # No `name:`, so the required context is the job key, "audit".
    ("scitex-hub-quality-audit-on-ubuntu-latest.yml", "audit"): None,
}


def _load(path: Path) -> dict:
    return yaml.safe_load(path.read_text())


def _triggers(workflow: dict) -> dict:
    # PyYAML reads the bare key `on` as boolean True.
    on = workflow.get("on", workflow.get(True)) or {}
    return on if isinstance(on, dict) else dict.fromkeys(on)


def _shared_admission_routes_forks(filename: str, job: dict) -> bool:
    """Admit only the shared authorization gate with explicit destinations."""
    workflow = _load(WORKFLOWS / filename)
    admission = workflow["jobs"].get("runner-admission") or {}
    requested = (admission.get("with") or {}).get("runs_on")
    if admission != {
        "uses": "scitex-ai/.github/.github/workflows/runner-admission.yml@main",
        "permissions": {},
        "with": {"runs_on": requested},
    } or "runner-admission" not in (
        [job.get("needs")]
        if isinstance(job.get("needs"), str)
        else (job.get("needs") or [])
    ):
        return False
    try:
        native = json.dumps(
            {"group": "Organization", "labels": json.loads(requested)},
            separators=(",", ":"),
        )
    except (TypeError, ValueError):
        return False
    expected = (
        "${{ needs.runner-admission.outputs.native_authorized == 'true' "
        f"&& fromJSON('{native}') || fromJSON('[\"ubuntu-latest\"]') "
        "}}"
    )
    return " ".join(str(job["runs-on"]).split()) == expected


def _self_hosted_pr_jobs():
    for path in sorted(WORKFLOWS.glob("*.y*ml")):
        workflow = _load(path)
        if "pull_request" not in _triggers(workflow):
            continue
        for key, job in (workflow.get("jobs") or {}).items():
            runs_on = str(job.get("runs-on", ""))
            steps = job.get("steps") or []
            checks_out = any(
                "actions/checkout" in str(step.get("uses", "")) for step in steps
            )
            if ("self-hosted" in runs_on or "scitex-docker" in runs_on) and checks_out:
                yield pytest.param(path.name, key, job, id=f"{path.name}::{key}")


SELF_HOSTED_PR_JOBS = list(_self_hosted_pr_jobs())


def test_the_scan_found_the_routed_jobs():
    # Arrange
    jobs = SELF_HOSTED_PR_JOBS
    # Act
    count = len(jobs)
    # Assert
    assert count >= 5, f"only {count} self-hosted PR jobs found; the scan is vacuous"


@pytest.mark.parametrize("filename,key,job", SELF_HOSTED_PR_JOBS)
def test_fork_prs_are_routed_to_hosted(filename, key, job):
    # Arrange
    runs_on = str(job["runs-on"])
    # Act
    routes_forks = (
        FORK_PREDICATE in runs_on and "ubuntu-latest" in runs_on
    ) or _shared_admission_routes_forks(filename, job)
    # Assert
    assert routes_forks, (
        f"{filename}::{key} checks out PR code on a self-hosted runner without "
        "sending fork PRs to ubuntu-latest in runs-on."
    )


@pytest.mark.parametrize("filename,key,job", SELF_HOSTED_PR_JOBS)
def test_fork_guard_is_the_first_step(filename, key, job):
    # Arrange
    first = job["steps"][0]
    # Act
    guard_if = str(first.get("if", ""))
    # Assert
    assert (
        FORK_PREDICATE in guard_if and "runner.environment == 'self-hosted'" in guard_if
    ), f"{filename}::{key} must refuse fork code on self-hosted before checkout."


DOCKER_JOBS = [
    p for p in SELF_HOSTED_PR_JOBS if "scitex-docker" in str(p.values[2]["runs-on"])
]


def test_the_docker_scan_found_the_suites():
    # Arrange
    jobs = DOCKER_JOBS
    # Act
    count = len(jobs)
    # Assert
    assert count >= 3, f"only {count} scitex-docker jobs found; the scan is vacuous"


@pytest.mark.parametrize("filename,key,job", DOCKER_JOBS)
def test_docker_jobs_run_in_a_non_root_job_container(filename, key, job):
    # Arrange
    container = job.get("container") or {}
    # Act
    image, options = str(container.get("image", "")), str(container.get("options", ""))
    # Assert
    assert "buildpack-deps" in image and "--user 1000:1000" in options, (
        f"{filename}::{key} runs on a persistent scitex-docker host outside a "
        "non-root job container, so the suite can read the runner user's $HOME."
    )


@pytest.mark.parametrize("filename,key", sorted(REQUIRED_CONTEXTS_KEPT))
def test_required_check_job_names_are_unchanged(filename, key):
    # Arrange
    job = _load(WORKFLOWS / filename)["jobs"][key]
    # Act
    name = job.get("name")
    # Assert
    assert name == REQUIRED_CONTEXTS_KEPT[(filename, key)], (
        f"{filename}::{key} name changed to {name!r}; branch protection requires "
        "the check context by this exact name."
    )


# EOF


def test_cli_smoke_uses_shared_authorization_and_explicit_destinations():
    # Arrange
    jobs = _load(WORKFLOWS / "cli-import-smoke-on-ubuntu-latest.yml")["jobs"]
    job = jobs["cli-import-smoke"]
    expected = """${{
        needs.runner-admission.outputs.native_authorized == 'true'
        && fromJSON('{"group":"Organization","labels":["self-hosted","Linux","X64","scitex-org-cpu"]}')
        || fromJSON('["ubuntu-latest"]')
    }}"""
    # Act
    selected = (job.get("needs"), " ".join(job["runs-on"].split()))
    # Assert
    assert selected == ("runner-admission", " ".join(expected.split()))


def test_cli_smoke_requests_the_organization_cpu_quarantine_boundary():
    # Arrange
    jobs = _load(WORKFLOWS / "cli-import-smoke-on-ubuntu-latest.yml")["jobs"]
    # Act
    admission = jobs.get("runner-admission")
    # Assert
    assert admission == {
        "uses": "scitex-ai/.github/.github/workflows/runner-admission.yml@main",
        "permissions": {},
        "with": {"runs_on": '["self-hosted","Linux","X64","scitex-org-cpu"]'},
    }


def test_cli_smoke_keeps_its_fork_refusal_before_checkout():
    # Arrange
    jobs = _load(WORKFLOWS / "cli-import-smoke-on-ubuntu-latest.yml")["jobs"]
    # Act
    first = jobs["cli-import-smoke"]["steps"][0]
    # Assert
    assert (FORK_PREDICATE in first.get("if", "")) and (
        "runner.environment == 'self-hosted'" in first["if"]
    )


@pytest.mark.parametrize(
    "change",
    ["wrong-provider", "missing-dependency", "broad-authorization", "unguarded"],
)
def test_shared_admission_contract_rejects_bypasses(tmp_path, change):
    # Arrange
    workflow = _load(WORKFLOWS / "cli-import-smoke-on-ubuntu-latest.yml")
    job = workflow["jobs"]["cli-import-smoke"]
    if change == "wrong-provider":
        workflow["jobs"]["runner-admission"]["uses"] = "outsider/repo/workflow@main"
    elif change == "missing-dependency":
        job.pop("needs")
    elif change == "broad-authorization":
        job["runs-on"] = job["runs-on"].replace("== 'true'", "!= 'false'")
    else:
        job["runs-on"] = ["self-hosted", "Linux", "X64", "scitex-org-cpu"]
    path = tmp_path / "workflow.yml"
    path.write_text(yaml.safe_dump(workflow))
    # Act
    routed = _shared_admission_routes_forks(str(path), job)
    # Assert
    assert not routed


def test_workflows_do_not_request_the_legacy_cpu_pool():
    # Arrange
    legacy = []
    for path in sorted(WORKFLOWS.glob("*.y*ml")):
        workflow = _load(path)
        for key, job in (workflow.get("jobs") or {}).items():
            if "scitex-local-cpu" in str(job.get("runs-on", "")):
                legacy.append(f"{path.name}::{key}")
    # Act
    remaining = len(legacy)
    # Assert
    assert remaining == 0, legacy


def _organization_cpu_jobs():
    for path in sorted(WORKFLOWS.glob("*.y*ml")):
        workflow = _load(path)
        for key, job in (workflow.get("jobs") or {}).items():
            if "scitex-org-cpu" in str(job.get("runs-on", "")):
                yield pytest.param(path.name, key, job, id=f"{path.name}::{key}")


@pytest.mark.parametrize("filename,key,job", list(_organization_cpu_jobs()))
def test_organization_cpu_jobs_depend_on_exact_shared_authorization(filename, key, job):
    # Arrange
    candidate = job
    # Act
    admitted = _shared_admission_routes_forks(filename, candidate)
    # Assert
    assert admitted, f"{filename}::{key} bypasses shared authorization"
