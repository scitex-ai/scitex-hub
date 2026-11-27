"""One Hub launch is ONE ``WorkloadSession`` row, carrying what spend bills by.

Before the fold, a job submitted through the API was written by
``begin_workload`` AND by spend_app's ``open_workload``, and a terminal by the
allocation AND by the web consumer. Real database, real views, and the fake
SLURM executables from ``conftest.fake_slurm``.
"""

import json
from pathlib import Path

import pytest
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone

from apps.infra.project_app.models import Project
from apps.workspace.console_app.models import WorkloadSession
from apps.workspace.console_app.services.terminal_broker.allocation import Allocation

pytestmark = pytest.mark.django_db


@pytest.fixture
def alice(db):
    return User.objects.create_user(username="alice")


@pytest.fixture
def project(alice):
    return Project.objects.create(owner=alice, name="EEG", slug="eeg")


@pytest.fixture
def job_api(tmp_path, settings, fake_slurm):
    """The job API wired to a scripts dir and workspace under ``tmp_path``."""
    from apps.workspace.console_app import job_api_views
    from apps.workspace.console_app.services import SlurmManager

    settings.USER_WORKSPACE_BASE = str(tmp_path / "workspaces")
    saved = job_api_views._slurm_manager
    job_api_views._slurm_manager = SlurmManager(tmp_path / "scripts")
    fake_slurm.set(FAKE_SLURM_JOB_ID="7001")
    yield fake_slurm
    job_api_views._slurm_manager = saved


def _submit(client, user, **body):
    client.force_login(user)
    payload = {"script_path": "/workspace/run.py", "job_name": "run", **body}
    return client.post(
        reverse("console_app:api_submit_job"),
        data=json.dumps(payload),
        content_type="application/json",
    )


def _alloc(tmp_path):
    return Allocation(
        username="alice",
        project_slug="eeg",
        container_path="/opt/scitex/container.sif",
        host_user_dir=Path("/data/alice"),
        host_project_dir=Path("/data/alice/proj/eeg"),
        script_dir=tmp_path / "alloc-scripts",
    )


def test_a_job_submitted_through_the_api_is_one_row(client, job_api, alice):
    # Arrange
    # Act
    _submit(client, alice)
    # Assert
    assert WorkloadSession.objects.filter(user=alice).count() == 1


def test_the_job_row_carries_its_allocation(client, job_api, alice):
    # Arrange
    _submit(client, alice, cpus=3, memory_gb=6, time_limit="02:00:00")
    # Act
    row = WorkloadSession.objects.get(user=alice)
    # Assert
    assert (row.scheduler_job_id, row.cpus, row.memory_gb, row.max_seconds) == (
        "7001",
        3,
        6,
        7200,
    )


def test_cancelling_a_job_closes_its_row_as_a_user_stop(client, job_api, alice):
    # Arrange
    from apps.workspace.console_app import job_api_views

    _submit(client, alice)
    # Act: what api_cancel_job runs once ownership is established (the fake
    # squeue lists no job names, so the view's ownership check cannot pass).
    job_api_views.get_slurm_manager().cancel_job(7001)
    # Assert
    assert WorkloadSession.objects.get(user=alice).stop_reason == "user"


def test_a_terminal_allocation_is_one_row(tmp_path, fake_slurm, project):
    # Arrange
    fake_slurm.set(FAKE_SLURM_JOB_ID="5150", FAKE_SRUN_STDOUT="scitex-alice")
    # Act
    _alloc(tmp_path).start()
    # Assert
    assert WorkloadSession.objects.count() == 1


def test_the_terminal_row_carries_the_interactive_allocation(
    tmp_path, fake_slurm, project
):
    # Arrange
    from apps.workspace.console_app.views.terminal.config import (
        SLURM_CPUS,
        SLURM_MEMORY_GB,
        SLURM_TIME_LIMIT_SECONDS,
    )

    fake_slurm.set(FAKE_SLURM_JOB_ID="5150", FAKE_SRUN_STDOUT="scitex-alice")
    # Act
    _alloc(tmp_path).start()
    # Assert
    row = WorkloadSession.objects.get()
    assert (row.cpus, row.memory_gb, row.max_seconds) == (
        SLURM_CPUS,
        SLURM_MEMORY_GB,
        SLURM_TIME_LIMIT_SECONDS,
    )


def test_reattaching_reopens_a_row_closed_as_lost(tmp_path, fake_slurm, project):
    # Arrange: the broker restarted and its reaper closed the running job's
    # row as lost; the user then re-attaches to the same job.
    fake_slurm.set(FAKE_SLURM_JOB_ID="5150", FAKE_SRUN_STDOUT="scitex-alice")
    _alloc(tmp_path).start()
    WorkloadSession.objects.update(stop_reason="lost", stopped_at=timezone.now())
    # Act
    _alloc(tmp_path).attach_to_existing("5150")
    # Assert
    assert WorkloadSession.objects.get().stopped_at is None


def test_a_spend_stop_cancels_the_job_and_records_the_reason(client, job_api, alice):
    # Arrange
    from apps.infra.spend_app.services import enforcement, policy

    _submit(client, alice)
    verdict = policy.RunningVerdict(policy.Run.STOP, reason="cap_reached")
    # Act
    enforcement.stop_running_work(alice, verdict)
    # Assert
    row = WorkloadSession.objects.get(user=alice)
    assert (row.stop_reason, job_api.calls("scancel")[0]["argv"]) == (
        "spend_cap",
        ["7001"],
    )


def test_a_project_service_is_one_row_on_the_host_scheduler(alice, project):
    # Arrange
    from apps.workspace.console_app.services.workload_sessions import (
        begin_service_workload,
    )

    # Act
    row = begin_service_workload(
        alice, project_id=project.pk, service_id="svc-1", label="tensorboard"
    )
    # Assert
    assert (row.workload, row.scheduler, row.scheduler_job_id) == (
        "service",
        "local",
        "svc-1",
    )
