#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: tests/config/test_workflow_jobs_have_timeouts.py
"""Every workflow job that runs steps declares a bounded `timeout-minutes`.

WHY THIS EXISTS. GitHub's default job timeout is 360 minutes. On 2026-11-27 a
"Security Regression Gates" run sat stuck for 3+ hours holding one of the few
scitex-docker runners while pull requests queued behind it. A job that hangs
must give its runner back at about twice its normal duration, not after six
hours. Values were set from the slowest successful run per job over ~300 recent
runs (2x, floor 10 minutes).

Jobs that only call a reusable workflow (`uses:`) cannot carry
`timeout-minutes`; the called workflow's own jobs are covered here when they
live in this repository.
"""

from __future__ import annotations

from pathlib import Path

import yaml

WORKFLOWS = Path(__file__).resolve().parents[2] / ".github" / "workflows"
CEILING_MINUTES = 120


def _step_jobs():
    for path in sorted([*WORKFLOWS.glob("*.yml"), *WORKFLOWS.glob("*.yaml")]):
        jobs = yaml.safe_load(path.read_text(encoding="utf-8")).get("jobs") or {}
        for key, job in jobs.items():
            if "uses" not in job:
                yield f"{path.name}:{key}", job


def test_every_step_job_declares_a_timeout():
    # Arrange
    jobs = dict(_step_jobs())
    # Act
    missing = sorted(name for name, job in jobs.items() if "timeout-minutes" not in job)
    # Assert
    assert (len(jobs) > 0, missing) == (True, [])


def test_no_timeout_exceeds_the_ceiling():
    # Arrange
    jobs = dict(_step_jobs())
    # Act
    unbounded = sorted(
        name
        for name, job in jobs.items()
        if not isinstance(job.get("timeout-minutes"), int)
        or not 1 <= job["timeout-minutes"] <= CEILING_MINUTES
    )
    # Assert
    assert unbounded == []
