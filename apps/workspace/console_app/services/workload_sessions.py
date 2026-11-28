"""Write and close ``WorkloadSession`` rows: the Hub's ONE launch record.

Every launcher of billable compute writes exactly one row here, and spend
controls read the same rows (``spend_app.services.usage``), so a launch is
never recorded twice.

SLURM launchers follow the same order so that no job runs unrecorded:

1. ``begin_workload`` writes the row *before* submitting, with the allocated
   resources. If the database is unavailable this raises and nothing is
   submitted.
2. The launcher submits with ``row.tags`` (``SlurmTags``) on the command line.
3. ``bind_job`` stores the scheduler job id; ``abandon_workload`` deletes
   the row if submission failed (nothing was launched).
4. ``mark_stopped_*`` / ``close_workloads*`` set ``stopped_at`` and the stop
   reason wherever the Hub learns the workload ended (cancel, allocation
   stop, shell exit, idle or spend-cap stop).

Project services are host processes, not SLURM jobs: ``begin_service_workload``
records one after it started, keyed by its ``service_id``.
"""

from __future__ import annotations

import logging
import re
import socket
from typing import Iterable, Optional, Tuple

from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.workspace.console_app.models import WorkloadSession

from .slurm.tags import SlurmTags

logger = logging.getLogger(__name__)

StopReason = WorkloadSession.StopReason


def begin_workload(
    *,
    user_id: Optional[int],
    tags: SlurmTags,
    workload: str,
    extra_tags: Optional[dict] = None,
    cpus: int = 1,
    memory_gb: int = 4,
    gpus: int = 0,
    max_seconds: Optional[int] = None,
    label: str = "",
) -> WorkloadSession:
    """Create the row for a launch that is about to be submitted with ``tags``.

    ``cpus``/``memory_gb``/``gpus`` are the ALLOCATION (what is billed) and
    ``max_seconds`` the time limit that caps billing when no stop is seen.
    Raises ``ValueError`` for an unknown workload kind.
    """
    if workload not in dict(WorkloadSession.WORKLOAD_CHOICES):
        raise ValueError(f"Unknown workload kind: {workload!r}")
    if not isinstance(tags, SlurmTags):
        raise TypeError("tags must be a SlurmTags instance")
    record = tags.as_record(user_id, workload)
    record.update(extra_tags or {})
    row = WorkloadSession.objects.create(
        session_id=tags.session_id,
        user_id=user_id,
        project_id=tags.project_id,
        workload=workload,
        scheduler=WorkloadSession.SCHEDULER_SLURM,
        host=socket.gethostname(),
        tags=record,
        **_resources(cpus, memory_gb, gpus, max_seconds, label),
    )
    _usage_changed([user_id])
    return row


def begin_terminal_workload(
    username: str, project_slug: str, extra_tags: Optional[dict] = None
) -> Tuple[WorkloadSession, SlurmTags]:
    """Resolve a terminal's owner and project, build fresh tags, write the row.

    A terminal is billed by the interactive allocation (CPUs, memory, time
    limit from the terminal config).
    """
    from apps.workspace.console_app.views.terminal.config import (
        SLURM_CPUS,
        SLURM_MEMORY_GB,
        SLURM_TIME_LIMIT_SECONDS,
    )

    user_id, project_id = resolve_terminal_owner(username, project_slug)
    tags = SlurmTags.for_project(project_id)
    row = begin_workload(
        user_id=user_id,
        tags=tags,
        workload=WorkloadSession.WORKLOAD_TERMINAL,
        extra_tags=extra_tags,
        cpus=SLURM_CPUS,
        memory_gb=SLURM_MEMORY_GB,
        max_seconds=SLURM_TIME_LIMIT_SECONDS,
        label="interactive",
    )
    return row, tags


def begin_service_workload(
    user, *, project_id: Optional[int], service_id, label: str = ""
) -> WorkloadSession:
    """Record a project service (notebook, TensorBoard, ...) that started."""
    row = WorkloadSession.objects.create(
        user=user,
        project_id=project_id,
        workload=WorkloadSession.WORKLOAD_SERVICE,
        scheduler=WorkloadSession.SCHEDULER_LOCAL,
        scheduler_job_id=str(service_id),
        host=socket.gethostname(),
        tags={"scitex.service": str(service_id)},
        **_resources(1, 4, 0, None, label),
    )
    _usage_changed([user.pk])
    return row


def bind_job(row: WorkloadSession, scheduler_job_id) -> None:
    """Record the scheduler's job id on a row written by ``begin_workload``."""
    job_id = str(scheduler_job_id).strip()
    if not job_id:
        raise ValueError("Empty scheduler job id")
    row.scheduler_job_id = job_id
    row.save(update_fields=["scheduler_job_id"])


def abandon_workload(row: WorkloadSession) -> None:
    """Delete the row of a launch whose submission failed."""
    row.delete()
    _usage_changed([row.user_id])


def mark_stopped_by_job(scheduler_job_id, *, reason: str = StopReason.COMPLETED) -> int:
    """Close the open rows for this SLURM job id with ``reason``."""
    job_id = str(scheduler_job_id or "").strip()
    if not job_id:
        return 0
    return _close(
        WorkloadSession.objects.filter(
            scheduler=WorkloadSession.SCHEDULER_SLURM,
            scheduler_job_id=job_id,
        ),
        reason,
    )


def mark_stopped_by_session(session_id, *, reason: str = StopReason.COMPLETED) -> int:
    """Close the open row for this workload session id with ``reason``."""
    if not session_id:
        return 0
    return _close(WorkloadSession.objects.filter(session_id=session_id), reason)


def close_workloads(
    user, *, workload: str, reason: str, scheduler_job_id: Optional[str] = None
) -> int:
    """Close every open ``workload`` row of ``user`` (optionally one job).

    Only OPEN rows change, so a reason recorded first (an idle or spend-cap
    stop) is kept when a later, generic stop path runs.
    """
    qs = WorkloadSession.objects.filter(user=user, workload=workload)
    if scheduler_job_id is not None:
        qs = qs.filter(scheduler_job_id=str(scheduler_job_id))
    return _close(qs, reason)


def close_workloads_for_username(username: str, *, workload: str, reason: str) -> int:
    user = get_user_model().objects.filter(username=username).first()
    if user is None:
        return 0
    return close_workloads(user, workload=workload, reason=reason)


def resolve_terminal_owner(username: str, project_slug: str) -> Tuple[int, int]:
    """Return ``(user_id, project_id)`` for a terminal launched in a project.

    Terminals are always opened from a project owned by ``username`` (the
    consumer passes ``project.owner.username`` and ``project.slug``), so a
    missing project is an error, never a silent ``none`` tag.
    """
    from apps.infra.project_app.models import Project

    user = get_user_model().objects.get(username=username)
    project_id = (
        Project.objects.filter(owner=user, slug=project_slug)
        .values_list("pk", flat=True)
        .first()
    )
    if project_id is None:
        raise LookupError(
            f"No project {project_slug!r} owned by {username!r}; "
            "refusing to launch an unattributed terminal job"
        )
    return user.pk, project_id


def memory_gb_from_slurm(mem) -> int:
    """``--mem`` value (``"4G"``, ``"512M"``, ``"8"`` = MB) to whole GB, min 1."""
    match = re.fullmatch(r"\s*(\d+(?:\.\d+)?)\s*([KMGT]?)B?\s*", str(mem), re.I)
    if match is None:
        raise ValueError(f"Unrecognised SLURM memory value: {mem!r}")
    per_gb = {"K": 1 / 1024**2, "M": 1 / 1024, "": 1 / 1024, "G": 1, "T": 1024}
    gb = float(match.group(1)) * per_gb[match.group(2).upper()]
    return max(1, int(-(-gb // 1)))


def time_limit_seconds_from_slurm(time_limit) -> Optional[int]:
    """``--time`` value (``HH:MM:SS`` / ``MM:SS``) to seconds; ``None`` (bill
    until a stop is seen) for a format the Hub does not parse, e.g.
    ``D-HH:MM:SS``."""
    from apps.workspace.console_app.views.terminal.config import (
        parse_time_limit_seconds,
    )

    try:
        return parse_time_limit_seconds(str(time_limit))
    except ValueError:
        return None


def _resources(cpus, memory_gb, gpus, max_seconds, label) -> dict:
    return {
        "cpus": max(1, int(cpus or 1)),
        "memory_gb": max(0, int(memory_gb or 0)),
        "gpus": max(0, int(gpus or 0)),
        "max_seconds": int(max_seconds) if max_seconds else None,
        "label": str(label or "")[:128],
    }


def _close(qs, reason: str) -> int:
    qs = qs.filter(stopped_at__isnull=True)
    user_ids = set(qs.values_list("user_id", flat=True))
    n = qs.update(stopped_at=timezone.now(), stop_reason=reason)
    if n:
        _usage_changed(user_ids)
    return n


def _usage_changed(user_ids: Iterable[Optional[int]]) -> None:
    """Drop the cached month-to-date usage so caps see the change at once."""
    from apps.infra.spend_app.services.usage import invalidate_user_id

    for user_id in user_ids:
        if user_id is not None:
            invalidate_user_id(user_id)


__all__ = [
    "StopReason",
    "abandon_workload",
    "begin_service_workload",
    "begin_terminal_workload",
    "begin_workload",
    "bind_job",
    "close_workloads",
    "close_workloads_for_username",
    "mark_stopped_by_job",
    "mark_stopped_by_session",
    "memory_gb_from_slurm",
    "resolve_terminal_owner",
    "time_limit_seconds_from_slurm",
]
