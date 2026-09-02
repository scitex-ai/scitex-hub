#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Load and render the published price list from its single source of truth.

Every price SciTeX shows a visitor comes from ``data/pricing.json``. Before
this module, ``/services/`` hard-coded nine JPY rows in its template and
``/landing/`` hard-coded twelve USD items in its view; the two disagreed by up
to 2.7x on the same service, and neither matched the other's currency.

The JSON stores an ``amount`` and never a formatted string. This module owns
the formatting, so "11000" has exactly one rendering and changing a price is a
one-place edit that reaches every page and the brochure PDF together.

No silent fallback: a missing or malformed file RAISES. A pricing page that
renders empty because its data vanished is worse than one that fails loudly —
it looks like "we charge nothing".
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

__all__ = [
    "PRICING_PATH",
    "format_amount",
    "load_pricing",
    "plan_rows",
    "pricing_rows",
    "published_price_rows",
]

PRICING_PATH = Path(__file__).resolve().parent / "data" / "pricing.json"

# How a unit renders in front of the amount. ``once`` is the consulting bands'
# bare figure; ``per_case`` / ``per_hour`` were added 2026-09-03 for the
# published price list (オンプレ導入 1件, コンサル 1時間). An unknown unit raises in
# format_amount rather than rendering a bare number that could be read as
# monthly, one-off or hourly by whoever is looking.
_UNIT_PREFIX = {"month": "月額 ", "once": "", "per_case": "1件 ", "per_hour": "1時間 "}


def load_pricing() -> dict[str, Any]:
    """Return the parsed price list, or raise if it cannot be trusted."""
    if not PRICING_PATH.exists():
        raise FileNotFoundError(
            f"pricing.json not found at {PRICING_PATH}. It is the single "
            "source of truth for every published price and has no fallback — "
            "restore it from git rather than hard-coding prices back into a "
            "template."
        )
    data = json.loads(PRICING_PATH.read_text(encoding="utf-8"))
    if not data.get("consulting"):
        raise ValueError(
            f"pricing.json at {PRICING_PATH} parsed but has no 'consulting' "
            "entries, so every price table would render empty. Fix the data "
            "file; do not let the page claim there is nothing to buy."
        )
    return data


def format_amount(amount: int, unit: str = "once", from_price: bool = False) -> str:
    """Render one amount the single agreed way.

    ``0`` is free rather than "0円" — and it is free regardless of unit, since
    "月額 無料" reads as a paid plan that happens to cost nothing.
    """
    if amount == 0:
        return "無料"
    if unit not in _UNIT_PREFIX:
        raise ValueError(
            f"unknown price unit {unit!r} in pricing.json; expected one of "
            f"{sorted(_UNIT_PREFIX)}. Add the unit here deliberately rather "
            "than letting it render as a bare number."
        )
    suffix = "円〜" if from_price else "円"
    return f"{_UNIT_PREFIX[unit]}{amount:,}{suffix}"


def _render(row: dict[str, Any]) -> str:
    return format_amount(
        row["amount"], row.get("unit", "once"), row.get("from_price", False)
    )


def pricing_rows() -> list[dict[str, str]]:
    """Return display-ready rows: ``[{"label": ..., "price": ...}, ...]``."""
    data = load_pricing()
    return [
        {"label": row["label"], "price": _render(row)} for row in data["consulting"]
    ]


def published_price_rows(today: date | None = None) -> list[dict[str, Any]]:
    """The price list the 特定商取引法 page publishes, formatted, gated by date.

    Reads ``published_prices`` from pricing.json — the operator's current
    catalogue (upstream: scitex-kk/config/business.yaml), tax-included by
    ruling of 2026-09-03.

    ``available_from`` (YYYY-MM) is a GATE, not a label. A row dated in the
    future is part of the catalogue and NOT on the page: a 特商法 page that
    prices a service which is not yet for sale invites exactly the reviewer
    query the operator hit while filling in the Stripe activation form. The
    gate is date-driven so a service becomes visible on its month without a
    code change — and so the test can prove the gate closes by dating a row
    ahead of ``today``.

    This replaced ``subscription_rows`` on 2026-09-03. That function rendered
    ``plans[].subscription`` — Individual 2,980 / Lab 100,000 — and the Lab tier
    had been RETIRED six days earlier without this file hearing about it. The
    name changed with the data: these are not subscriptions, they are every
    priced offer, and a name that says otherwise invites the next person to
    put the next non-subscription somewhere else.
    """
    today = today or date.today()
    this_month = f"{today.year:04d}-{today.month:02d}"
    rows = []
    for item in load_pricing().get("published_prices", []):
        available_from = item.get("available_from")
        if available_from and available_from > this_month:
            continue
        rows.append(
            {
                "id": item["id"],
                "label": item["label"],
                "price": format_amount(
                    item["amount"], item.get("unit", "once"), item.get("from_price", False)
                ),
            }
        )
    return rows


def plan_rows() -> list[dict[str, Any]]:
    """Return the plan tiers with prices RESOLVED from the bands they cite.

    A plan carries a ``price_ref`` into ``consulting`` rather than its own
    number, so the comparison table and the mobile cards cannot drift apart
    from the price list the way the hand-typed originals did. An unresolvable
    ref raises: a plan card silently rendering a blank price is how a visitor
    concludes the tier is free.
    """
    data = load_pricing()
    bands = {row["id"]: row for row in data["consulting"]}
    resolved = []
    for plan in data.get("plans", []):
        ref = plan["price_ref"]
        if ref not in bands:
            raise ValueError(
                f"plan {plan['id']!r} cites price_ref {ref!r}, which is not an "
                f"id in 'consulting' ({sorted(bands)}). Fix pricing.json — a "
                "dangling reference would render an empty price."
            )
        resolved.append(
            {
                "id": plan["id"],
                "name": plan["name"],
                "audience": plan["audience"],
                "featured": plan.get("featured", False),
                "price": _render(bands[ref]) + plan.get("suffix", ""),
            }
        )
    return resolved
