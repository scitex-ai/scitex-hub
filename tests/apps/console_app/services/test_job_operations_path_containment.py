#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Path-containment regression tests for SLURM batch scripts."""

from pathlib import Path
from unittest.mock import patch

import pytest
from django.contrib.auth.models import User

from apps.workspace.console_app.services.slurm.job_operations import submit_job
from apps.workspace.console_app.services.slurm.tags import NO_PROJECT


def _submit(root: Path, user_id: str, job_name: str):
    with (
        patch(
            "apps.workspace.console_app.services.slurm.job_operations.create_batch_script",
            return_value="#!/bin/sh\n",
        ),
        patch(
            "apps.workspace.console_app.services.slurm.job_operations.subprocess.run"
        ) as run,
    ):
        run.return_value.stdout = "Submitted batch job 7"
        return submit_job(
            job_scripts_dir=root,
            user_id=user_id,
            job_name=job_name,
            script_path=Path("run.py"),
            container_path=Path("image.sif"),
            workspace=Path("workspace"),
            project_id=NO_PROJECT,
        )


def test_submit_job_rejects_traversal_before_writing(tmp_path):
    scripts = tmp_path / "scripts"
    scripts.mkdir()

    result = _submit(scripts, "alice", "../../../escaped")

    assert result == {"success": False, "message": "Invalid job configuration."}


def test_submit_job_traversal_creates_no_file_outside_root(tmp_path):
    scripts = tmp_path / "scripts"
    scripts.mkdir()

    _submit(scripts, "alice", "../../../escaped")

    assert not (tmp_path.parent / "escaped.sh").exists()


def test_submit_job_rejects_symlink_escape_before_writing(tmp_path):
    scripts = tmp_path / "scripts"
    outside = tmp_path / "outside"
    scripts.mkdir()
    outside.mkdir()
    (scripts / "job_alice_link").symlink_to(outside, target_is_directory=True)

    result = _submit(scripts, "alice", "link/payload")

    assert result == {"success": False, "message": "Invalid job configuration."}


@pytest.mark.django_db
def test_submit_job_writes_legitimate_batch_script(tmp_path):
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    alice = User.objects.create_user(username="alice")

    result = _submit(scripts, str(alice.id), "analysis")

    assert result["success"] is True
