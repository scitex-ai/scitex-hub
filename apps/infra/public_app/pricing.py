#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Load and render the published price list from its single source of truth.

Every price SciTeX shows a visitor comes from ``data/pricing.json``, which
mirrors the operator's "SciTeX Services SSOT — Provisional v1.0" (2026-09-14).
Prices are USD and USD is the only stored currency; the yen on /tokushoho/ is a
reference computed at render time from the live exchange rate.

The JSON stores numeric ``amount`` values or an explicit on-request price
with no amount, never a formatted price. This module owns the formatting so
a catalogue change reaches every page together.

English is the i18n SOURCE for every phrase built here; Japanese comes from the
catalog (locale/ja/LC_MESSAGES/django.po), applied at CALL time so it follows
the active language.

No silent fallback: a missing or malformed file RAISES. A pricing page that
renders empty because its data vanished is worse than one that fails loudly —
it looks like "we charge nothing".
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

from django.utils.translation import gettext as _

from .pricing_attributes import (  # noqa: F401 - re-exported
    _ATTRIBUTE_TEXT,
    _LICENSE_TERM_DISPLAY,
    _LICENSE_TERM_LABELS,
    _credit_text,
    _egress_text,
    _eligibility_text,
    _idle_reclaim_text,
    _license_terms_text,
    _limit_set_by_text,
    _no_card_required_text,
    _overage_text,
    _self_hosted_text,
    _storage_text,
    _trial_text,
    _workspace_limits_text,
    displayed_attributes,
    included_items,
    remarks_items,
    validate_spend_cap,
)
from .pricing_comparison import (  # noqa: F401 - re-exported
    _merge_repeated_cells,
    cloud_plan_comparison,
    plan_comparison,
    table_notes,
)
from .pricing_format import (  # noqa: F401 - re-exported
    _UNIT_SUFFIX,
    coming_soon,
    format_amount,
    format_usd,
)
from .pricing_fx import (  # noqa: F401 - re-exported
    annotate_jpy_reference,
    get_usd_jpy_rate,
    usd_to_jpy,
)
from .pricing_metered import (  # noqa: F401 - re-exported
    _API_KEY_DISPLAY,
    _API_PRIORITY_DISPLAY,
    _metered_and_api_rows,
    _priority_cells,
)

__all__ = [
    "PRICING_PATH",
    "coming_soon",
    "displayed_attributes",
    "format_amount",
    "format_usd",
    "included_items",
    "load_pricing",
    "published_price_groups",
    "published_price_rows",
    "tier_rows",
    "validate_spend_cap",
]

PRICING_PATH = Path(__file__).resolve().parent / "data" / "pricing.json"


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


def _published_price(item: dict[str, Any]) -> str:
    """Format a numeric price or an explicitly quoted offer; reject ambiguity."""
    status = item.get("price_status", "fixed")
    amount = item["amount"]
    unit = item.get("unit", "once")
    from_price = item.get("from_price", False)
    if status == "on-request":
        if amount is not None or from_price or unit not in _UNIT_SUFFIX:
            raise ValueError(
                "An on-request price needs a null amount, a known unit and no floor."
            )
        return _("On request")
    if status != "fixed":
        raise ValueError(f"Unknown price_status {status!r} in pricing.json.")
    return format_amount(amount, unit, from_price)


def published_price_rows(today: date | None = None) -> list[dict[str, Any]]:
    """The price list the 特定商取引法 page publishes, formatted, gated by date.

    ``available_from`` (YYYY-MM) is a GATE, not a label: published iff set and
    <= this month. ``withheld`` (a stated reason) hides a row whatever its date
    says; whitespace is not a hold.
    """
    today = today or date.today()
    this_month = f"{today.year:04d}-{today.month:02d}"
    data = load_pricing()
    rows = []
    for item in data.get("published_prices", []):
        available_from = item.get("available_from")
        if not available_from or available_from > this_month:
            continue
        if str(item.get("withheld", "")).strip():
            continue
        from_price = item.get("from_price", False)
        basis = item.get("basis", "")
        attrs = item.get("attributes", {})
        # One attribute, one string, from ONE function: each dedicated column
        # takes its text from the same registry included_items() uses, and the
        # 備考 cell excludes those attributes so nothing is stated twice.
        storage_str = (
            _storage_text(attrs["included_storage"], basis)
            if "included_storage" in attrs
            else ""
        )
        credit_str = (
            _credit_text(attrs["included_compute_credit"], basis)
            if "included_compute_credit" in attrs
            else ""
        )
        overage_str = _overage_text(attrs["overage"]) if "overage" in attrs else ""
        rows.append(
            {
                "id": item["id"],
                "label": item["label"],
                "price": _published_price(item),
                "price_note": "",
                "storage": storage_str,
                "compute_credit": credit_str,
                "overage": overage_str,
                "included": included_items(attrs, basis),
                "remarks": remarks_items(
                    attrs, basis, storage_str, credit_str, overage_str
                ),
                "usd_amount": item["amount"],
                # A floor price ("from $X"); the yen reference prefixes 〜.
                "is_from_price": bool(from_price),
                "category": item.get("category", "service"),
                "description": item.get("description", ""),
                "basis": basis,
                "attributes": attrs,
                "price_is_floor": bool(item.get("price_is_floor", False)),
            }
        )
    return rows


_CATEGORY_LABELS = {
    "subscription": "サブスク",
    "license": "ライセンス",
    "service": "サービス",
}


def published_price_groups(today: date | None = None) -> list[dict[str, Any]]:
    """published_price_rows() grouped by category, in catalogue order."""
    groups: list[dict[str, Any]] = []
    for row in published_price_rows(today=today):
        cat = row["category"]
        if cat not in _CATEGORY_LABELS:
            raise ValueError(
                f"published_prices row {row['id']!r} has category {cat!r}; "
                f"expected one of {sorted(_CATEGORY_LABELS)}. Add the category here "
                "deliberately rather than letting it render unlabelled."
            )
        group = next((g for g in groups if g["category"] == cat), None)
        if group is None:
            group = {"category": cat, "label": _CATEGORY_LABELS[cat], "rows": []}
            groups.append(group)
        group["rows"].append(row)
    return groups


def tier_rows(today: date | None = None) -> list[dict[str, Any]]:
    """The plan groups with their cited prices resolved and date-gated.

    A tier cites published_prices ids rather than carrying amounts, so the
    tier copy can never disagree with the price list. A dangling id raises: a
    tier card that silently shows no price reads as free.
    """
    rows_by_id = {r["id"]: r for r in published_price_rows(today=today)}
    data = load_pricing()
    catalogue_ids = {r["id"] for r in data.get("published_prices", [])}
    tiers = []
    for tier in data.get("tiers", []):
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
