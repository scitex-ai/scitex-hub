#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Load and render the published price list from its single source of truth.

Every price SciTeX shows a visitor comes from ``data/pricing.json``, which
mirrors the operator's "SciTeX Services SSOT — Provisional v1.0" (2026-09-14).
Prices are USD and USD is the only stored currency; the yen on /tokushoho/ is a
reference computed at render time from the live exchange rate.

The JSON stores an ``amount`` and never a formatted string. This module owns
the formatting, so "2400" has exactly one rendering and changing a price is a
one-place edit that reaches every page together.

English is the i18n SOURCE for every phrase built here; Japanese comes from the
catalog (locale/ja/LC_MESSAGES/django.po), applied at CALL time so it follows
the active language.

No silent fallback: a missing or malformed file RAISES. A pricing page that
renders empty because its data vanished is worse than one that fails loudly —
it looks like "we charge nothing".
"""

from __future__ import annotations

import functools
import json
from datetime import date
from pathlib import Path
from typing import Any

from django.utils.translation import gettext as _

__all__ = [
    "PRICING_PATH",
    "coming_soon",
    "format_amount",
    "format_usd",
    "included_items",
    "load_pricing",
    "published_price_groups",
    "published_price_rows",
    "tier_rows",
]

PRICING_PATH = Path(__file__).resolve().parent / "data" / "pricing.json"

# The suffix a unit adds after the amount. Deliberately NOT translated: the
# public price reads "$19/mo" in both languages (landing tests pin that).
# An unknown unit raises rather than rendering a bare number that could be read
# as monthly, one-off or hourly by whoever is looking.
_UNIT_SUFFIX = {
    "once": "",
    "per_case": "",
    "month": "/mo",
    "year": "/year",
    "per_hour": "/hr",
    "per_project": "/project",
}


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


def format_usd(amount: int | float) -> str:
    """One USD amount: ``$2,400`` for whole dollars, ``$0.10`` / ``$0.005`` for
    rates (at least two decimals, more only when the SSOT needs them)."""
    if isinstance(amount, int):
        return f"${amount:,}"
    text = f"{amount:,.3f}".rstrip("0")
    whole, _sep, frac = text.partition(".")
    return f"${whole}.{frac.ljust(2, '0')}"


def format_amount(amount: int | float, unit: str = "once", from_price: bool = False) -> str:
    """Render one plan/service price the single agreed way.

    ``0`` is "Free" regardless of unit. ``from_price`` renders the floor form
    ("from $2,000"; JA 「$2,000〜」).
    """
    if unit not in _UNIT_SUFFIX:
        raise ValueError(
            f"unknown price unit {unit!r} in pricing.json; expected one of "
            f"{sorted(_UNIT_SUFFIX)}. Add the unit here deliberately rather "
            "than letting it render as a bare number."
        )
    if amount == 0:
        return _("Free")
    base = format_usd(amount) + _UNIT_SUFFIX[unit]
    return _("from %(price)s") % {"price": base} if from_price else base


def coming_soon(text: str) -> str:
    """Label a feature that is not live yet (EN "(Coming soon)", JA 「（近日提供）」)."""
    return _("%(text)s (Coming soon)") % {"text": text}


# How one attribute of a published row reads to a visitor. Every value form is
# enumerated, so a value this table has not seen fails the test that renders
# the whole catalogue instead of reaching a legal page untranslated.


def _storage_text(value: dict[str, Any], basis: str = "") -> str:
    return _("%(amount)s GB %(tier)s storage included") % {
        "amount": f"{value['amount']:,}",
        "tier": value.get("tier", "Cool"),
    }


def _credit_text(value: dict[str, Any], basis: str = "") -> str:
    text = _("%(amt)s compute credit per billing cycle") % {
        "amt": format_usd(value["amount"])
    }
    return coming_soon(text) if value.get("coming_soon") else text


def _trial_text(value: dict[str, Any]) -> str:
    # The trial compute credit is a compute credit, which is not live yet.
    return _(
        "%(days)s-day free trial with %(storage)s GB Cool storage "
        "and a %(credit)s trial compute credit (credit: Coming soon)"
    ) % {
        "days": value["days"],
        "storage": value["storage_gb"],
        "credit": format_usd(value["compute_credit"]),
    }


def _egress_text(value: dict[str, Any]) -> str:
    return _(
        "%(amount)s GB internet egress per billing cycle; ingress and "
        "internal SciTeX traffic are free"
    ) % {"amount": value["amount"]}


def _overage_text(key: str) -> str:
    if key == "metered":
        return _("Storage and egress above the included amounts are metered")
    raise ValueError(f"unknown overage value {key!r}")


def _limit_set_by_text(key: str) -> str:
    if key == "user":
        return coming_soon(_("Monthly spending cap set by the user"))
    raise ValueError(f"unknown monthly_limit_set_by value {key!r}")


def _eligibility_text(value: str) -> str:
    return _("Eligibility: %(v)s") % {"v": _(value)}


def _no_card_required_text(value: bool) -> str:
    if value is not True:
        raise ValueError(f"unknown no_card_required value {value!r}")
    return _("No credit card required")


def _workspace_limits_text(value: dict[str, Any]) -> str:
    gpu = _(", with GPU") if value.get("gpu") else _("")
    return _("%(cpu)s CPU, %(mem)s GB memory workspace%(gpu)s") % {
        "cpu": value["cpu"],
        "mem": value["memory_gb"],
        "gpu": gpu,
    }


def _idle_reclaim_text(value: dict[str, Any]) -> str:
    return _(
        "Idle workspaces pause after %(pause)s days and are removed after %(delete)s"
    ) % {
        "pause": value["pause_after_days"],
        "delete": value["delete_after_days"],
    }


_ATTRIBUTE_TEXT = {
    "no_card_required": _no_card_required_text,
    "workspace_limits": _workspace_limits_text,
    "idle_reclaim": _idle_reclaim_text,
    "free_trial": _trial_text,
    "included_storage": _storage_text,
    "included_compute_credit": _credit_text,
    "included_egress": _egress_text,
    "overage": _overage_text,
    "monthly_limit_set_by": _limit_set_by_text,
    "eligibility": _eligibility_text,
}


def included_items(attributes: dict[str, Any], basis: str = "") -> list[str]:
    """What a row includes, one short phrase per attribute, in catalogue order.

    Raises on an attribute name this module does not know: the catalogue is
    committed with the code that renders it, so an unknown field is a red CI
    rather than a silently shorter legal page.
    """
    text = dict(_ATTRIBUTE_TEXT)
    if basis:
        text["included_storage"] = functools.partial(_storage_text, basis=basis)
        text["included_compute_credit"] = functools.partial(_credit_text, basis=basis)
    items = []
    for key, value in attributes.items():
        if key not in text:
            raise ValueError(
                f"unknown attribute {key!r} in pricing.json; add its wording to "
                "_ATTRIBUTE_TEXT deliberately rather than dropping it from the page."
            )
        items.append(text[key](value))
    return items


def remarks_items(
    attrs: dict[str, Any],
    basis: str = "",
    storage_text: str = "",
    credit_text: str = "",
    overage_text: str = "",
) -> list[str]:
    """備考 cell: the included list MINUS attributes that have their own column.

    A row whose attributes are ALL dedicated (storage / compute credit /
    overage) has an EMPTY 備考 by design; a template fallback to the full
    included list would repeat every dedicated column there.
    """
    column_texts = {
        "included_storage": storage_text,
        "included_compute_credit": credit_text,
        "overage": overage_text,
    }
    drop = {key for key, rendered in column_texts.items() if rendered and key in attrs}
    return included_items({k: v for k, v in attrs.items() if k not in drop}, basis)


def get_usd_jpy_rate() -> dict:
    """The live USD→JPY rate, fetched from a public FX API, cached for 60 min.

    The tokushoho page shows the yen figure as a DERIVED REFERENCE (operator
    2026-09-12: USD is the SSoT; the referential yen is calculated from the
    latest rate and the method is explained on the page). If the API is
    unreachable the rate is ``None`` and the reference column shows "—":
    there is no stored yen amount to fall back to.
    """
    import time

    import requests

    global _FX_RATE_CACHE
    now = time.time()
    cached = _FX_RATE_CACHE
    if cached and (now - cached[0]) < 3600:
        return cached[1]
    try:
        resp = requests.get("https://open.er-api.com/v6/latest/USD", timeout=5)
        resp.raise_for_status()
        data = resp.json()
        result = {
            "rate": float(data["rates"]["JPY"]),
            "as_of": data.get("time_last_update_utc", ""),
            "source": "open.er-api.com",
        }
    except Exception:  # noqa: BLE001 — any failure degrades to "—"
        result = {"rate": None, "as_of": "", "source": ""}
    _FX_RATE_CACHE = (now, result)
    return result


_FX_RATE_CACHE: tuple | None = None


def usd_to_jpy(usd_amount: int, rate: float) -> int:
    """Convert a USD amount to yen at the given rate, rounded to the nearest
    10 yen (a clean reference figure)."""
    return int(round(usd_amount * rate / 10.0)) * 10


def annotate_jpy_reference(rows: list[dict], rate: float | None) -> list[dict]:
    """Attach a computed ``price_jpy`` to each row, from the live rate.

    Free rows and an unavailable rate both show "—". Mutates and returns rows.
    """
    for row in rows:
        usd = row.get("usd_amount")
        prefix = "〜" if row.get("is_from_price") else ""
        if rate and usd:
            row["price_jpy"] = f"{prefix}{usd_to_jpy(usd, rate):,}円"
        else:
            row["price_jpy"] = "—"
    return rows


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
        unit = item.get("unit", "once")
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
                "price": format_amount(item["amount"], unit, from_price),
                "price_note": "",
                "storage": storage_str,
                "compute_credit": credit_str,
                "overage": overage_str,
                "included": included_items(attrs, basis),
                "remarks": remarks_items(attrs, basis, storage_str, credit_str, overage_str),
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


_CATEGORY_LABELS = {"subscription": "サブスク", "license": "ライセンス", "service": "サービス"}


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
