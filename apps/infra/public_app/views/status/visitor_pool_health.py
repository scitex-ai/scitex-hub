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

Kept in its own module rather than appended to ``health_checks.py`` because
that file is already at its line ceiling, and because the visitor pool is a
product surface rather than an infrastructure daemon.
"""

from __future__ import annotations

import logging

logger = logging.getLogger("scitex")

# The repair, named inside the issue text itself. An issues[] entry that states
# the symptom without naming the fix hands the next operator exactly the
# archaeology this incident already cost (constitution §2). ``--repair-only`` is
# deliberate and load-bearing: the PLAIN reconcile quarantines every slot
# including healthy ones, so recommending it against a live, partially degraded
# pool would make things strictly worse.
VISITOR_POOL_REPAIR_HINT = (
    "docker exec scitex-hub-prod-django-1 "
    "python manage.py reconcile_visitor_slots --repair-only"
)


def classify_visitor_pool(pool_status: dict) -> dict:
    """Map a pool-status dict to a health entry. Pure function, no I/O.

    ``ready`` — never ``free`` — is the number that answers "can a visitor get
    a real slot?": allocation requires ``quarantined=False`` AND
    ``is_active=False`` AND ``workspace_ready=True``. ``free`` is merely
    total-minus-occupied and counts slots that can never be handed out; a UI
    that showed ``free`` claimed spare capacity while every visitor was
    correctly downgraded to read-only (prod 2026-07-30). During the 2026-08-16
    outage ``free`` was 16 — the number that looks perfect.

    Severity:

    ``ready == 0`` -> ``unhealthy``, i.e. overall ``"error"`` and the RED dot.
        Deliberately not ``"warning"``. The anonymous-visitor product path is
        entirely down, and ``issues[]`` renders only in the notification bell,
        which is wrapped in ``{% if DEBUG or user.is_staff %}``. Only the
        status colour reaches a non-staff visitor, and only ``"error"`` moves
        it off green. Filing a total outage as a warning would reproduce the
        incident for everyone who is not staff.

    ``ready > 0`` with ``quarantined > 0`` -> ``warning`` (degraded capacity).
        Keyed on ``quarantined``, NOT on ``ready < total``: a slot in USE is
        legitimately not ready, so ``ready < total`` would raise an alarm every
        time a visitor showed up.

    otherwise -> ``healthy``.
    """
    total = pool_status.get("total") or 0
    ready = pool_status.get("ready") or 0
    quarantined = pool_status.get("quarantined") or 0
    allocated = pool_status.get("allocated") or 0

    entry = {
        "total": total,
        "ready": ready,
        "quarantined": quarantined,
        "allocated": allocated,
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

    if ready == 0:
        entry.update(
            {
                "is_healthy": False,
                "status": "error",
                "health_class": "unhealthy",
                "level": "error",
                "message": (
                    f"0 of {total} visitor slots ready ({quarantined} "
                    f"quarantined) — every anonymous visitor is downgraded to "
                    f"the shared readonly-visitor account "
                    f"(reason=no_ready_slot). Fix: {VISITOR_POOL_REPAIR_HINT}"
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
                "message": (
                    f"{ready} of {total} visitor slots ready, {quarantined} "
                    f"quarantined — pool degraded; capacity will exhaust. "
                    f"Fix: {VISITOR_POOL_REPAIR_HINT}"
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
            "message": f"{ready} of {total} visitor slots ready",
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
