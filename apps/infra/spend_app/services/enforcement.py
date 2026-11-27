"""Periodic evaluation: alerts, then the running-work grace window and stop.

Called by the Celery beat sweep (``spend_app.tasks``) and, for interactive
terminals, by the terminal broker's reaper thread through
:func:`terminal_verdict` (the broker owns those PTYs, so only it can stop them).

At 100 % the 100 % alert's ``created_at`` starts the grace window. During the
window work keeps running and the holder has the warning (email + in-app, and
a line in every attached terminal). When it ends:

* SLURM batch jobs recorded in ``WorkloadSession`` are ``scancel``-ed;
* queued/running ``PlatformJob`` rows are cancelled through ``JobQueue``;
* project services (notebook, TensorBoard) are stopped;
* terminals are stopped by the broker reaper.

Each stop closes its ``WorkloadSession`` with ``stop_reason=spend_cap`` (or
``restricted``). Storage is never touched.
"""

from __future__ import annotations

import logging
from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from . import gate, notify, policy

logger = logging.getLogger("scitex")


def _grace() -> timedelta:
    return timedelta(minutes=settings.SPEND_CONTROLS["running_grace_minutes"])


def verdict_for(status: gate.AccountStatus, *, now=None) -> policy.RunningVerdict:
    return policy.running_verdict(
        status.standing,
        status.level,
        reached_at=status.reached_at,
        now=now or timezone.now(),
        grace=_grace(),
        mode=status.mode,
    )


def _stop_reason(verdict: policy.RunningVerdict) -> str:
    from ..models import WorkloadSession

    return (
        WorkloadSession.StopReason.RESTRICTED
        if verdict.reason.startswith("account_")
        else WorkloadSession.StopReason.SPEND_CAP
    )


def stop_running_work(user, verdict: policy.RunningVerdict) -> dict:
    """Stop the non-terminal billable work of ``user``. Returns counts."""
    from ..models import WorkloadSession

    reason = _stop_reason(verdict)
    stopped = {"jobs": 0, "platform_jobs": 0, "services": 0}

    for row in WorkloadSession.objects.filter(
        user=user, kind=WorkloadSession.Kind.JOB, stopped_at__isnull=True
    ):
        if row.scheduler_id:
            try:
                from apps.workspace.console_app.services.slurm.job_operations import (
                    cancel_job,
                )

                result = cancel_job(int(row.scheduler_id))
                if not result.get("success"):
                    logger.error(
                        "spend: scancel %s for user %s failed: %s",
                        row.scheduler_id,
                        user.pk,
                        result.get("message"),
                    )
                    continue
            except (ValueError, FileNotFoundError) as exc:
                logger.error("spend: cannot scancel %s: %s", row.scheduler_id, exc)
                continue
        row.stopped_at = timezone.now()
        row.stop_reason = reason
        row.save(update_fields=["stopped_at", "stop_reason"])
        stopped["jobs"] += 1

    try:
        from apps.infra.platform_app.models import PlatformJob
        from apps.infra.platform_app.services.jobqueue.executor import JobQueue

        queue = JobQueue()
        for job in PlatformJob.objects.filter(
            owner=user,
            status__in=(PlatformJob.Status.QUEUED, PlatformJob.Status.RUNNING),
        ):
            if queue.cancel(str(job.pk)):
                stopped["platform_jobs"] += 1
    except ImportError:  # pragma: no cover
        pass

    try:
        from apps.workspace.console_app.models import ProjectService
        from apps.workspace.console_app.services.project_service_manager import (
            ProjectServiceManager,
        )

        manager = ProjectServiceManager()
        for service in ProjectService.objects.filter(
            user=user, status__in=("starting", "running")
        ):
            if manager.stop_service(user, str(service.service_id)):
                stopped["services"] += 1
        if stopped["services"]:
            from .workloads import close_workloads

            close_workloads(user, kind=WorkloadSession.Kind.SERVICE, reason=reason)
    except ImportError:  # pragma: no cover
        pass

    if any(stopped.values()):
        from .dunning import _log

        _log(user, "running_work_stopped", detail_reason=verdict.reason, **stopped)
    return stopped


def sweep_user(user, *, now=None) -> dict:
    """Recompute, alert, and enforce for one account."""
    status = gate.account_status(user, fresh=True)
    notify.evaluate_alerts(user, status)
    if status.reached_at is None and status.level is policy.CapLevel.REACHED:
        status = gate.account_status(user)  # pick up the alert just created
    verdict = verdict_for(status, now=now)
    result = {"level": int(status.level), "verdict": verdict.verdict.value}
    if verdict.verdict is policy.Run.STOP:
        result.update(stop_running_work(user, verdict))
    return result


def users_to_sweep(*, active_only: bool):
    """Accounts with billable work in flight (``active_only``), or every
    account that used the product in the last 35 days."""
    from django.contrib.auth import get_user_model

    from ..models import BillingAccountState, WorkloadSession

    User = get_user_model()
    open_ids = set(
        WorkloadSession.objects.filter(stopped_at__isnull=True).values_list(
            "user_id", flat=True
        )
    )
    try:
        from apps.infra.platform_app.models import PlatformJob

        open_ids |= set(
            PlatformJob.objects.filter(
                status__in=(PlatformJob.Status.QUEUED, PlatformJob.Status.RUNNING)
            ).values_list("owner_id", flat=True)
        )
    except ImportError:  # pragma: no cover
        pass
    open_ids |= set(
        BillingAccountState.objects.exclude(
            state=BillingAccountState.State.GOOD
        ).values_list("user_id", flat=True)
    )
    if active_only:
        return User.objects.filter(pk__in=open_ids, is_active=True)
    since = timezone.now() - timedelta(days=35)
    return User.objects.filter(is_active=True).filter(
        last_login__gte=since
    ) | User.objects.filter(pk__in=open_ids)


def require_terminal(payer) -> None:
    """Gate for opening a terminal on ``payer``'s interactive allocation.

    Re-attaching to an allocation that is already running is NOT new work: it
    is allowed through the grace window (so the holder can save and exit) and
    refused only once that work is due to stop. Opening a new allocation is new
    billable compute and follows :func:`gate.require_compute`.
    """
    from ..models import WorkloadSession

    running = WorkloadSession.objects.filter(
        user=payer, kind=WorkloadSession.Kind.TERMINAL, stopped_at__isnull=True
    ).exists()
    if not running:
        gate.require_compute(payer)
        return
    status = gate.account_status(payer)
    verdict = verdict_for(status)
    if verdict.verdict is policy.Run.STOP:
        code = verdict.reason
        link = (
            gate.billing_url()
            if code.startswith("account_")
            else gate.spend_settings_url()
        )
        raise gate.Refused(code, gate.message_for(code, status), link=link)


def terminal_verdict(username: str) -> policy.RunningVerdict:
    """For the terminal broker: may this user's interactive session continue?"""
    from django.contrib.auth import get_user_model

    user = get_user_model().objects.filter(username=username).first()
    if user is None:
        return policy.RunningVerdict(policy.Run.RUN)
    status = gate.account_status(user)
    return verdict_for(status)


__all__ = [
    "stop_running_work",
    "sweep_user",
    "terminal_verdict",
    "users_to_sweep",
    "verdict_for",
]
