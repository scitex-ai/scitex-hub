"""The enforcement entry point every billable launch path calls.

Two kinds of refusal, one exception type:

* SPEND — the account's standing or its monthly cap (:mod:`.policy`).
* QUOTA — the per-user limits in ``config/settings/quotas.py`` overridden by
  ``console_app.UserQuota``. These existed before spend controls but nothing
  ever checked them.

Call sites use :func:`require_billable` (spend + the relevant quota) and turn a
:class:`Refused` into their own transport: a JSON 402/403, a terminal line, a
Django message. :func:`refusal_payload` gives them one shape to send.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal

from django.conf import settings
from django.urls import NoReverseMatch, reverse
from django.utils import timezone

from . import catalog, policy, usage
from .policy import Action, CapLevel, Standing

logger = logging.getLogger("scitex")

SECONDS_PER_HOUR = 3_600


class Refused(Exception):
    """A billable action was refused. ``str()`` is the user-facing message."""

    def __init__(
        self, code: str, message: str, *, http_status: int = 402, link: str = ""
    ):
        super().__init__(message)
        self.code = code
        self.message = message
        self.http_status = http_status
        self.link = link


@dataclass(frozen=True)
class AccountStatus:
    standing: Standing
    terms: catalog.PlanTerms
    cap_usd: Decimal
    cap_is_default: bool
    snapshot: usage.UsageSnapshot
    level: CapLevel
    percent: int
    reached_at: datetime | None
    mode: str

    @property
    def spend_usd(self) -> Decimal:
        return self.snapshot.total_usd


def spend_settings_url() -> str:
    try:
        return reverse("spend_app:settings")
    except NoReverseMatch:  # pragma: no cover - urls not mounted
        return "/accounts/settings/spend/"


def billing_url() -> str:
    try:
        return reverse("accounts_app:billing")
    except NoReverseMatch:  # pragma: no cover
        return "/accounts/settings/billing/"


def standing_for(user) -> Standing:
    from ..models import BillingAccountState

    row = BillingAccountState.objects.filter(user=user).only("state").first()
    return Standing(row.state) if row is not None else Standing.GOOD


def effective_cap(user) -> tuple[Decimal, bool, catalog.PlanTerms]:
    """(cap, is_plan_default, plan terms). A stored cap above a (lowered) plan
    maximum is clamped to the maximum rather than honoured."""
    from ..models import SpendControl

    terms = catalog.plan_terms(catalog.plan_id_for(user))
    row = SpendControl.objects.filter(user=user).first()
    if row is None or row.monthly_cap_usd is None:
        return terms.default_cap_usd, True, terms
    return min(Decimal(row.monthly_cap_usd), terms.max_cap_usd), False, terms


def account_status(user, *, fresh: bool = False, source=None) -> AccountStatus:
    from ..models import SpendAlert

    cap, is_default, terms = effective_cap(user)
    snap = usage.current_snapshot(user, fresh=fresh, source=source)
    level = policy.cap_level(snap.total_usd, cap)
    reached = (
        SpendAlert.objects.filter(user=user, period=snap.period, threshold=100)
        .values_list("created_at", flat=True)
        .first()
    )
    return AccountStatus(
        standing=standing_for(user),
        terms=terms,
        cap_usd=cap,
        cap_is_default=is_default,
        snapshot=snap,
        level=level,
        percent=policy.percent_used(snap.total_usd, cap),
        reached_at=reached,
        mode=settings.SPEND_CONTROLS["mode"],
    )


def message_for(code: str, status: AccountStatus | None = None) -> str:
    if code == "spend_cap_reached":
        detail = (
            f" (${status.spend_usd:.2f} of your ${status.cap_usd:.2f} monthly cap)"
            if status
            else ""
        )
        return (
            f"Your monthly spend cap has been reached{detail}. New compute "
            "sessions and jobs are paused until next month. You can raise your cap "
            f"in Settings > Spend controls: {spend_settings_url()}"
        )
    if code == "storage_read_only":
        return (
            "Your monthly spend cap has been reached, so your storage is read-only: "
            "nothing is deleted, and you can still read, download and delete files. "
            f"Raise your cap to upload again: {spend_settings_url()}"
        )
    if code == "account_restricted":
        return (
            "Your account is restricted because a payment did not go through. Your "
            "data is kept and readable; new compute and uploads resume once the "
            f"payment is settled: {billing_url()}"
        )
    return "This action is not available on your account right now."


def has_account(user) -> bool:
    """Whether ``user`` is a stored, signed-in account spend controls apply to.

    Anonymous visitors (and a request no auth middleware has populated) have
    nothing to bill; the view's own access check decides for them, and an
    unsaved user object has no rows to read. Both are allowed through here
    rather than raising, so the gate never replaces a view's 401/403.
    """
    return bool(getattr(user, "is_authenticated", False)) and (
        getattr(user, "pk", None) is not None
    )


def check(
    user, action: Action, *, status: AccountStatus | None = None
) -> policy.Decision:
    if not has_account(user):
        return policy.ALLOW
    status = status or account_status(user)
    decision = policy.decide(status.standing, status.level, action, mode=status.mode)
    if decision.shadowed:
        logger.warning(
            "spend[shadow]: would refuse %s for user %s (%s)",
            action.value,
            user.pk,
            decision.code,
        )
    return decision


def require(user, action: Action) -> AccountStatus | None:
    """Raise :class:`Refused` if the account may not take ``action`` now."""
    if not has_account(user):
        return None
    status = account_status(user)
    decision = check(user, action, status=status)
    if decision.refused:
        link = (
            billing_url()
            if decision.code.startswith("account_")
            else spend_settings_url()
        )
        raise Refused(decision.code, message_for(decision.code, status), link=link)
    return status


# ---------------------------------------------------------------------------
# Quotas (config/settings/quotas.py + console_app.UserQuota)
# ---------------------------------------------------------------------------


def effective_quotas(user) -> dict:
    from config.settings.quotas import get_user_quotas

    return get_user_quotas(user)


def _quota_refusal(message: str) -> Refused:
    return Refused(
        "quota_exceeded", message, http_status=403, link=spend_settings_url()
    )


def check_job_quota(
    user,
    *,
    cpus: int,
    memory_gb: int,
    time_limit_seconds: int,
    partition: str,
    status: AccountStatus | None = None,
) -> None:
    from apps.workspace.console_app.models import WorkloadSession

    q = effective_quotas(user)["slurm"]
    if int(memory_gb) > int(q["max_memory_gb_per_job"]):
        raise _quota_refusal(
            f"A job may use at most {q['max_memory_gb_per_job']} GB of memory "
            f"(requested {memory_gb} GB)."
        )
    if (
        int(time_limit_seconds) > int(q["max_runtime_hours"]) * SECONDS_PER_HOUR
    ):  # stx-allow: STX-NL001
        raise _quota_refusal(
            f"A job may run for at most {q['max_runtime_hours']} hours."
        )
    allowed = [p.strip() for p in q["allowed_partitions"] if p.strip()]
    if allowed and partition not in allowed:
        raise _quota_refusal(
            f"Partition {partition!r} is not available on your account "
            f"(allowed: {', '.join(allowed)})."
        )
    # A job nobody polled after it ended stays open; past its time limit it
    # cannot still be running, so it does not count against concurrency.
    now = timezone.now()
    running = sum(
        1
        for started, limit in WorkloadSession.objects.filter(
            user=user,
            workload=WorkloadSession.WORKLOAD_JOB,
            stopped_at__isnull=True,
        ).values_list("started_at", "max_seconds")
        if limit is None or started + timedelta(seconds=limit) > now
    )
    if running >= int(q["max_concurrent_jobs"]):
        raise _quota_refusal(
            f"You already have {running} job(s) running; the limit is "
            f"{q['max_concurrent_jobs']}."
        )
    status = status or account_status(user)
    monthly = Decimal(q["max_cpu_hours_monthly"])
    if status.snapshot.cpu_hours >= monthly:
        raise _quota_refusal(
            f"You have used {status.snapshot.cpu_hours:.1f} of your "
            f"{monthly} CPU-hours this month."
        )


def check_storage_quota(user, *, incoming_sizes: list[int]) -> None:
    q = effective_quotas(user)["storage"]
    per_file = int(q["file_upload_mb"]) * 1_048_576
    for size in incoming_sizes:
        if size > per_file:
            raise _quota_refusal(
                f"A single upload may be at most {q['file_upload_mb']} MB."
            )
    used = usage.current_snapshot(user).storage_bytes
    limit = int(q["total_gb"]) * 1_073_741_824
    if used + sum(incoming_sizes) > limit:
        raise _quota_refusal(
            f"This upload would exceed your {q['total_gb']} GB storage quota. "
            "Delete files to make room; nothing is deleted automatically."
        )


def check_project_quota(user) -> None:
    from apps.infra.project_app.models import Project

    limit = int(effective_quotas(user)["project"]["max_projects"])
    if Project.objects.filter(owner=user).count() >= limit:
        raise _quota_refusal(f"You can own at most {limit} projects.")


def require_compute(user) -> AccountStatus | None:
    return require(user, Action.START_COMPUTE)


def require_job(user, *, cpus, memory_gb, time_limit_seconds, partition) -> None:
    status = require(user, Action.SUBMIT_JOB)
    if status is not None:
        check_job_quota(
            user,
            cpus=cpus,
            memory_gb=memory_gb,
            time_limit_seconds=time_limit_seconds,
            partition=partition,
            status=status,
        )


def require_storage_write(user, *, incoming_sizes: list[int] | None = None) -> None:
    require(user, Action.WRITE_STORAGE)
    if incoming_sizes is not None and has_account(user):
        check_storage_quota(user, incoming_sizes=incoming_sizes)


def refusal_payload(exc: Refused) -> dict:
    return {
        "success": False,
        "error": exc.code,
        "message": exc.message,
        "detail": exc.message,
        "raise_cap_url": exc.link,
    }


def refusal_json(exc: Refused):
    from django.http import JsonResponse

    return JsonResponse(refusal_payload(exc), status=exc.http_status)


__all__ = [
    "AccountStatus",
    "Refused",
    "account_status",
    "check",
    "check_job_quota",
    "check_project_quota",
    "check_storage_quota",
    "effective_cap",
    "effective_quotas",
    "has_account",
    "message_for",
    "refusal_json",
    "refusal_payload",
    "require",
    "require_compute",
    "require_job",
    "require_storage_write",
    "standing_for",
]
