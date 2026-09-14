#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""JSON twin of the /server-status/ page.

WHY THIS EXISTS: status.scitex.ai is a Cloudflare Worker at the edge, so it
survives the outage it reports on — but from outside it can only ever see "does
the URL answer". Everything the operator actually reads on /server-status/
(containers, disk, queues, visitor slots) lives inside the hub. This endpoint is
the one door through which the edge can see it.

WHY IT REUSES THE PAGE'S COLLECTOR RATHER THAN RE-CHECKING: ``_collect_status_data``
already runs every check in parallel under ONE hard deadline and represents a
check that misses it three-valued as UNKNOWN. Re-implementing that here would
create a second source of truth that drifts from the page silently — the page
and this endpoint would disagree about the same server and both look right.
One collector, two renderers: HTML for humans, JSON for the edge.

EXPOSURE IS UNCHANGED BY CONSTRUCTION, not by assertion. The payload is the same
``status_data`` dict the template already renders, produced by the same
``_CHECK_PLACEMENTS`` registry. Checks outside that registry — ``check_citation_graph``,
``check_user_data_permissions`` — are not called by the page and are not called
here either. Since the 2026-09-14 site audit the full payload is served only to
instance admins (as the full /server-status/ page is); everyone else gets the
same shape reduced to per-service state by ``redact_for_public``.

PARTIAL RESULTS ARE THE POINT. A status API that answers only when every check
succeeds is useless in exactly the incident it exists for. ``complete`` says
whether every check answered, and the checks that did not are named in
``status_data.unknown_checks`` — so the edge can render "unknown" as its own
state instead of guessing up or down.
"""

from __future__ import annotations

import logging

from django.core.serializers.json import DjangoJSONEncoder
from django.http import JsonResponse
from django.utils import timezone

from ..access import is_instance_admin
from ..server import CHECK_DEADLINE_SECONDS, _CHECK_PLACEMENTS, _collect_status_data

logger = logging.getLogger("scitex")

# Bumped only on a BREAKING change to the payload shape. The edge renderer keys
# off this, so an additive field must NOT bump it — that would make every
# deployed consumer refuse a payload it could have read.
SCHEMA = "scitex-hub.status/1"

# NON-ADMIN REDACTION (site audit 2026-09-14). The full payload carries host CPU /
# memory / disk / network counters, container images, internal URLs, ports, SSH
# banners, package versions, visitor usernames and raw error strings that can
# name hosts and paths. A non-admin (including the anonymous status.scitex.ai
# Worker) keeps the SAME declared shape but only per-service STATE: name, status,
# health_class. Sections that are host detail in their entirety are dropped.
_PUBLIC_LIST_SECTIONS = ("services", "ssh_services", "api_services")
_PUBLIC_DICT_SECTIONS = ("database", "redis", "slurm", "apptainer")
_PUBLIC_ENTRY_FIELDS = ("name", "status", "health_class")


def redact_for_public(status_data: dict) -> dict:
    """Reduce ``status_data`` to per-service state for a non-admin viewer."""
    redacted: dict = {
        "unknown_checks": [
            {"name": u.get("name"), "check": u.get("check")}
            for u in status_data.get("unknown_checks", [])
        ],
    }
    for key in _PUBLIC_LIST_SECTIONS:
        redacted[key] = [
            {f: entry.get(f) for f in _PUBLIC_ENTRY_FIELDS if f in entry}
            for entry in status_data.get(key, [])
        ]
    for key in _PUBLIC_DICT_SECTIONS:
        section = status_data.get(key) or {}
        redacted[key] = {
            f: section.get(f) for f in _PUBLIC_ENTRY_FIELDS[1:] if f in section
        }
    return redacted


def status_api(request, checks=None, deadline_seconds=None):
    """Return the /server-status/ payload as JSON.

    ``checks`` / ``deadline_seconds`` are injectable for tests, matching
    ``server_status()``; URL routing calls this with the defaults so the page
    and the API are the same measurement of the same machine.
    """
    if checks is None:
        checks = {
            name: getattr(_server_module(), name) for name in _CHECK_PLACEMENTS
        }
    if deadline_seconds is None:
        deadline_seconds = CHECK_DEADLINE_SECONDS

    status_data = _collect_status_data(request, checks, deadline_seconds)
    if not is_instance_admin(getattr(request, "user", None)):
        status_data = redact_for_public(status_data)

    payload = {
        "schema": SCHEMA,
        "generated_at": timezone.now().isoformat(),
        "deadline_seconds": deadline_seconds,
        # False when any check missed the deadline. The names are in
        # status_data["unknown_checks"] — not duplicated here, so the two can
        # never disagree.
        "complete": not status_data.get("unknown_checks"),
        "status_data": status_data,
    }

    try:
        return JsonResponse(
            payload,
            encoder=DjangoJSONEncoder,
            json_dumps_params={"ensure_ascii": False},
            headers={
                # A status reading served from a cache is a claim about the past
                # presented as the present. The edge caches its own rendered page
                # for 60 s, which is where the load is bounded.
                "Cache-Control": "no-store",
            },
        )
    except TypeError as exc:
        # Fail LOUD and actionable: a check grew a value JSON cannot carry.
        # Silently dropping it would make the edge page quietly incomplete.
        logger.error("status_api: payload is not JSON-serializable: %s", exc)
        return JsonResponse(
            {
                "schema": SCHEMA,
                "error": "status payload is not JSON-serializable",
                "detail": str(exc),
                "hint": (
                    "A status check returned a value JsonResponse cannot encode "
                    "(datetime and Decimal are handled by DjangoJSONEncoder; "
                    "model instances, sets and timedeltas are not). Find the "
                    "check in apps/infra/public_app/views/status/ and convert "
                    "the value at the point it is built."
                ),
            },
            status=500,
        )


def _server_module():
    """Resolve check callables at call time, exactly as ``server_status`` does.

    Imported lazily through the module object rather than by name so a test that
    monkeypatches a check on ``server`` is honoured here too — the page and the
    API must never resolve a different function for the same check name.
    """
    from .. import server

    return server


# EOF
