"""Month-to-date usage, read through ONE interface.

:class:`UsageSource` is the contract. The append-only usage ledger (hub issue
#1232, design §3.1) will implement it from rated ledger events; nothing else in
spend controls reads usage any other way, so swapping the source is one line in
:func:`get_usage_source`.

Until the ledger exists, :class:`ProvisionalUsageSource` reads the best source
available today for each resource and marks every line ``provisional=True``
with the source it used. The UI shows that label next to every figure.

=========  ==========================================  ========================
resource   provisional source                          known gap
=========  ==========================================  ========================
compute    ``console_app.WorkloadSession`` rows        allocation x wall time
           (terminal, services, SLURM jobs) +          from launch/stop records,
           ``PlatformJob`` start/finish; billed by     not sacct/cgroup; a job
           ALLOCATION (cores x wall time, 4 GiB/core   with no stop record is
           bundled); concurrent terminal rows of a     charged to its time limit
           user share one allocation, billed once
storage    on-demand scan of the user's data root      point-in-time size held
           (``filesystem.get_storage_usage``), cached  constant for the month
           backup snapshots live outside that root,
           so they are never counted (decision b)
egress     not measured anywhere yet                   always 0 until the
                                                       egress collector lands
=========  ==========================================  ========================
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from datetime import timezone as dt_timezone
from decimal import ROUND_HALF_UP, Decimal
from typing import Protocol

from django.conf import settings
from django.core.cache import cache
from django.utils import timezone

from . import catalog

logger = logging.getLogger("scitex")

GIB = 1_024**3
SECONDS_PER_HOUR = Decimal("3600")  # stx-allow: STX-NL001
SECONDS_PER_MONTH = Decimal("2629800")  # 30.4375 days, as design §3.3.4
CENT = Decimal("0.0001")


@dataclass(frozen=True)
class UsageLine:
    resource: str
    quantity: Decimal
    unit: str
    amount_usd: Decimal
    source: str
    provisional: bool
    note: str = ""


@dataclass(frozen=True)
class UsageSnapshot:
    user_id: int
    period: str
    window_start: datetime
    window_end: datetime
    lines: tuple = field(default_factory=tuple)
    #: Included compute credit applied against compute (plan allowance).
    compute_credit_usd: Decimal = Decimal("0")
    #: Core-hours allocated this period (for the monthly CPU-hour quota).
    cpu_hours: Decimal = Decimal("0")
    storage_bytes: int = 0

    @property
    def provisional(self) -> bool:
        return any(line.provisional for line in self.lines)

    @property
    def gross_usd(self) -> Decimal:
        return sum((line.amount_usd for line in self.lines), Decimal("0"))

    @property
    def total_usd(self) -> Decimal:
        compute = sum(
            (l.amount_usd for l in self.lines if l.resource == "compute"), Decimal("0")
        )
        credit = min(self.compute_credit_usd, compute)
        return (self.gross_usd - credit).quantize(CENT, rounding=ROUND_HALF_UP)


class UsageSource(Protocol):
    """What spend controls needs from usage. The ledger (#1232) implements it."""

    name: str

    def snapshot(self, user, *, start: datetime, end: datetime) -> UsageSnapshot:
        """Rated usage for ``user`` in ``[start, end)``, in USD."""


def period_bounds(now: datetime | None = None) -> tuple[str, datetime, datetime]:
    """The billing month containing ``now`` (UTC calendar month, provisional:
    the ledger will align periods with the provider's billing cycle)."""
    now = now or timezone.now()
    now = now.astimezone(dt_timezone.utc)
    start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    if start.month == 12:
        nxt = start.replace(year=start.year + 1, month=1)
    else:
        nxt = start.replace(month=start.month + 1)
    return f"{start:%Y-%m}", start, nxt


def _overlap_seconds(start, stop, window_start, window_end) -> Decimal:
    lo = max(start, window_start)
    hi = min(stop, window_end)
    return Decimal(max(0.0, (hi - lo).total_seconds()))


def _billed_span(row, window_start, window_end):
    """``(lo, hi, cpus, memory_gb)`` of ``row`` inside the window, or None.

    A row with no stop record runs to the window end, capped at its time
    limit (``max_seconds``)."""
    stop = row.stopped_at
    if stop is None:
        stop = window_end
        if row.max_seconds:
            stop = min(stop, row.started_at + timedelta(seconds=row.max_seconds))
    lo = max(row.started_at, window_start)
    hi = min(stop, window_end)
    if hi <= lo:
        return None
    return lo, hi, max(1, row.cpus), row.memory_gb


def _merge_concurrent(spans):
    """Split overlapping spans into disjoint pieces, each carrying the
    largest cpus and memory of the spans in force over it."""
    edges = sorted({t for lo, hi, _, _ in spans for t in (lo, hi)})
    pieces = []
    for a, b in zip(edges, edges[1:]):
        live = [(c, m) for lo, hi, c, m in spans if lo <= a and hi >= b]
        if live:
            pieces.append((a, b, max(c for c, _ in live), max(m for _, m in live)))
    return pieces


def _charge(span, rate) -> tuple[Decimal, Decimal]:
    """USD and core-hours of one allocation span (cores x wall time, memory
    beyond the bundled GiB per core as an add-on)."""
    lo, hi, cpus, memory_gb = span
    hours = Decimal((hi - lo).total_seconds()) / SECONDS_PER_HOUR
    cpus = Decimal(cpus)
    extra_mem = max(Decimal("0"), Decimal(memory_gb) - cpus * rate.gib_per_cpu_unit)
    usd = cpus * hours * rate.cpu_unit_hour_usd
    usd += extra_mem * hours * rate.memory_addon_gib_hour_usd
    return usd, cpus * hours


class ProvisionalUsageSource:
    """PROVISIONAL: today's best source per resource. Replaced by #1232."""

    name = "provisional"

    def __init__(self, *, storage_bytes_fn=None, now_fn=None, billing_policy_fn=None):
        self._storage_bytes_fn = storage_bytes_fn or _scan_storage_bytes
        self._now_fn = now_fn or timezone.now
        self._billing_policy_fn = billing_policy_fn or catalog.billing_policy

    def snapshot(self, user, *, start, end) -> UsageSnapshot:
        now = self._now_fn()
        window_end = min(end, now)
        terms = catalog.plan_terms(catalog.plan_id_for(user))
        rate = catalog.rates()
        lines = []

        compute_usd, cpu_hours, n = self._compute(user, start, window_end, rate)
        lines.append(
            UsageLine(
                resource="compute",
                quantity=cpu_hours.quantize(CENT),
                unit="core-hour",
                amount_usd=compute_usd.quantize(CENT, rounding=ROUND_HALF_UP),
                source="workload_sessions+platform_jobs",
                provisional=True,
                note=f"{n} workload(s), billed by allocation from launch/stop records",
            )
        )

        policy = self._billing_policy_fn()
        if policy.storage_counts_backups:
            # Decision b (2026-11-27) is that backups are NOT counted; the scan
            # below covers the user's data root only, and backup snapshots live
            # outside it. A catalog saying otherwise needs a meter that counts
            # them, not a silent under-charge.
            raise catalog.CatalogError(
                "billing_policy.storage_counts_backups is true, but the storage "
                "meter scans the user's data root only and cannot count backups"
            )
        storage_bytes = int(self._storage_bytes_fn(user))
        over_gb = max(
            Decimal("0"), Decimal(storage_bytes) / GIB - terms.included_storage_gb
        )
        elapsed = Decimal(max(0.0, (window_end - start).total_seconds()))
        tier_rate = rate.storage_gb_month_usd.get(terms.storage_tier, Decimal("0"))
        storage_usd = over_gb * tier_rate * (elapsed / SECONDS_PER_MONTH)
        lines.append(
            UsageLine(
                resource="storage",
                quantity=(Decimal(storage_bytes) / GIB).quantize(CENT),
                unit="GB",
                amount_usd=storage_usd.quantize(CENT, rounding=ROUND_HALF_UP),
                source="filesystem_scan",
                provisional=True,
                note=(
                    f"{terms.included_storage_gb} GB included ({terms.storage_tier}); "
                    "backup copies are not counted; "
                    "current size held constant for the month"
                ),
            )
        )
        lines.append(
            UsageLine(
                resource="egress",
                quantity=Decimal("0"),
                unit="GB",
                amount_usd=Decimal("0"),
                source="unmeasured",
                provisional=True,
                note="Data transfer is not measured yet; not charged",
            )
        )
        period, _, _ = period_bounds(start)
        return UsageSnapshot(
            user_id=user.pk,
            period=period,
            window_start=start,
            window_end=window_end,
            lines=tuple(lines),
            compute_credit_usd=terms.included_compute_credit_usd,
            cpu_hours=cpu_hours,
            storage_bytes=storage_bytes,
        )

    def _compute(self, user, start, end, rate):
        from apps.workspace.console_app.models import WorkloadSession

        total = Decimal("0")
        core_hours = Decimal("0")
        count = 0
        rows = WorkloadSession.objects.filter(user=user, started_at__lt=end).exclude(
            stopped_at__lt=start
        )
        terminal_spans = []
        for row in rows:
            span = _billed_span(row, start, end)
            if span is None:
                continue
            count += 1
            if row.workload == WorkloadSession.WORKLOAD_TERMINAL:
                terminal_spans.append(span)
                continue
            usd, hours = _charge(span, rate)
            total += usd
            core_hours += hours
        # Every terminal tab of a user runs on ONE interactive allocation, so
        # overlapping terminal rows are billed once (the largest allocation
        # in force), never once per tab.
        for span in _merge_concurrent(terminal_spans):
            usd, hours = _charge(span, rate)
            total += usd
            core_hours += hours

        try:
            from apps.infra.platform_app.models import PlatformJob

            jobs = PlatformJob.objects.filter(
                owner=user, started_at__isnull=False, started_at__lt=end
            ).exclude(finished_at__lt=start)
        except Exception:  # pragma: no cover - app not installed
            jobs = []
        for job in jobs:
            stop = job.finished_at or end
            secs = _overlap_seconds(job.started_at, stop, start, end)
            if secs <= 0:
                continue
            count += 1
            hours = secs / SECONDS_PER_HOUR
            core_hours += hours
            total += hours * rate.cpu_unit_hour_usd
        return total, core_hours, count


def _scan_storage_bytes(user) -> int:
    """PROVISIONAL storage figure: a scan of the user's data root, cached."""
    key = f"spend:storage-bytes:{user.pk}"
    cached = cache.get(key)
    if cached is not None:
        return int(cached)
    try:
        from apps.infra.project_app.services.filesystem.operations import (
            get_storage_usage,
        )

        total = int(get_storage_usage(user).get("total_size", 0))
    except Exception:
        logger.exception("spend: storage scan failed for user %s", user.pk)
        raise
    cache.set(key, total, 600)
    return total


def get_usage_source() -> UsageSource:
    """The one place the usage source is chosen. #1232 swaps this line."""
    return ProvisionalUsageSource()


def current_snapshot(
    user, *, source: UsageSource | None = None, fresh=False
) -> UsageSnapshot:
    """Month-to-date usage for ``user``, cached briefly for request paths."""
    period, start, end = period_bounds()
    key = f"spend:snapshot:{user.pk}:{period}"
    if not fresh and source is None:
        cached = cache.get(key)
        if cached is not None:
            return cached
    snap = (source or get_usage_source()).snapshot(user, start=start, end=end)
    if source is None:
        cache.set(key, snap, settings.SPEND_CONTROLS["usage_cache_seconds"])
    return snap


def invalidate(user) -> None:
    invalidate_user_id(user.pk)


def invalidate_user_id(user_id: int) -> None:
    period, _, _ = period_bounds()
    cache.delete(f"spend:snapshot:{user_id}:{period}")


__all__ = [
    "ProvisionalUsageSource",
    "UsageLine",
    "UsageSnapshot",
    "UsageSource",
    "current_snapshot",
    "get_usage_source",
    "invalidate",
    "invalidate_user_id",
    "period_bounds",
]
