"""Write and close ``WorkloadSession`` rows for Hub-launched SLURM jobs.

Every launcher follows the same order so that no job runs unrecorded:

1. ``begin_workload`` writes the row *before* submitting. If the database
   is unavailable this raises and nothing is submitted.
2. The launcher submits with ``row.tags`` (``SlurmTags``) on the command line.
3. ``bind_job`` stores the scheduler job id; ``abandon_workload`` deletes
   the row if submission failed (nothing was launched).
4. ``mark_stopped_*`` sets ``stopped_at`` wherever the Hub learns the job
   ended (cancel, allocation stop, shell exit).
"""

from __future__ import annotations

import logging
import socket
from typing import Optional, Tuple

from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.workspace.console_app.models import WorkloadSession

from .slurm.tags import SlurmTags

logger = logging.getLogger(__name__)


def begin_workload(
    *,
    user_id: Optional[int],
    tags: SlurmTags,
    workload: str,
    extra_tags: Optional[dict] = None,
) -> WorkloadSession:
    """Create the row for a launch that is about to be submitted with ``tags``.

    Raises ``ValueError`` for an unknown workload kind.
    """
    if workload not in dict(WorkloadSession.WORKLOAD_CHOICES):
        raise ValueError(f"Unknown workload kind: {workload!r}")
    if not isinstance(tags, SlurmTags):
        raise TypeError("tags must be a SlurmTags instance")
    record = tags.as_record(user_id, workload)
    record.update(extra_tags or {})
    return WorkloadSession.objects.create(
        session_id=tags.session_id,
        user_id=user_id,
        project_id=tags.project_id,
        workload=workload,
        scheduler=WorkloadSession.SCHEDULER_SLURM,
        host=socket.gethostname(),
        tags=record,
    )


def begin_terminal_workload(
    username: str, project_slug: str, extra_tags: Optional[dict] = None
) -> Tuple[WorkloadSession, SlurmTags]:
    """Resolve a terminal's owner and project, build fresh tags, write the row."""
    user_id, project_id = resolve_terminal_owner(username, project_slug)
    tags = SlurmTags.for_project(project_id)
    row = begin_workload(
        user_id=user_id,
        tags=tags,
        workload=WorkloadSession.WORKLOAD_TERMINAL,
        extra_tags=extra_tags,
    )
    return row, tags


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


def mark_stopped_by_job(scheduler_job_id) -> int:
    """Set ``stopped_at`` on the open rows for this SLURM job id."""
    job_id = str(scheduler_job_id or "").strip()
    if not job_id:
        return 0
    return WorkloadSession.objects.filter(
        scheduler=WorkloadSession.SCHEDULER_SLURM,
        scheduler_job_id=job_id,
        stopped_at__isnull=True,
    ).update(stopped_at=timezone.now())


def mark_stopped_by_session(session_id) -> int:
    """Set ``stopped_at`` on the open row for this workload session id."""
    if not session_id:
        return 0
    return WorkloadSession.objects.filter(
        session_id=session_id, stopped_at__isnull=True
    ).update(stopped_at=timezone.now())


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


__all__ = [
    "abandon_workload",
    "begin_terminal_workload",
    "begin_workload",
    "bind_job",
    "mark_stopped_by_job",
    "mark_stopped_by_session",
    "resolve_terminal_owner",
]
