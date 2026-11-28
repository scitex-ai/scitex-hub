"""HPC submissions are tagged and recorded like every other Hub SLURM job.

Real database; ``sbatch`` is the fake executable from ``conftest.fake_slurm``.
"""

from pathlib import Path

import pytest
from django.contrib.auth.models import User

from apps.workspace.console_app.models import WorkloadSession
from apps.workspace.console_app.services.singularity_manager.hpc_manager import (
    HPCManager,
)
from apps.workspace.console_app.services.slurm.tags import NO_PROJECT


@pytest.mark.django_db
def test_hpc_submission_is_tagged_and_recorded(fake_slurm):
    # Arrange
    alice = User.objects.create_user(username="alice")
    fake_slurm.set(FAKE_SLURM_JOB_ID="909")
    # Act
    job_id = HPCManager(config=None).submit_to_hpc(
        alice, Path("/workspace/run.py"), project_id=NO_PROJECT
    )
    # Assert
    row = WorkloadSession.objects.get()
    script = fake_slurm.calls("sbatch")[0]["stdin"]
    assert (job_id, row.scheduler_job_id, "#SBATCH --wckey=pnone" in script) == (
        "909",
        "909",
        True,
    )
