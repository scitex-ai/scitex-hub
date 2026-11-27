"""Hub batch jobs are tagged and durably recorded as WorkloadSession rows.

Real database and real subprocesses: ``sbatch``/``scancel`` are the fake
SLURM executables from ``conftest.fake_slurm``.
"""

from pathlib import Path

import pytest
from django.contrib.auth.models import User

from apps.infra.project_app.models import Project
from apps.workspace.console_app.models import WorkloadSession
from apps.workspace.console_app.services.slurm.job_operations import (
    cancel_job,
    submit_job,
)
from apps.workspace.console_app.services.slurm.tags import NO_PROJECT, parse_comment
from apps.workspace.console_app.services.workload_sessions import (
    begin_terminal_workload,
    mark_stopped_by_job,
)


def _submit(tmp_path, user, project_id):
    scripts = tmp_path / "scripts"
    scripts.mkdir(exist_ok=True)
    return submit_job(
        job_scripts_dir=scripts,
        user_id=str(user.id),
        script_path=Path("/workspace/run.py"),
        container_path=Path("/opt/scitex/image.sif"),
        workspace=tmp_path / "ws",
        job_name="scitex_alice_run",
        project_id=project_id,
    )


@pytest.fixture
def alice(db):
    return User.objects.create_user(username="alice")


@pytest.fixture
def project(alice):
    return Project.objects.create(owner=alice, name="EEG", slug="eeg")


@pytest.mark.django_db
def test_submit_writes_row_with_job_id(tmp_path, fake_slurm, alice, project):
    # Arrange
    fake_slurm.set(FAKE_SLURM_JOB_ID="4242")
    # Act
    result = _submit(tmp_path, alice, project.id)
    # Assert
    row = WorkloadSession.objects.get(session_id=result["workload_session_id"])
    assert (row.scheduler_job_id, row.user_id, row.project_id) == (
        "4242",
        alice.id,
        project.id,
    )


@pytest.mark.django_db
def test_submitted_script_carries_the_rows_session(
    tmp_path, fake_slurm, alice, project
):
    # Arrange
    result = _submit(tmp_path, alice, project.id)
    script = Path(fake_slurm.calls("sbatch")[0]["argv"][0]).read_text()
    # Act
    comment = next(
        ln.split("=", 1)[1] for ln in script.splitlines() if "--comment=" in ln
    )
    # Assert
    assert parse_comment(comment) == {
        "project": str(project.id),
        "session": result["workload_session_id"],
    }


@pytest.mark.django_db
def test_submitted_script_keeps_the_user_account(tmp_path, fake_slurm, alice, project):
    # Arrange
    _submit(tmp_path, alice, project.id)
    # Act
    script = Path(fake_slurm.calls("sbatch")[0]["argv"][0]).read_text()
    # Assert
    assert f"#SBATCH --account=user_{alice.id}" in script.splitlines()


@pytest.mark.django_db
def test_submit_without_project_records_null_project(tmp_path, fake_slurm, alice):
    # Arrange
    # Act
    result = _submit(tmp_path, alice, NO_PROJECT)
    # Assert
    row = WorkloadSession.objects.get(session_id=result["workload_session_id"])
    assert (row.project_id, row.tags["scitex.project"]) == (None, "none")


@pytest.mark.django_db
def test_failed_sbatch_leaves_no_row(tmp_path, fake_slurm, alice, project):
    # Arrange
    fake_slurm.set(FAKE_SBATCH_FAIL="1")
    # Act
    result = _submit(tmp_path, alice, project.id)
    # Assert
    assert (result["success"], WorkloadSession.objects.count()) == (False, 0)


@pytest.mark.django_db
def test_invalid_project_submits_nothing(tmp_path, fake_slurm, alice):
    # Arrange
    payload = "1; rm -rf /"
    # Act
    result = _submit(tmp_path, alice, payload)
    # Assert
    assert (result["success"], fake_slurm.calls("sbatch")) == (False, [])


@pytest.mark.django_db
def test_cancel_sets_stopped_at(tmp_path, fake_slurm, alice, project):
    # Arrange
    fake_slurm.set(FAKE_SLURM_JOB_ID="77")
    result = _submit(tmp_path, alice, project.id)
    # Act
    cancel_job(77)
    # Assert
    row = WorkloadSession.objects.get(session_id=result["workload_session_id"])
    assert row.stopped_at is not None


@pytest.mark.django_db
def test_mark_stopped_by_job_ignores_closed_rows(tmp_path, fake_slurm, alice, project):
    # Arrange
    fake_slurm.set(FAKE_SLURM_JOB_ID="78")
    _submit(tmp_path, alice, project.id)
    mark_stopped_by_job("78")
    # Act
    updated = mark_stopped_by_job("78")
    # Assert
    assert updated == 0


@pytest.mark.django_db
def test_terminal_workload_resolves_owner_and_project(alice, project):
    # Arrange
    # Act
    row, tags = begin_terminal_workload("alice", "eeg")
    # Assert
    assert (row.project_id, row.workload, tags.project_id) == (
        project.id,
        WorkloadSession.WORKLOAD_TERMINAL,
        project.id,
    )


@pytest.mark.django_db
def test_terminal_workload_refuses_unknown_project(alice):
    # Arrange
    # Act
    # Assert
    with pytest.raises(LookupError):
        begin_terminal_workload("alice", "no-such-project")
