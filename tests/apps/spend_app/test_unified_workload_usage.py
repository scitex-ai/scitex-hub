"""Spend controls bill from the ONE launch record, ``console_app.WorkloadSession``.

Rows are written by the real console writer (``begin_workload``), not by a
spend-only helper: there is no second launch table any more.
"""

from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.workspace.console_app.models import WorkloadSession

pytestmark = pytest.mark.django_db


def _launch_job(user, *, cpus, memory_gb, hours):
    """A job recorded by the console writer, then ended ``hours`` later."""
    from apps.workspace.console_app.services.slurm.tags import NO_PROJECT, SlurmTags
    from apps.workspace.console_app.services.workload_sessions import (
        begin_workload,
        mark_stopped_by_session,
    )

    row = begin_workload(
        user_id=user.pk,
        tags=SlurmTags.for_project(NO_PROJECT),
        workload=WorkloadSession.WORKLOAD_JOB,
        cpus=cpus,
        memory_gb=memory_gb,
    )
    now = timezone.now()
    WorkloadSession.objects.filter(pk=row.pk).update(
        started_at=now - timedelta(hours=hours)
    )
    mark_stopped_by_session(row.session_id)
    return row


def _compute_line(user):
    from apps.infra.spend_app.services import usage

    snap = usage.current_snapshot(user, fresh=True)
    return next(line for line in snap.lines if line.resource == "compute")


def test_a_job_recorded_by_the_console_writer_is_billed_by_allocation(
    user, subscription
):
    # Arrange
    _launch_job(user, cpus=2, memory_gb=8, hours=1.0)  # 2 CPU-units x 1 h at $0.05
    # Act
    compute = _compute_line(user)
    # Assert
    assert compute.amount_usd == Decimal("0.1000")


def test_two_overlapping_terminal_tabs_bill_the_allocation_once(
    user, workload, subscription
):
    # Arrange: two srun tabs of the same user over the same hour.
    workload(cpus=2, hours=1.0, kind=WorkloadSession.WORKLOAD_TERMINAL)
    workload(cpus=2, hours=1.0, kind=WorkloadSession.WORKLOAD_TERMINAL)
    # Act
    compute = _compute_line(user)
    # Assert
    assert compute.quantity == Decimal("2.0000")


def test_overlapping_terminal_rows_bill_the_largest_allocation_in_force(
    user, workload, subscription
):
    # Arrange
    workload(cpus=2, hours=1.0, kind=WorkloadSession.WORKLOAD_TERMINAL)
    workload(cpus=4, hours=0.5, kind=WorkloadSession.WORKLOAD_TERMINAL)
    # Act
    compute = _compute_line(user)
    # Assert: 0.5 h x 2 cores + 0.5 h x 4 cores
    assert compute.quantity == Decimal("3.0000")


def test_concurrent_jobs_are_each_billed(user, workload, subscription):
    # Arrange: jobs are separate allocations, unlike terminal tabs.
    workload(cpus=2, hours=1.0, kind=WorkloadSession.WORKLOAD_JOB)
    workload(cpus=2, hours=1.0, kind=WorkloadSession.WORKLOAD_JOB)
    # Act
    compute = _compute_line(user)
    # Assert
    assert compute.quantity == Decimal("4.0000")


def test_an_enforcement_stop_sets_the_reason_on_the_launch_row(user, subscription):
    # Arrange
    from apps.infra.spend_app.services import enforcement, policy
    from apps.workspace.console_app.services.slurm.tags import NO_PROJECT, SlurmTags
    from apps.workspace.console_app.services.workload_sessions import begin_workload

    row = begin_workload(
        user_id=user.pk,
        tags=SlurmTags.for_project(NO_PROJECT),
        workload=WorkloadSession.WORKLOAD_JOB,
    )
    verdict = policy.RunningVerdict(policy.Run.STOP, reason="cap_reached")
    # Act
    enforcement.stop_running_work(user, verdict)
    # Assert
    assert WorkloadSession.objects.get(pk=row.pk).stop_reason == "spend_cap"


def test_a_closed_row_keeps_the_reason_recorded_first(user, workload):
    # Arrange
    from apps.workspace.console_app.services.workload_sessions import (
        close_workloads,
    )

    row = workload(open_=True)
    close_workloads(user, workload="terminal", reason="idle")
    # Act
    close_workloads(user, workload="terminal", reason="user")
    # Assert
    assert WorkloadSession.objects.get(pk=row.pk).stop_reason == "idle"
