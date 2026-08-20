#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Visitor-pool health check — the product path that was down while all green.

WHY THIS MODULE EXISTS (incident 2026-08-16, measured on the prod host).
Every deploy quarantines all 16 visitor slots. That is the boot fail-safe in
``entrypoint-prod.sh`` and it is correct: after a restart no slot's on-disk
state can be trusted. Slots return only as ``celery_worker_vis`` verifies each
one clean.

On that day they never returned. The image was built 22:06:16 JST, the django
container was recreated 22:08:34 JST, and for ~1h35m EVERY anonymous visitor
was funnelled onto the single shared ``readonly-visitor`` account. Throughout,
``/api/server-health/`` reported ``"healthy"`` with an empty ``issues[]`` — and
it was not lying. Postgres, Redis, SSH, the API probes, SLURM, apptainer, the
containers and the data-dir permissions were all genuinely fine. The endpoint
was answering a question that did not include the visitor pool. A human
noticed the outage; no signal did.

The probe already existed — ``PoolAllocator.get_pool_status`` computes
``ready`` — and three call sites (``collect_server_metrics``, the realtime API,
the history API) read that dict and threw ``ready``/``quarantined`` away. So
this is not "add a probe"; it is "stop dropping the field on the floor".

WHY IT WAS AMENDED (measured 2026-08-16 15:55Z, the SAME day).
The first version of this module keyed on ``ready == 0`` / ``quarantined > 0``.
That catches "everything QUARANTINED" and misses "everything HELD" — the
commoner shape. Hours after the first incident, a real anonymous visitor was
handed ``data-session-role="readonly_visitor"`` while the pool read 16 total,
0 quarantined, 12 workspace-clean and ONE allocatable. Both conditions were
false and the badge stayed green. It now keys on ``allocatable`` and names the
CAUSE of zero capacity, because the four causes have four different repairs
and the wrong one is worse than none. See ``visitor_pool.pool_health``.

Kept in its own module rather than appended to ``health_checks.py`` because
that file is already at its line ceiling, and because the visitor pool is a
product surface rather than an infrastructure daemon.
"""

from __future__ import annotations

import logging

logger = logging.getLogger("scitex")

# Every symbol this module needs from the visitor-pool package is imported
# INSIDE the functions below, never at module scope. That is not stylistic:
# ``apps.infra.project_app.services.__init__`` reaches the ORM on import, so a
# module-level import here would make this file — and therefore the whole
# ``/api/server-health/`` view tree — unimportable before ``apps.populate()``.
# A status page that cannot be imported because the thing it reports on is sick
# tells the operator strictly less than one that says "could not measure".
CAUSE_QUARANTINED = "quarantined"

# The repair, named inside the issue text itself. An issues[] entry that states
# the symptom without naming the fix hands the next operator exactly the
# archaeology this incident already cost (constitution §2). ``--repair-only`` is
# deliberate and load-bearing: the PLAIN reconcile quarantines every slot
# including healthy ones, so recommending it against a live, partially degraded
# pool would make things strictly worse.
#
# Spelled out rather than composed from ``REPAIR_BY_CAUSE`` only because of the
# lazy-import rule above; ``test_repair_hint_matches_the_single_source`` pins
# the two to the same string so they cannot drift.
VISITOR_POOL_REPAIR_HINT = (
    "docker exec scitex-hub-prod-django-1 "
    "python manage.py reconcile_visitor_slots --repair-only"
)


def _capacity_api():
    """Lazily load the shared capacity semantics. See the note above."""
    from apps.infra.project_app.services.visitor_pool.pool_health import (
        REPAIR_BY_CAUSE,
        WARN_BELOW_ALLOCATABLE,
        capacity_cause,
        describe_partition,
        partition_pool_status,
    )

    # The quarantine repair is the only one with a docker-prefixed rendering
    # (the badge is read on a laptop, outside the container). The others are
    # already self-contained instructions.
    hints = dict(REPAIR_BY_CAUSE)
    hints[CAUSE_QUARANTINED] = VISITOR_POOL_REPAIR_HINT
    return (
        partition_pool_status,
        capacity_cause,
        describe_partition,
        hints,
        WARN_BELOW_ALLOCATABLE,
    )


def classify_visitor_pool(pool_status: dict) -> dict:
    """Map a pool-status dict to a health entry. Pure function, no I/O.

    ``allocatable`` — never ``free``, and never "the workspace is clean" — is
    the number that answers "can the NEXT visitor get a real slot?". Allocation
    requires ``quarantined=False`` AND ``is_active=False`` AND
    ``workspace_ready=True``; a slot failing any of the three is not servable
    however healthy it looks.

    WHY THIS IS NOT #628's PREDICATE. That version keyed on ``ready == 0`` or
    ``quarantined > 0``, which catches "everything QUARANTINED" (the incident
    it was written for) and misses "everything HELD", which is the commoner
    shape. Measured on prod 2026-08-16 15:55Z: 16 slots, 0 quarantined, 12
    workspace-clean, ONE allocatable, and a real anonymous visitor entering
    the site was handed ``data-session-role="readonly_visitor"`` — the shared
    fallback account. Both of #628's conditions were false. The badge was
    green while the product path was, for that visitor, down.

    Severity:

    ``allocatable == 0`` -> ``unhealthy``, i.e. overall ``"error"`` and the RED
        dot. Deliberately not ``"warning"``. The anonymous-visitor product path
        is entirely down, and ``issues[]`` renders only in the notification
        bell, which is wrapped in ``{% if DEBUG or user.is_staff %}``. Only the
        status colour reaches a non-staff visitor, and only ``"error"`` moves
        it off green. Filing a total outage as a warning would reproduce the
        incident for everyone who is not staff.

        The message NAMES THE CAUSE and the repair that matches it. Naming the
        wrong repair is worse than naming none: against a saturated pool
        ``reconcile_visitor_slots --repair-only`` touches only
        ``quarantined=True`` rows, so it is a no-op that reads to the operator
        as "I ran the documented fix and nothing changed".

    ``0 < allocatable < WARN_BELOW_ALLOCATABLE`` -> ``warning``. One arrival
        consumes the last slot and it does not come back for tens of minutes,
        so green here is a false claim about the next visitor.

    ``quarantined > 0`` with capacity remaining -> ``warning``. Quarantine
        never self-heals; capacity only decreases until someone repairs.
        Keyed on ``quarantined``, NOT on ``allocatable < total``: a slot in USE
        is legitimately not allocatable, so ``allocatable < total`` would raise
        an alarm every time a visitor showed up.

    ``resetting > 0`` alone -> NOT a warning. It is the normal post-release and
        post-deploy transient; alarming on it would fire on every deploy, and
        an alarm that fires on every deploy gets muted.

    otherwise -> ``healthy``.
    """
    (
        partition_pool_status,
        capacity_cause,
        describe_partition,
        hint_by_cause,
        warn_below,
    ) = _capacity_api()

    part = partition_pool_status(pool_status)
    total = part["total"]
    allocatable = part["allocatable"]
    quarantined = part["quarantined"]

    entry = {
        "total": total,
        # ``ready`` kept as an alias of ``allocatable``: same predicate, and
        # three live consumers plus the #628 suite read that name.
        "ready": allocatable,
        "allocatable": allocatable,
        "quarantined": quarantined,
        "allocated": part["live"],
        "live": part["live"],
        "reclaimable": part["reclaimable"],
        "resetting": part["resetting"],
        "missing": part["missing"],
    }

    if total <= 0:
        # No pool configured (a deployment with visitors disabled). Not a
        # failure — but do not claim health that was never measured.
        entry.update(
            {
                "is_healthy": True,
                "status": "ok",
                "health_class": "unknown",
                "level": "warning",
                "message": "No visitor pool configured",
            }
        )
        return entry

    census = describe_partition(part)

    if part["inconsistent"]:
        # The buckets do not sum to the pool size, so the producer and this
        # reader disagree about what a slot is. Say so rather than classify
        # confidently on numbers one of us has misunderstood.
        entry.update(
            {
                "is_healthy": False,
                "status": "warning",
                "health_class": "warning",
                "level": "warning",
                "cause": "inconsistent",
                "repair": "report this payload — the pool counters disagree",
                "message": (
                    f"Visitor-pool counts are inconsistent: {census} plus "
                    f"{allocatable} allocatable does not sum to {total}. "
                    f"Capacity cannot be trusted until this is explained."
                ),
            }
        )
        return entry

    if allocatable == 0:
        cause = capacity_cause(part)
        entry.update(
            {
                "is_healthy": False,
                "status": "error",
                "health_class": "unhealthy",
                "level": "error",
                "cause": cause,
                "repair": hint_by_cause[cause],
                "message": (
                    f"0 of {total} visitor slots allocatable — every anonymous "
                    f"visitor is downgraded to the shared readonly-visitor "
                    f"account (reason=no_ready_slot). Cause={cause}: {census}. "
                    f"Fix: {hint_by_cause[cause]}"
                ),
            }
        )
        return entry

    if quarantined > 0:
        entry.update(
            {
                "is_healthy": False,
                "status": "warning",
                "health_class": "warning",
                "level": "warning",
                "cause": CAUSE_QUARANTINED,
                "repair": VISITOR_POOL_REPAIR_HINT,
                "message": (
                    f"{allocatable} of {total} visitor slots allocatable, "
                    f"{quarantined} quarantined — pool degraded; capacity will "
                    f"exhaust. Fix: {VISITOR_POOL_REPAIR_HINT}"
                ),
            }
        )
        return entry

    if allocatable < warn_below:
        cause = capacity_cause(part)
        entry.update(
            {
                "is_healthy": False,
                "status": "warning",
                "health_class": "warning",
                "level": "warning",
                "cause": cause,
                "repair": hint_by_cause[cause],
                "message": (
                    f"Only {allocatable} of {total} visitor slots allocatable "
                    f"— the next arrival takes the last one, and a consumed "
                    f"slot does not return for tens of minutes. {census}. "
                    f"Fix: {hint_by_cause[cause]}"
                ),
            }
        )
        return entry

    entry.update(
        {
            "is_healthy": True,
            "status": "ok",
            "health_class": "healthy",
            "level": "info",
            "message": f"{allocatable} of {total} visitor slots allocatable",
        }
    )
    return entry


def check_visitor_pool(status_data: dict, pool_status_fn=None) -> None:
    """Populate ``status_data['visitor_pool']`` from the live pool status.

    READ-ONLY. It calls only ``VisitorPool.get_pool_status()``, which is pure
    ORM counting. It must NEVER call ``reconcile_visitor_slots``: that command's
    Phase 1 quarantines every slot, so "checking" the pool with it would take
    the pool down. A health check that mutates what it measures is not a health
    check — the operator hit exactly that on 2026-08-16 by running the
    reconcile as a probe.

    ``pool_status_fn`` is a kwarg-only test seam (never a request parameter),
    mirroring the ``enqueue_fn=`` / ``clone_fn=`` seams already used elsewhere
    in this repo: tests inject a tiny real function returning a measured status
    dict instead of provisioning sixteen real workspaces.
    """
    try:
        if pool_status_fn is None:
            # Imported lazily and on purpose: a health endpoint must not 500
            # because the visitor-pool package failed to import.
            from apps.infra.project_app.services.visitor_pool import VisitorPool

            pool_status_fn = VisitorPool.get_pool_status
        pool_status = pool_status_fn()
    except Exception as exc:
        logger.warning(f"Could not check visitor pool: {exc}")
        status_data["visitor_pool"] = {
            "is_healthy": False,
            "status": "error",
            "health_class": "unknown",
            "level": "warning",
            "error": str(exc),
            "message": f"Visitor pool check failed: {exc}",
        }
        return

    status_data["visitor_pool"] = classify_visitor_pool(pool_status)


# EOF
