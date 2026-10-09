#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Load and render the funding manifest from its single source of truth.

Every funding figure the ``/funding/`` page shows comes from
``data/funding.json``, which mirrors the operator's funding.json manifest
(SciTeX Inc. steward). The JSON stores the NUMBER, never a formatted string;
this module owns the formatting, so the plan amount has exactly one
rendering. The same file is served verbatim at
``/.well-known/funding.json``.

No silent fallback: a missing or malformed file RAISES. A funding page that
renders empty because its data vanished looks like "we need nothing".
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from django.utils.translation import gettext as _

__all__ = [
    "FUNDING_PATH",
    "format_funding_amount",
    "funding_plan",
    "load_funding",
]

FUNDING_PATH = Path(__file__).resolve().parent / "data" / "funding.json"


def load_funding() -> dict[str, Any]:
    """Return the parsed funding manifest, or raise if it cannot be trusted."""
    if not FUNDING_PATH.exists():
        raise FileNotFoundError(
            f"funding.json not found at {FUNDING_PATH}. It is the single "
            "source of truth for the /funding/ page and "
            "/.well-known/funding.json — restore it from git rather than "
            "hard-coding funding figures back into a template."
        )
    data = json.loads(FUNDING_PATH.read_text(encoding="utf-8"))
    plans = (data.get("funding") or {}).get("plans")
    if not plans:
        raise ValueError(
            f"funding.json at {FUNDING_PATH} parsed but has no "
            "'funding.plans' entries, so /funding/ would render an empty "
            "plan list. Fix the data file; do not let the page claim there "
            "is nothing to fund."
        )
    return data


def format_funding_amount(amount: int | float) -> str:
    """One funding amount: ``$25,000`` for whole dollars."""
    if isinstance(amount, int):
        return f"${amount:,}"
    text = f"{amount:,.2f}".rstrip("0").rstrip(".")
    return f"${text}"


def funding_plan(guid: str = "oss-sustainability") -> dict[str, Any]:
    """The active funding plan, formatted for the template.

    ``amount_display`` is the ONLY rendering of the amount (the template
    must never carry a literal); ``currency`` and ``frequency`` come
    straight from the manifest.
    """
    data = load_funding()
    plans = (data.get("funding") or {}).get("plans") or []
    plan = next((p for p in plans if p.get("guid") == guid), None)
    if plan is None:
        guids = sorted(p.get("guid", "?") for p in plans)
        raise ValueError(
            f"funding plan {guid!r} not found in funding.json "
            f"(available: {guids}). Fix the data file."
        )
    if plan.get("status") != "active":
        raise ValueError(
            f"funding plan {guid!r} has status {plan.get('status')!r}, "
            "expected 'active'. Fix the data file."
        )
    amount = plan["amount"]
    currency = plan.get("currency", "USD")
    frequency = plan.get("frequency", "yearly")
    per = {"yearly": _("per year"), "monthly": _("per month"), "once": _("one-time")}
    if frequency not in per:
        raise ValueError(
            f"funding plan {guid!r} has frequency {frequency!r}; "
            f"expected one of {sorted(per)}. Extend this deliberately."
        )
    return {
        "guid": plan.get("guid", ""),
        "name": plan.get("name", ""),
        "description": plan.get("description", ""),
        "amount": amount,
        "amount_display": format_funding_amount(amount),
        "currency": currency,
        "frequency": frequency,
        "frequency_display": per[frequency],
        "channels": list(plan.get("channels") or []),
        "entity_name": (data.get("entity") or {}).get("name", ""),
        "entity_email": (data.get("entity") or {}).get("email", ""),
    }
