#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Visitor container-wipe security tests (isolation audit gap #6).

Invariants under test — visitor usernames are permanent per slot, so
username-keyed container state must die with the session:

* Recycling a slot stops the ``scitex-<username>`` apptainer instance
  and cancels the visitor's SLURM job(s) BEFORE the filesystem wipe,
  and verifies both are gone (channel #1: visitor N+1 attaching into
  N's live instance).
* The wipe covers the ENTIRE home root — ``~/.bash_history``,
  ``~/.local``, AI-tool configs (channel #2) and
  ``~/.singularity/default.sif`` (channel #3: ``select_container``
  prefers that home-level image, so a SIF left by visitor N would
  become N+1's container) — then recreates the fresh skeleton and
  gates on EXACT expected contents.
* ``MEDIA_ROOT/user_containers/<id>`` (custom-container build output)
  is cleared and verified gone.
* Every teardown/verify failure quarantines the slot — never served.

Run (SQLite, no network — SLURM/apptainer are faked at the subprocess
boundary through the pipeline's ``run_cmd`` seam):

    SCITEX_HUB_DJANGO_SECRET_KEY=local-test-secret \
    SCITEX_HUB_GITEA_SSH_PORT_DEV=2222 \
    SCITEX_HUB_USE_SQLITE_DEV=1 \
    /opt/venv-sac/bin/python -m pytest <abs path to this file>
"""

import shutil
import subprocess
from pathlib import Path

import pytest
from django.conf import settings
from django.contrib.auth.models import User

from apps.infra.project_app.services.visitor_pool.home_state import (
    EXPECTED_HOME_ENTRIES,
    EXPECTED_PROJ_ENTRIES,
    user_container_dir,
)
from apps.infra.project_app.services.visitor_pool.slot_lifecycle import (
    get_or_create_allocation,
    reset_and_verify_slot,
)
from apps.infra.project_app.services.visitor_pool.workspace_manager import (
    TEMPLATE_MARKER_RELPATH,
    verify_template_marker,
)
from apps.workspace.console_app.services.terminal_broker.slurm_health import (
    instance_name_for,
    terminal_job_name,
)

USERNAME = "visitor-001"
INSTANCE = instance_name_for(USERNAME)
TERMINAL_JOB = terminal_job_name(USERNAME)

# ---------------------------------------------------------------------------
# Tiny real fakes (no unittest.mock) injected through the existing seams
# ---------------------------------------------------------------------------


class FakeGiteaClient:
    """In-memory Gitea client (no repos) for the reset pipeline."""

    def list_repositories(self, username):
        return []

    def delete_repository(self, owner, repo):
        return True


def fake_clone(template_id, dest, git_strategy=None):
    """Real, tiny template clone mirroring the ``.scitex/writer`` layout."""
    manuscript = Path(dest) / TEMPLATE_MARKER_RELPATH / "01_manuscript"
    manuscript.mkdir(parents=True, exist_ok=True)
    (manuscript / "main.tex").write_text("% fresh template\n")
    return True


def _completed(returncode, stdout="", stderr=""):
    return subprocess.CompletedProcess(
        args=[], returncode=returncode, stdout=stdout, stderr=stderr
    )


class FakeSlurmHost:
    """In-memory SLURM + apptainer host behind the ``run_cmd`` seam.

    Understands exactly the argv shapes ``container_teardown`` issues
    (squeue / scancel / srun --overlap ... instance stop / apptainer
    instance list). ``scancel`` removing a job also kills its instance
    by default — SLURM's proctrack kills every process in the job's
    cgroup, the instance included.
    """

    def __init__(
        self,
        jobs=None,
        instances=None,
        *,
        scancel_ok=True,
        scancel_removes_job=True,
        job_kill_stops_instance=True,
        srun_stop_works=True,
        squeue_rc=0,
    ):
        self.jobs = dict(jobs or {})  # job id -> job name
        self.instances = set(instances or ())
        self.scancel_ok = scancel_ok
        self.scancel_removes_job = scancel_removes_job
        self.job_kill_stops_instance = job_kill_stops_instance
        self.srun_stop_works = srun_stop_works
        self.squeue_rc = squeue_rc
        self.calls = []

    def __call__(self, argv, timeout=None):
        self.calls.append(list(argv))
        prog = argv[0]
        if prog == "squeue":
            if self.squeue_rc:
                return _completed(self.squeue_rc, "", "squeue: connection refused")
            rows = "".join(f"{jid} {name}\n" for jid, name in self.jobs.items())
            return _completed(0, rows)
        if prog == "scancel":
            if not self.scancel_ok:
                return _completed(1, "", "scancel: permission denied")
            if self.scancel_removes_job and argv[-1] in self.jobs:
                del self.jobs[argv[-1]]
                if self.job_kill_stops_instance:
                    self.instances.clear()
            return _completed(0, "")
        if prog == "srun":
            if self.srun_stop_works:
                self.instances.discard(argv[-1])
            return _completed(0, "")
        if prog == "apptainer":  # instance list
            header = "INSTANCE NAME    PID    IP    IMAGE\n"
            rows = "".join(
                f"{name} 4242 10.22.0.5 /opt/scitex/base.sif\n"
                for name in sorted(self.instances)
            )
            return _completed(0, header + rows)
        raise AssertionError(f"unexpected command through run_cmd seam: {argv}")


class NoContainerToolchain:
    """run_cmd fake: a host with no SLURM/apptainer binaries installed."""

    def __call__(self, argv, timeout=None):
        raise FileNotFoundError(argv[0])


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _home_root_for(username: str) -> Path:
    """The visitor's home root, under THIS test's private BASE_DIR.

    The ``isolated_visitor_data_root`` autouse fixture in this
    directory's conftest repoints ``settings.BASE_DIR`` at a per-test
    ``tmp_path`` before every test here, so the module-level
    ``USERNAME`` constant no longer names a directory shared by every
    xdist worker (CI run 29918531942).
    """
    return Path(settings.BASE_DIR) / "data" / "users" / username


@pytest.fixture
def visitor_slot(db):
    """visitor-001 user + allocation row; workspace dirs cleaned afterwards."""
    user = User.objects.create(username=USERNAME, email=f"{USERNAME}@visitor.local")
    allocation = get_or_create_allocation(1)
    yield user, allocation
    home = _home_root_for(USERNAME)
    if home.exists():
        shutil.rmtree(home, ignore_errors=True)


def _reset(allocation, host):
    ok = reset_and_verify_slot(
        allocation,
        gitea_client=FakeGiteaClient(),
        clone_fn=fake_clone,
        run_cmd=host,
    )
    allocation.refresh_from_db()
    return ok


@pytest.fixture
def live_container_reset(visitor_slot):
    """Reset over a slot whose previous visitor left a RUNNING terminal:
    one SLURM job + the scitex-visitor-001 instance."""
    user, allocation = visitor_slot
    host = FakeSlurmHost(jobs={"42": TERMINAL_JOB}, instances={INSTANCE})
    ok = _reset(allocation, host)
    return ok, allocation, host


@pytest.fixture
def fast_teardown_deadline():
    """Shrink the job-gone polling window (timing config constants) so the
    jobs-survive-scancel failure path completes in milliseconds instead of
    the production 30 s grace period. Restored on teardown."""
    from apps.infra.project_app.services.visitor_pool import container_teardown

    saved = (
        container_teardown.JOB_GONE_TIMEOUT,
        container_teardown.JOB_GONE_POLL_INTERVAL,
    )
    container_teardown.JOB_GONE_TIMEOUT = 0.2
    container_teardown.JOB_GONE_POLL_INTERVAL = 0.02
    yield
    (
        container_teardown.JOB_GONE_TIMEOUT,
        container_teardown.JOB_GONE_POLL_INTERVAL,
    ) = saved


# ---------------------------------------------------------------------------
# Channel #1 — live instance / SLURM job teardown
# ---------------------------------------------------------------------------


class TestContainerTeardown:
    def test_reset_with_live_container_verifies_clean(self, live_container_reset):
        # Arrange
        ok, allocation, host = live_container_reset
        # Act
        outcome = ok
        # Assert
        assert outcome is True

    def test_slurm_job_is_cancelled(self, live_container_reset):
        # Arrange
        ok, allocation, host = live_container_reset
        # Act
        remaining_jobs = host.jobs
        # Assert
        assert remaining_jobs == {}

    def test_instance_is_stopped(self, live_container_reset):
        # Arrange
        ok, allocation, host = live_container_reset
        # Act
        remaining_instances = host.instances
        # Assert
        assert remaining_instances == set()

    def test_instance_stop_runs_before_scancel(self, live_container_reset):
        # Arrange: a live instance holds the home bind open — the stop
        # must be issued inside the job before the job is cancelled.
        ok, allocation, host = live_container_reset
        # Act
        progs = [call[0] for call in host.calls]
        # Assert
        assert progs.index("srun") < progs.index("scancel")

    def test_instance_stop_targets_the_visitor_instance_inside_its_job(
        self, live_container_reset
    ):
        # Arrange
        ok, allocation, host = live_container_reset
        # Act
        srun_calls = [call for call in host.calls if call[0] == "srun"]
        # Assert
        assert srun_calls == [
            [
                "srun",
                "--overlap",
                "--jobid=42",
                "apptainer",
                "instance",
                "stop",
                INSTANCE,
            ]
        ]


class TestJobNameConventions:
    def test_container_library_job_naming_is_also_cancelled(self, visitor_slot):
        # Arrange: the installed scitex_container names sbatch jobs
        # scitex_<username>_<slug> (NOT the broker's scitex-hub-terminal-
        # prefix) — teardown must reap that family too.
        user, allocation = visitor_slot
        host = FakeSlurmHost(jobs={"77": f"scitex_{USERNAME}_default-project"})
        # Act
        _reset(allocation, host)
        # Assert
        assert host.jobs == {}

    def test_other_users_jobs_are_untouched(self, visitor_slot):
        # Arrange: jobs of a lookalike username and an unrelated user.
        user, allocation = visitor_slot
        host = FakeSlurmHost(
            jobs={
                "88": "scitex_visitor-0011_x",
                "89": terminal_job_name("visitor-002"),
            }
        )
        # Act
        _reset(allocation, host)
        # Assert
        assert set(host.jobs) == {"88", "89"}


# ---------------------------------------------------------------------------
# Teardown failure -> quarantine (never serve an unverified slot)
# ---------------------------------------------------------------------------


@pytest.fixture
def scancel_failure_reset(visitor_slot):
    user, allocation = visitor_slot
    host = FakeSlurmHost(jobs={"42": TERMINAL_JOB}, scancel_ok=False)
    ok = _reset(allocation, host)
    return ok, allocation


class TestTeardownFailuresQuarantine:
    def test_scancel_failure_reports_failure(self, scancel_failure_reset):
        # Arrange
        ok, allocation = scancel_failure_reset
        # Act
        outcome = ok
        # Assert
        assert outcome is False

    def test_scancel_failure_quarantines_slot(self, scancel_failure_reset):
        # Arrange
        ok, allocation = scancel_failure_reset
        # Act
        quarantined = allocation.quarantined
        # Assert
        assert quarantined is True

    def test_scancel_failure_records_teardown_reason(self, scancel_failure_reset):
        # Arrange
        ok, allocation = scancel_failure_reset
        # Act
        reason = allocation.quarantine_reason.lower()
        # Assert
        assert "teardown" in reason

    def test_job_surviving_scancel_quarantines_slot(
        self, visitor_slot, fast_teardown_deadline
    ):
        # Arrange: scancel "succeeds" but the job never leaves squeue.
        user, allocation = visitor_slot
        host = FakeSlurmHost(
            jobs={"42": TERMINAL_JOB}, scancel_removes_job=False
        )
        # Act
        _reset(allocation, host)
        # Assert
        assert allocation.quarantined is True

    def test_instance_surviving_teardown_quarantines_slot(self, visitor_slot):
        # Arrange: the job dies but the instance escapes both the in-job
        # stop and the job-kill (worst case) — the verify gate must catch it.
        user, allocation = visitor_slot
        host = FakeSlurmHost(
            jobs={"42": TERMINAL_JOB},
            instances={INSTANCE},
            job_kill_stops_instance=False,
            srun_stop_works=False,
        )
        # Act
        _reset(allocation, host)
        # Assert
        assert allocation.quarantined is True

    def test_unreadable_squeue_quarantines_slot(self, visitor_slot):
        # Arrange: squeue is installed but erroring — "cannot check" must
        # never verify as "clean" (no silent fallback).
        user, allocation = visitor_slot
        host = FakeSlurmHost(squeue_rc=1)
        # Act
        _reset(allocation, host)
        # Assert
        assert allocation.quarantined is True

    def test_missing_toolchain_resets_cleanly(self, visitor_slot):
        # Arrange: dev/CI baseline — no SLURM/apptainer binaries at all,
        # so no broker-created container state can exist here.
        user, allocation = visitor_slot
        # Act
        ok = _reset(allocation, NoContainerToolchain())
        # Assert
        assert ok is True


# ---------------------------------------------------------------------------
# Channels #2 + #3 — home-root residue and the home-level container image
# ---------------------------------------------------------------------------


@pytest.fixture
def home_residue_reset(visitor_slot):
    """Reset over a home root full of the residue a real visitor leaves:
    shell history, pip --user installs, AI-tool config, and a home-level
    ``.singularity/default.sif`` (which select_container would hand to
    the NEXT visitor as their container image)."""
    user, allocation = visitor_slot
    home = _home_root_for(USERNAME)
    (home / "proj" / "default-project").mkdir(parents=True, exist_ok=True)
    (home / "proj" / "default-project" / "notes.txt").write_text("visitor A data")
    (home / ".bash_history").write_text("curl https://visitor-a.example/secret\n")
    (home / ".claude.json").write_text('{"api_key": "visitor-a-key"}')
    pip_dir = home / ".local" / "lib" / "python3.11" / "site-packages"
    pip_dir.mkdir(parents=True, exist_ok=True)
    (pip_dir / "malicious.py").write_text("print('hi')\n")
    sif_dir = home / ".singularity"
    sif_dir.mkdir(exist_ok=True)
    (sif_dir / "default.sif").write_bytes(b"FAKE-SIF visitor A built this")

    ok = _reset(allocation, FakeSlurmHost())
    if not ok:
        raise RuntimeError("fixture reset must succeed")
    return home


class TestHomeRootWipe:
    def test_bash_history_does_not_survive(self, home_residue_reset):
        # Arrange
        home = home_residue_reset
        # Act
        survived = (home / ".bash_history").exists()
        # Assert
        assert survived is False

    def test_ai_tool_config_does_not_survive(self, home_residue_reset):
        # Arrange
        home = home_residue_reset
        # Act
        survived = (home / ".claude.json").exists()
        # Assert
        assert survived is False

    def test_pip_user_installs_do_not_survive(self, home_residue_reset):
        # Arrange
        home = home_residue_reset
        # Act
        survived = (home / ".local").exists()
        # Assert
        assert survived is False

    def test_home_level_container_image_does_not_survive(self, home_residue_reset):
        # Arrange: channel #3 — select_container prefers this exact path.
        home = home_residue_reset
        # Act
        survived = (home / ".singularity" / "default.sif").exists()
        # Assert
        assert survived is False

    def test_singularity_dir_is_empty_after_reset(self, home_residue_reset):
        # Arrange
        home = home_residue_reset
        # Act
        entries = list((home / ".singularity").iterdir())
        # Assert
        assert entries == []

    def test_home_holds_exactly_the_fresh_skeleton(self, home_residue_reset):
        # Arrange
        home = home_residue_reset
        # Act
        entries = {p.name for p in home.iterdir()}
        # Assert
        assert entries == set(EXPECTED_HOME_ENTRIES)

    def test_proj_holds_exactly_the_fresh_clone(self, home_residue_reset):
        # Arrange
        home = home_residue_reset
        # Act
        entries = {p.name for p in (home / "proj").iterdir()}
        # Assert
        assert entries == set(EXPECTED_PROJ_ENTRIES)

    def test_bashrc_symlink_points_into_fresh_dotfiles(self, home_residue_reset):
        # Arrange
        home = home_residue_reset
        # Act
        target = (home / ".bashrc").resolve()
        # Assert
        assert target == (home / "proj" / "dotfiles" / "bashrc").resolve()

    def test_template_marker_verified_after_home_wipe(self, home_residue_reset):
        # Arrange
        home = home_residue_reset
        # Act
        marker_ok = verify_template_marker(home / "proj" / "default-project")
        # Assert
        assert marker_ok is True


# ---------------------------------------------------------------------------
# user_containers build storage
# ---------------------------------------------------------------------------


@pytest.fixture
def user_containers_reset(visitor_slot):
    """Reset over a visitor who built a custom container image."""
    user, allocation = visitor_slot
    container_dir = user_container_dir(user)
    container_dir.mkdir(parents=True, exist_ok=True)
    (container_dir / "custom.sif").write_bytes(b"FAKE-SIF custom build")
    ok = _reset(allocation, FakeSlurmHost())
    yield ok, container_dir
    if container_dir.exists():
        shutil.rmtree(container_dir, ignore_errors=True)


class TestUserContainerStorage:
    def test_reset_with_built_container_succeeds(self, user_containers_reset):
        # Arrange
        ok, container_dir = user_containers_reset
        # Act
        outcome = ok
        # Assert
        assert outcome is True

    def test_user_container_build_dir_is_cleared(self, user_containers_reset):
        # Arrange
        ok, container_dir = user_containers_reset
        # Act
        survived = container_dir.exists()
        # Assert
        assert survived is False


if __name__ == "__main__":
    import os

    pytest.main([os.path.abspath(__file__)])
