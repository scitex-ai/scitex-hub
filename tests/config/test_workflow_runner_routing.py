#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: tests/config/test_workflow_runner_routing.py
"""Fork-authored pull requests never execute on our self-hosted runners.

Check jobs run on scitex-local-cpu (our compute nodes) because GitHub-hosted
concurrency is capped org-wide. Those runners are persistent and share a real
$HOME, so any job that checks out pull-request code there must route fork PRs
to ubuntu-latest AND refuse, as its first step, if it still lands self-hosted.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

WORKFLOWS = Path(__file__).resolve().parents[2] / ".github" / "workflows"
FORK_PREDICATE = (
    "github.event.pull_request.head.repo.full_name != github.repository"
)
REQUIRED_CONTEXTS_KEPT = {
    ("pytest-matrix-on-ubuntu-py3-11-3-12-3-13.yml", "ci-gate"):
        "Python CI aggregate gate",
    ("cli-import-smoke-on-ubuntu-latest.yml", "cli-import-smoke"):
        "cli-import-smoke-on-ubuntu-latest",
    # No `name:`, so the required context is the job key, "audit".
    ("scitex-hub-quality-audit-on-ubuntu-latest.yml", "audit"): None,
}


def _load(path: Path) -> dict:
    return yaml.safe_load(path.read_text())


def _triggers(workflow: dict) -> dict:
    # PyYAML reads the bare key `on` as boolean True.
    on = workflow.get("on", workflow.get(True)) or {}
    return on if isinstance(on, dict) else {name: None for name in on}


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
    routes_forks = FORK_PREDICATE in runs_on and "ubuntu-latest" in runs_on
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
    assert FORK_PREDICATE in guard_if and "runner.environment == 'self-hosted'" in guard_if, (
        f"{filename}::{key} must refuse fork code on self-hosted before checkout."
    )


DOCKER_JOBS = [p for p in SELF_HOSTED_PR_JOBS if "scitex-docker" in str(p.values[2]["runs-on"])]


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
