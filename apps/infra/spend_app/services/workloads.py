"""Launch/stop records for billable workloads (design §3.2 ``WorkloadSession``).

Every launcher that starts billable compute calls :func:`open_workload` after
the start succeeded and :func:`close_workload` when it ends. The rows are the
provisional compute source (:mod:`.usage`) and the join the ledger will use.
"""

from __future__ import annotations

from django.utils import timezone

from . import usage


def open_workload(
    user,
    *,
    kind: str,
    project_id=None,
    cpus: int = 1,
    memory_gb: int = 4,
    gpus: int = 0,
    max_seconds=None,
    scheduler_id: str = "",
    label: str = "",
    reuse_open: bool = False,
):
    """Record a launch. ``reuse_open`` keeps ONE open row per (user, kind):
    an interactive allocation is shared by every terminal tab, so a second
    tab must not double-bill it."""
    from ..models import WorkloadSession

    if reuse_open:
        existing = (
            WorkloadSession.objects.filter(
                user=user, kind=kind, stopped_at__isnull=True
            )
            .order_by("-started_at")
            .first()
        )
        if existing is not None:
            return existing
    row = WorkloadSession.objects.create(
        user=user,
        kind=kind,
        project_id=project_id,
        cpus=max(1, int(cpus or 1)),
        memory_gb=max(0, int(memory_gb or 0)),
        gpus=max(0, int(gpus or 0)),
        max_seconds=max_seconds,
        scheduler_id=str(scheduler_id or "")[:128],
        label=str(label or "")[:128],
        started_at=timezone.now(),
    )
    usage.invalidate(user)
    return row


def close_workloads(
    user, *, kind: str, reason: str, scheduler_id: str | None = None
) -> int:
    """Close every open row of ``kind`` for ``user`` (optionally one job)."""
    from ..models import WorkloadSession

    qs = WorkloadSession.objects.filter(user=user, kind=kind, stopped_at__isnull=True)
    if scheduler_id is not None:
        qs = qs.filter(scheduler_id=str(scheduler_id))
    n = qs.update(stopped_at=timezone.now(), stop_reason=reason)
    if n:
        usage.invalidate(user)
    return n


def close_workloads_for_username(username: str, *, kind: str, reason: str) -> int:
    from django.contrib.auth import get_user_model

    user = get_user_model().objects.filter(username=username).first()
    if user is None:
        return 0
    return close_workloads(user, kind=kind, reason=reason)


__all__ = ["close_workloads", "close_workloads_for_username", "open_workload"]
