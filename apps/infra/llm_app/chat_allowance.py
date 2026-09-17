#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Chat allowance: the browser-visible half of the daily free-message guarantee.

Card: hub-chat-free-daily-message-allowance-20260917 (operator 7971-7972).
SSOT: docs/product/PRIVATE_BETA_LOGIN_TO_WOW.md §6 — 10 SciTeX-funded messages
per day for every email-verified real user, with the selected model, the
remaining count and the reset time shown BEFORE sending.

Boundary: the accounting (atomic per-user quota, spend caps, kill switch,
idempotency) is backend and lives with the Hub service owner. This module only
normalises whatever that layer reports and decides which of three honestly
different states the surface is in. It never invents a number, because a
made-up "10 of 10 left" is worse than saying nothing: the user plans around it.

Consumed payload (from the backend, once it exists):

    {"state": "available", "model": "deepseek-chat", "remaining": 7,
     "total": 10, "reset_at": "2026-09-18T00:00:00Z",
     "reset_label": "2026-09-18 00:00 UTC"}
"""

from __future__ import annotations

from typing import Any, Mapping, Optional

AVAILABLE = "available"
EXHAUSTED = "exhausted"
UNKNOWN = "unknown"

#: Where a user without their own provider key goes, and where a paid allowance
#: is offered. Both are existing routes, verified against the running Hub.
BYOK_URL = "/ai-setup/"
PAID_URL = "/pricing/"


def allowance_context(payload: Optional[Mapping[str, Any]]) -> dict:
    """Normalise a backend allowance payload into template context.

    ``None`` (no backend yet, request failed, not signed in) yields the explicit
    ``unknown`` state with no counts attached.
    """
    if not payload:
        return {"state": UNKNOWN, "model": "", "remaining": None,
                "total": None, "reset_at": "", "reset_label": ""}

    remaining = payload.get("remaining")
    state = payload.get("state")
    if state not in (AVAILABLE, EXHAUSTED):
        # Derive it rather than trust a missing/odd state: a reported zero is
        # exhausted, anything else with a count is available, and no count is
        # unknown. This keeps the surface truthful even if the backend adds a
        # state name this client does not know yet.
        if remaining is None:
            state = UNKNOWN
        else:
            state = EXHAUSTED if int(remaining) <= 0 else AVAILABLE

    return {
        "state": state,
        "model": payload.get("model") or "",
        "remaining": None if remaining is None else int(remaining),
        "total": payload.get("total"),
        "reset_at": payload.get("reset_at") or "",
        "reset_label": payload.get("reset_label") or "",
    }


# EOF
