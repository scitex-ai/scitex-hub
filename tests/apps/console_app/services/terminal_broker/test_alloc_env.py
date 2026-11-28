"""The shared allocation's sbatch/srun calls get an allowlisted environment.

``sbatch`` and ``srun`` export the caller's environment into the job, and
the Apptainer instance started there is shared by every shell the user
opens. The fake SLURM toolkit (conftest) records the environment NAMES each
call actually received.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from django.contrib.auth.models import User

from apps.infra.project_app.models import Project
from apps.workspace.console_app.services.terminal_broker.allocation import (
    Allocation,
)

SECRET = "SCITEX_HUB_DJANGO_SECRET_KEY"


@pytest.fixture
def cluster(fake_slurm):
    fake_slurm.set(FAKE_SLURM_JOB_ID="5150", FAKE_SRUN_STDOUT="scitex-alice")
    return fake_slurm


@pytest.fixture
def server_secret():
    saved = os.environ.get(SECRET)
    os.environ[SECRET] = "x"
    try:
        yield SECRET
    finally:
        if saved is None:
            os.environ.pop(SECRET, None)
        else:
            os.environ[SECRET] = saved


@pytest.fixture
def started(db, tmp_path, cluster, server_secret):
    alice = User.objects.create_user(username="alice")
    Project.objects.create(owner=alice, name="EEG", slug="eeg")
    alloc = Allocation(
        username="alice",
        project_slug="eeg",
        container_path="/opt/scitex/container.sif",
        host_user_dir=Path("/data/alice"),
        host_project_dir=Path("/data/alice/proj/eeg"),
        script_dir=tmp_path / "alloc-scripts",
    )
    alloc.start()
    return cluster


def test_sbatch_does_not_receive_server_secrets(started):
    # Arrange
    calls = started.calls("sbatch")
    # Act
    names = set(calls[0]["env_names"])
    # Assert
    assert SECRET not in names


def test_srun_does_not_receive_server_secrets(started):
    # Arrange
    calls = started.calls("srun")
    # Act
    leaked = [c for c in calls if SECRET in c["env_names"]]
    # Assert
    assert leaked == []
