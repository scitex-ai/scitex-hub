"""Tag and record a terminal allocation's SLURM job (see services/workload_sessions).

The shared allocation is one sbatch job per user, so it is ONE row: every
shell (tab) attached to it runs inside that job and writes no row of its
own, which is what keeps a multi-tab session billed once. The row is
attributed to the project the user opened when the job was submitted;
shells later attached for other projects are not re-attributed.
"""

from __future__ import annotations

import logging

from ..slurm.tags import SlurmTags

logger = logging.getLogger(__name__)


def begin(alloc) -> SlurmTags:
    """Write the WorkloadSession row for ``alloc`` and return its tags.

    Raises if the user/project cannot be resolved or the row cannot be
    written, so the allocation never submits an unrecorded job.
    """
    from ..workload_sessions import begin_terminal_workload

    alloc.workload_row, tags = begin_terminal_workload(
        alloc.username,
        alloc.project_slug,
        extra_tags={"scitex.allocation": alloc.allocation_id},
    )
    return tags


def bind_job(alloc) -> None:
    from ..workload_sessions import bind_job as bind_row

    bind_row(alloc.workload_row, alloc.job_id)


def abandon(alloc) -> None:
    """Drop the row of an allocation whose sbatch never returned a job."""
    from ..workload_sessions import abandon_workload

    if alloc.workload_row is not None and not alloc.job_id:
        abandon_workload(alloc.workload_row)
        alloc.workload_row = None


def adopt_existing(alloc) -> None:
    """Attach ``alloc`` to the row of the job it is re-attaching to.

    A row the idle reaper closed as ``lost`` (the broker restarted and lost
    track of a job that kept running) is reopened: the allocation never
    stopped, so neither does its clock.
    """
    from apps.workspace.console_app.models import WorkloadSession

    try:
        row = (
            WorkloadSession.objects.filter(
                scheduler=WorkloadSession.SCHEDULER_SLURM,
                scheduler_job_id=str(alloc.job_id),
            )
            .order_by("-started_at")
            .first()
        )
        if row is not None and row.stopped_at is not None:
            if row.stop_reason == WorkloadSession.StopReason.LOST:
                row.stopped_at = None
                row.stop_reason = WorkloadSession.StopReason.NONE
                row.save(update_fields=["stopped_at", "stop_reason"])
            else:
                row = None
    except Exception:
        # The job was recorded when it was submitted; only its end time is
        # at risk, which must not block re-attaching a running terminal.
        logger.exception(
            "Allocation %s: could not look up the row of job %s",
            alloc.allocation_id[:8],
            alloc.job_id,
        )
        row = None
    if row is None:
        logger.warning(
            "Allocation %s: job %s has no WorkloadSession row "
            "(submitted before workload recording, or outside the Hub)",
            alloc.allocation_id[:8],
            alloc.job_id,
        )
    alloc.workload_row = row


def record_ended(alloc, reason: str = "completed") -> None:
    """Close the allocation's row once the Hub knows the job ended.

    Only an open row changes, so a reason recorded first (user, idle, spend
    cap) is kept."""
    from ..workload_sessions import mark_stopped_by_session

    row = getattr(alloc, "workload_row", None)
    if row is None:
        return
    try:
        mark_stopped_by_session(row.session_id, reason=reason)
    except Exception:
        # Called on teardown paths that must finish; the row stays open and
        # the collector still has sacct's End time for the job.
        logger.exception(
            "Allocation %s: could not record the end of job %s",
            alloc.allocation_id[:8],
            alloc.job_id,
        )
