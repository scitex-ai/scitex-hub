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
    "published_price_groups",
    "published_price_rows",
    "tier_rows",
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
    if not data.get("published_prices"):
        raise ValueError(
            f"pricing.json at {PRICING_PATH} parsed but has no 'published_prices' "
            "entries, so /services/ and /tokushoho/ would both render an empty price "
            "list. Fix the data file; do not let a page claim there is nothing to buy."
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


def published_price_rows(today: date | None = None) -> list[dict[str, Any]]:
    """The price list the 特定商取引法 page publishes, formatted, gated by date.

    Reads ``published_prices`` from pricing.json — the operator's current
    catalogue (upstream: scitex-kk/config/business.yaml), tax-included by
    ruling of 2026-09-03.

    ``withheld`` (a stated reason) hides a row whose amount is settled but
    whose presentation is not — added 2026-09-02 when the two subscription
    rows turned out to be LIST prices under an active 50% launch discount,
    so neither the list price nor a struck-through pair could go on a legal
    page without an operator ruling. The row stays in the catalogue.

    ``available_from`` (YYYY-MM) is a GATE, not a label, and it is the SAME
    rule the upstream business.yaml uses: published iff set and <= this
    month. A row dated in the future is part of the catalogue and NOT on the
    page: a 特商法 page that prices a service which is not yet for sale invites
    exactly the reviewer query the operator hit while filling in the Stripe
    activation form. A row with NO date is not for sale at a list price and
    is excluded. The gate is date-driven so a service becomes visible on its
    month without a code change — and so the test can prove the gate closes
    by dating a row ahead of ``today``.

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
        # business.yaml's rule, verbatim: published iff available_from is SET
        # and <= this month. A row with no date is not for sale at a list
        # price (upstream's usage-billed rows have none), so it is excluded —
        # the same outcome the export will produce, which is the point. The
        # test suite requires the field on every hand-entered row, so an
        # accidental omission fails CI rather than silently hiding a price.
        available_from = item.get("available_from")
        if not available_from or available_from > this_month:
            continue
        # A settled amount whose PRESENTATION is not settled (e.g. a list
        # price that is never the selling price during an active discount).
        # Stated reason, never a bare flag; whitespace is not a hold.
        if str(item.get("withheld", "")).strip():
            continue
        rows.append(
            {
                "id": item["id"],
                "label": item["label"],
                "price": format_amount(
                    item["amount"], item.get("unit", "once"), item.get("from_price", False)
                ),
                # Pass-through of the upstream catalogue's descriptive fields, so
                # /services/ can describe an offer in business.yaml's words.
                "category": item.get("category", "service"),
                "description": item.get("description", ""),
                "attributes": item.get("attributes", {}),
                "price_is_floor": bool(item.get("price_is_floor", False)),
            }
        )
    return rows


def published_price_groups(today: date | None = None) -> list[dict[str, Any]]:
    """published_price_rows() grouped by category, in catalogue order.

    Category labels are the upstream's own words (business.yaml `category`),
    rendered in Japanese exactly as the operator's price table does: the
    subscriptions are the サブスク rows; everything else is a サービス. The
    template gets a list, not a dict, so category order is the JSON order and
    not whatever a dict happens to iterate in.
    """
    labels = {"subscription": "サブスク", "service": "サービス"}
    groups: list[dict[str, Any]] = []
    for row in published_price_rows(today=today):
        cat = row["category"]
        if cat not in labels:
            raise ValueError(
                f"published_prices row {row['id']!r} has category {cat!r}; "
                f"expected one of {sorted(labels)}. Add the category here "
                "deliberately rather than letting it render unlabelled."
            )
        group = next((g for g in groups if g["category"] == cat), None)
        if group is None:
            group = {"category": cat, "label": labels[cat], "rows": []}
            groups.append(group)
        group["rows"].append(row)
    return groups


def tier_rows(today: date | None = None) -> list[dict[str, Any]]:
    """The /services/ tiers with their cited prices resolved and date-gated.

    A tier cites published_prices ids rather than carrying amounts, so the
    tier copy can never disagree with the price list — the drift that put a
    retired Lab tier, priced, on /services/ for five days after business
    retired it. A dangling id raises: a tier card that silently shows no price
    reads as free.
    """
    rows_by_id = {r["id"]: r for r in published_price_rows(today=today)}
    catalogue_ids = {r["id"] for r in load_pricing().get("published_prices", [])}
    tiers = []
    for tier in load_pricing().get("tiers", []):
        resolved = []
        for rid in tier.get("rows", []):
            if rid not in catalogue_ids:
                raise ValueError(
                    f"tier {tier['id']!r} cites published_prices id {rid!r}, which "
                    f"does not exist ({sorted(catalogue_ids)}). Fix pricing.json — a "
                    "dangling reference would render a tier with no price."
                )
            if rid in rows_by_id:  # absent only when the row is date-gated off
                resolved.append(rows_by_id[rid])
        tiers.append(
            {
                "id": tier["id"],
                "name": tier["name"],
                "audience": tier.get("audience", ""),
                "description": tier.get("description", ""),
                "quote_only": bool(tier.get("quote_only", False)),
                "rows": resolved,
            }
        )
    return tiers
