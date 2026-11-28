"""The terminal broker tags its SLURM jobs and records them durably.

Before this, the shared allocation kept its job id only in memory. Real
database and real subprocesses: ``sbatch``/``squeue``/``srun``/``scancel``/
``sinfo`` are the fake SLURM executables from ``conftest.fake_slurm``.
"""

import time
from pathlib import Path

import pytest
from django.contrib.auth.models import User

from apps.infra.project_app.models import Project
from apps.workspace.console_app.models import WorkloadSession
from apps.workspace.console_app.services.slurm.tags import parse_comment
from apps.workspace.console_app.services.terminal_broker.allocation import (
    Allocation,
    AllocationState,
)
from apps.workspace.console_app.services.terminal_broker.session import (
    TerminalSession,
)


@pytest.fixture
def project(db):
    alice = User.objects.create_user(username="alice")
    return Project.objects.create(owner=alice, name="EEG", slug="eeg")


@pytest.fixture
def cluster(fake_slurm):
    fake_slurm.set(FAKE_SLURM_JOB_ID="5150", FAKE_SRUN_STDOUT="scitex-alice")
    return fake_slurm


def _alloc(tmp_path, slug="eeg"):
    return Allocation(
        username="alice",
        project_slug=slug,
        container_path="/opt/scitex/container.sif",
        host_user_dir=Path("/data/alice"),
        host_project_dir=Path(f"/data/alice/proj/{slug}"),
        script_dir=tmp_path / "alloc-scripts",
    )


def _option(argv, name):
    return next(a.split("=", 1)[1] for a in argv if a.startswith(f"--{name}="))


@pytest.mark.django_db
def test_start_records_the_job_id(tmp_path, cluster, project):
    # Arrange
    alloc = _alloc(tmp_path)
    # Act
    started = alloc.start()
    # Assert
    row = WorkloadSession.objects.get()
    assert (started, row.scheduler_job_id, row.project_id, row.workload) == (
        True,
        "5150",
        project.id,
        WorkloadSession.WORKLOAD_TERMINAL,
    )


@pytest.mark.django_db
def test_sbatch_carries_the_rows_tags(tmp_path, cluster, project):
    # Arrange
    _alloc(tmp_path).start()
    argv = cluster.calls("sbatch")[0]["argv"]
    # Act
    comment, wckey = _option(argv, "comment"), _option(argv, "wckey")
    # Assert
    row = WorkloadSession.objects.get()
    assert (parse_comment(comment), wckey) == (
        {"project": str(project.id), "session": str(row.session_id)},
        f"p{project.id}",
    )


@pytest.mark.django_db
def test_stop_sets_stopped_at(tmp_path, cluster, project):
    # Arrange
    alloc = _alloc(tmp_path)
    alloc.start()
    # Act
    alloc.stop()
    # Assert
    row = WorkloadSession.objects.get()
    assert (row.stopped_at is not None, cluster.calls("scancel")[0]["argv"]) == (
        True,
        ["5150"],
    )


@pytest.mark.django_db
def test_unknown_project_submits_nothing(tmp_path, cluster, project):
    # Arrange
    alloc = _alloc(tmp_path, slug="not-a-project")
    # Act
    started = alloc.start()
    # Assert
    assert (started, cluster.calls("sbatch"), WorkloadSession.objects.count()) == (
        False,
        [],
        0,
    )


@pytest.mark.django_db
def test_failed_sbatch_leaves_no_row(tmp_path, cluster, project):
    # Arrange
    cluster.set(FAKE_SBATCH_FAIL="1")
    alloc = _alloc(tmp_path)
    # Act
    started = alloc.start()
    # Assert
    assert (started, alloc.state, WorkloadSession.objects.count()) == (
        False,
        AllocationState.DEAD,
        0,
    )


@pytest.mark.django_db
def test_reattached_allocation_closes_the_original_row(tmp_path, cluster, project):
    # Arrange
    _alloc(tmp_path).start()
    reattached = _alloc(tmp_path)
    reattached.attach_to_existing("5150")
    # Act
    reattached.stop()
    # Assert
    assert WorkloadSession.objects.get().stopped_at is not None


def _wait_for(predicate, timeout=15.0):
    deadline = time.time() + timeout
    while time.time() < deadline and not predicate():
        time.sleep(0.05)
    return predicate()


@pytest.mark.django_db
def test_legacy_srun_session_is_tagged_and_recorded(tmp_path, cluster, project):
    # Arrange
    session = TerminalSession(
        session_id="legacy-1",
        username="alice",
        user_data_dir=Path("/data/alice"),
        project_dir=Path("/data/alice/proj/eeg"),
        container_path="/opt/scitex/container.sif",
        project_slug="eeg",
    )
    # Act
    session.spawn()
    _wait_for(lambda: cluster.calls("srun"))
    session.close()
    # Assert
    row = WorkloadSession.objects.get()
    argv = cluster.calls("srun")[0]["argv"]
    assert (
        parse_comment(_option(argv, "comment"))["session"],
        _option(argv, "wckey"),
        row.stopped_at is not None,
    ) == (str(row.session_id), f"p{project.id}", True)
