#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Pool CAPACITY semantics: what "available" means, and why it is zero.

WHY THIS MODULE EXISTS (measured on prod 2026-08-16 15:55Z).
PR #628 taught the health badge and the deploy gate to ask about the visitor
pool at all — a real fix for the incident it was written for (all 16 slots
quarantined, every signal green). But its predicate was NARROWER than the
property it claims to protect. It keys on::

    ready == 0        -> red
    quarantined > 0   -> warning

which catches "everything QUARANTINED" and misses "everything HELD". Held is
the commoner shape. A real anonymous visitor entered the site at 15:55Z and
was handed ``data-session-role="readonly_visitor"`` — the shared fallback
account, i.e. the product path was down for them — while the pool reported::

    total=16  quarantined=0  workspace-clean=12  ALLOCATABLE=1

Both guards passed. ``quarantined > 0`` was false, and ``ready == 0`` was
false. Nothing was lying and nothing was useful.

THE CORRECTION. "Clean" is not "available". A slot is allocatable only when
nobody holds it:

    allocatable = NOT quarantined AND NOT is_active AND workspace_ready

That is the predicate ``PoolAllocator._try_allocate_slot`` actually serves, so
it is the only number that answers "can the NEXT visitor get a real slot?".
Deliberately NOT the looser ``NOT (is_active AND expires_at > now)``: a row
that is ``is_active`` but stale is not served either — the allocator releases
it, sets ``workspace_ready=False`` and enqueues an async wipe, then REFUSES it
to the requester who found it. Counting such rows as available would be wrong
in the optimistic direction, which is the exact failure mode of ``free``.

AND WHY IT IS ZERO. Zero-allocatable has four causes with four DIFFERENT
repairs, and naming the wrong one is worse than naming none: on a saturated
pool ``reconcile_visitor_slots --repair-only`` re-cleans only
``quarantined=True`` rows, so it is a no-op that reads to the operator as "I
ran the documented fix and nothing changed". This module attributes the cause
and hands back the repair that matches it.

MEASUREMENT AND INTERPRETATION LIVE TOGETHER, on purpose. Every bug in this
area has been a counter and a reader drifting apart on what "available" means.
:func:`measure_pool` is the only ORM in the module; everything below it is a
pure function over a status dict, so the health view, the deploy gate and the
tests share ONE definition and the pure half needs no database.

Django is imported INSIDE :func:`measure_pool`, never at module scope, so
importing this module can never fail. The health endpoint depends on that: a
status page that 500s because the thing it reports on failed to import tells
the operator strictly less than one that says "could not measure".
"""

from __future__ import annotations


def measure_pool(pool_size: int) -> dict:
    """Count the pool into the capacity partition. The one ORM read.

    Returns the six partition buckets (see :func:`partition_pool_status`) plus
    the legacy keys ``allocated`` (== ``live``), ``free``, ``expired`` and
    ``ready`` (== ``allocatable``, identical predicate — kept because three
    call sites and the #628 regression suite read that name).

    ``free``, ``allocatable`` and "the workspace is clean" are THREE DIFFERENT
    NUMBERS and only the middle one governs. ``free`` is merely
    total - occupied, so it counts slots that can never be handed out; a UI
    that showed ``free`` claimed spare capacity while every visitor was
    correctly downgraded to read-only (prod 2026-07-30). "Clean" is looser
    still: on 2026-08-16 15:55Z twelve slots were clean and zero quarantined,
    while exactly ONE was allocatable and a real visitor was being handed the
    shared readonly account.

    Every count is bounded by ``visitor_number <= pool_size``. The allocator
    only walks ``range(1, pool_size + 1)``, so rows left behind by a SHRUNK
    pool are slots that can never be handed out; counting them inflated
    ``ready`` with unreachable capacity.
    """
    from django.utils import timezone

    from apps.infra.project_app.models import VisitorAllocation

    from .slot_lifecycle import stale_allocation_q

    now = timezone.now()
    stale = stale_allocation_q(now)

    rows = VisitorAllocation.objects.filter(visitor_number__lte=pool_size)
    usable = rows.filter(quarantined=False)

    # "Live" = a genuinely LIVE visitor session: ``is_active`` AND neither
    # expired nor idle. A stale row (``is_active`` with a future ``expires_at``
    # but a weeks-old ``last_activity``) is NOT live — it is reclaimable.
    # Counting only ``expires_at`` (the old behaviour) let such zombie rows
    # wedge the pool at free=0 (prod 2026-07-09).
    live = usable.filter(is_active=True).exclude(stale).count()

    # Reclaimable is its OWN bucket rather than folded into allocatable:
    # ``_try_allocate_slot`` does not serve these. It releases the stale row,
    # sets ``workspace_ready=False``, enqueues the async wipe, and then REFUSES
    # the slot to the very request that found it.
    reclaimable = usable.filter(is_active=True).filter(stale).count()

    allocatable = usable.filter(is_active=False, workspace_ready=True).count()
    resetting = usable.filter(is_active=False, workspace_ready=False).count()

    quarantined = rows.filter(quarantined=True).count()
    expired = rows.filter(is_active=True, expires_at__lte=now).count()

    # A slot number with no row is refused by the allocator and, before this
    # change, appeared in NO bucket — so the buckets silently failed to sum to
    # ``total`` on a partly-provisioned pool.
    missing = max(0, pool_size - rows.count())

    return {
        "total": pool_size,
        "allocated": live,
        "free": max(0, pool_size - live),
        "expired": expired,
        "ready": allocatable,
        "allocatable": allocatable,
        "live": live,
        "reclaimable": reclaimable,
        "resetting": resetting,
        "quarantined": quarantined,
        "missing": missing,
    }


# ---------------------------------------------------------------------------
# Causes of zero capacity, each with its own repair.
# ---------------------------------------------------------------------------

CAUSE_UNPROVISIONED = "unprovisioned"
CAUSE_QUARANTINED = "quarantined"
CAUSE_RESETTING = "resetting"
CAUSE_SATURATED = "saturated"

# Bare ``manage.py`` form on purpose: the deploy gate already wraps its output
# in ``docker exec``, and an operator reading this inside the container needs
# no prefix. The one docker-prefixed rendering lives in the health view, built
# FROM these strings so the two can never disagree.
REPAIR_BY_CAUSE = {
    # Slots exist but failed wipe/verify. ``--repair-only`` is load-bearing:
    # the PLAIN reconcile's Phase 1 quarantines every slot including healthy
    # ones, so recommending it against a live, partially degraded pool makes
    # things strictly worse.
    CAUSE_QUARANTINED: "python manage.py reconcile_visitor_slots --repair-only",
    # No rows at all for these slot numbers — nothing to repair, only to create.
    CAUSE_UNPROVISIONED: (
        "python manage.py create_visitor_pool, then "
        "python manage.py reconcile_visitor_slots --repair-only"
    ),
    # Released slots awaiting the async wipe+verify (~10s/slot on vis_queue).
    # The pool is not broken; the worker is either busy or dead. Naming a pool
    # repair here would send the operator to the wrong process entirely.
    CAUSE_RESETTING: (
        "wait — the async wipe+verify is ~10s per slot; if it does not clear, "
        "the wipe worker is the fault, not the pool: "
        "docker logs --tail 100 scitex-hub-<env>-celery_worker_vis-1"
    ),
    # Every slot is legitimately held by a session. No pool command helps.
    CAUSE_SATURATED: (
        "capacity, not corruption: raise SCITEX_HUB_VISITOR_POOL_SIZE, or "
        "shorten the hold (SESSION_LIFETIME_HOURS / IDLE_TIMEOUT_MINUTES)"
    ),
}

# Warn below this many allocatable slots.
#
# NOT because 2 is a magic number — because the downgrade is BINARY AND STICKY
# and recovery is SLOW. A visitor who lands on ``readonly-visitor`` stays there
# for the whole session; there is no queue and no retry. A consumed slot then
# returns only after the hold ends (a 120s probation promoted to a full hour by
# the first heartbeat, or 30 idle minutes) PLUS a full wipe+verify. So at
# allocatable==1 the SECOND visitor within the next half hour gets the shared
# account. Two visitors in half an hour on a public site is the ordinary case,
# not a burst — green there is a false claim about what the next visitor
# experiences.
#
# This is a FLOOR, not the answer. The principled threshold is "allocatable <
# peak concurrent live over the last 24h" (the site already records that in
# ``ServerMetrics.visitor_pool_allocated``); wiring that history read is
# deliberately left out of this change.
WARN_BELOW_ALLOCATABLE = 2

_PARTITION_KEYS = ("live", "reclaimable", "resetting", "missing")


def _int(value) -> int:
    """Coerce a status field to a non-negative int; unusable values read 0."""
    try:
        return max(0, int(value or 0))
    except (TypeError, ValueError):
        return 0


def _present(pool_status: dict, key: str) -> bool:
    return pool_status.get(key) is not None


def partition_pool_status(pool_status: dict) -> dict:
    """Normalise any pool-status dict into the six-bucket capacity partition.

    Buckets, which must sum to ``total``:

    ``allocatable``  servable to the next visitor right now.
    ``live``         held by a genuinely live session (not expired, not idle).
    ``reclaimable``  held by a stale row; capacity returns, but only after a
                     release + wipe + verify, not on this request.
    ``resetting``    released and awaiting the async wipe+verify.
    ``quarantined``  failed wipe/verify; never allocated until re-verified.
    ``missing``      slot numbers inside the pool with no row at all.

    Accepts the PRE-#628 dict shape too (``total``/``ready``/``quarantined``/
    ``allocated`` only). Back-compat is not politeness here: three live call
    sites and the existing regression suite pass exactly that shape, and a
    normaliser that only understood the new keys would silently read every one
    of them as an empty pool.

    Precedence for ``allocatable``: an explicit ``allocatable`` key wins; else,
    if the producer supplied any partition key, it is the residual after every
    unavailable bucket (the partition is ground truth about who HOLDS what,
    whereas ``ready`` alone cannot distinguish "clean and free" from "clean and
    held"); else it falls back to ``ready``, whose predicate it matches.
    """
    total = _int(pool_status.get("total"))
    quarantined = _int(pool_status.get("quarantined"))
    resetting = _int(pool_status.get("resetting"))
    reclaimable = _int(pool_status.get("reclaimable"))

    # ``allocated`` is the legacy name for ``live``; identical predicate.
    live = _int(
        pool_status.get("live")
        if _present(pool_status, "live")
        else pool_status.get("allocated")
    )

    if _present(pool_status, "allocatable"):
        allocatable = _int(pool_status.get("allocatable"))
    elif any(_present(pool_status, key) for key in _PARTITION_KEYS):
        allocatable = max(0, total - live - reclaimable - resetting - quarantined)
    else:
        allocatable = _int(pool_status.get("ready"))

    unavailable = live + reclaimable + resetting + quarantined
    if _present(pool_status, "missing"):
        missing = _int(pool_status.get("missing"))
    else:
        missing = max(0, total - allocatable - unavailable)

    accounted = allocatable + unavailable + missing
    return {
        "total": total,
        "allocatable": allocatable,
        "live": live,
        "reclaimable": reclaimable,
        "resetting": resetting,
        "quarantined": quarantined,
        "missing": missing,
        # Stated, never hoped for. A partition that does not sum to the pool
        # size means the producer and this reader disagree about what a slot
        # is; say so rather than classify confidently on nonsense.
        "inconsistent": total > 0 and accounted != total,
    }


def capacity_cause(partition: dict) -> str:
    """Attribute zero (or near-zero) capacity to its dominant cause.

    Largest bucket wins; ties break in declaration order, which runs from the
    most specific and most actionable repair to the least. Only meaningful
    when ``allocatable`` is low — a healthy pool has no cause to attribute.
    """
    candidates = (
        (partition["missing"], CAUSE_UNPROVISIONED),
        (partition["quarantined"], CAUSE_QUARANTINED),
        (partition["resetting"], CAUSE_RESETTING),
        (partition["live"] + partition["reclaimable"], CAUSE_SATURATED),
    )
    count, cause = max(candidates, key=lambda item: item[0])
    if count <= 0:
        # Every bucket empty while capacity is zero: the pool has no usable
        # rows at all, which is the unprovisioned shape however it got there.
        return CAUSE_UNPROVISIONED
    return cause


def describe_partition(partition: dict) -> str:
    """One-line census of every bucket.

    ALWAYS reports all of them, including the zeros. Naming a single cause must
    not hide a second fault, and "0 quarantined" is itself the load-bearing
    fact that tells the operator not to reach for the reconcile.
    """
    return (
        f"{partition['live']} held by live sessions, "
        f"{partition['reclaimable']} reclaimable, "
        f"{partition['resetting']} awaiting wipe+verify, "
        f"{partition['quarantined']} quarantined, "
        f"{partition['missing']} missing"
    )


# EOF
