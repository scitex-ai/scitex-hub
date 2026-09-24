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
from django.utils.translation import gettext_lazy as _lazy

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
    "year": "/yr",
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


# Metered compute rates + API services for the comparison table. Rates are
# provider-wide (identical in every tier column); Self-Hosted runs on your
# own hardware so metered cells render a dash there. GPU-hour pricing bundles
# VRAM by model (no standalone VRAM rate exists in the SSOT), and per-service
# API credit costs are not set yet — the services row states the billing
# mechanism (Compute Credits + margin, coming soon) instead of inventing
# numbers. Closed enums throughout: unknown SSOT values raise loudly.
_API_KEY_DISPLAY = {
    "rate-limited": _lazy("Rate-limited"),
    "included": _lazy("Included"),
    "not-applicable": _lazy("—"),
}

_API_SERVICE_LABELS = {
    "scholar": _lazy("Scholar"),
    "stats": _lazy("Stats"),
    "figrecipe": _lazy("FigRecipe"),
    "writer": _lazy("Writer"),
}

_API_SERVICES_ROW_LABEL = _lazy("Scholar, Stats, FigRecipe and Writer")


def _metered_and_api_rows() -> list[dict[str, Any]]:
    card = load_pricing()["rate_card"]
    comp = card["compute"]
    api = card.get("api") or {}
    margin = card["payg_margin_pct"]

    services = api.get("services") or []
    unknown_services = set(services) - set(_API_SERVICE_LABELS)
    if unknown_services:
        raise ValueError(
            f"unknown api.services {sorted(unknown_services)} in pricing.json; "
            "extend _API_SERVICE_LABELS deliberately."
        )
    if set(services) != set(_API_SERVICE_LABELS):
        raise ValueError(
            f"api.services is {services}; the table row label names "
            "Scholar, Stats, FigRecipe and Writer exactly. Update "
            "_API_SERVICES_ROW_LABEL deliberately if the set changes."
        )
    keys = api.get("keys") or {}
    for tier in ("free", "pro", "self_hosted"):
        if keys.get(tier) not in _API_KEY_DISPLAY:
            raise ValueError(
                f"api.keys[{tier!r}] is {keys.get(tier)!r} in pricing.json; "
                "extend _API_KEY_DISPLAY deliberately."
            )

    dash = _("—")
    rate = lambda amount, msgid: msgid % {"price": format_usd(amount)}  # noqa: E731
    cpu_cell = rate(comp["cpu_unit_rate"], _("%(price)s / CPU Unit-hour"))
    mem_cell = rate(comp["memory_addon_rate"], _("%(price)s / GiB-hour"))
    gpu_rows = [
        {
            # One row per GPU class: a single "$X / GPU-hour" cell scans and
            # wraps cleanly on narrow displays, where one combined cell grew
            # into an unreadable word-by-word tower (measured on 390px).
            "label": _(g["name"]),
            "cells": [
                rate(g["amount"], _("%(price)s / GPU-hour")),
                rate(g["amount"], _("%(price)s / GPU-hour")),
                dash,
                dash,
            ],
        }
        for g in comp["gpus"]
    ]
    key_cells = [
        _API_KEY_DISPLAY[keys["free"]],
        _API_KEY_DISPLAY[keys["pro"]],
        _API_KEY_DISPLAY[keys["self_hosted"]],
        _API_KEY_DISPLAY[keys["self_hosted"]],
    ]
    metered_line = coming_soon(
        _("Metered as ordinary compute (CPU / memory / GPU) — "
          "no separate per-app fee")
    )
    agents_pct = api.get("agents_fee_percent", 10)
    agents_line = coming_soon(
        _("Metered compute + model API × %(factor)s")
        % {"factor": f"{100 + agents_pct}%"}
    )
    per_service_api_line = coming_soon(
        _("Rate depends on the service")
    )
    return [
        {"group": coming_soon(_("Metered compute rates"))},
        {
            "label": _("Metered CPU"),
            "cells": [cpu_cell, cpu_cell, dash, dash],
            "nowrap": True,
        },
        {
            "label": _("Metered memory"),
            "cells": [mem_cell, mem_cell, dash, dash],
            "nowrap": True,
        },
        *({**r, "nowrap": True} for r in gpu_rows),
        {"group": _("Applications")},
        {"label": _("API keys"), "cells": key_cells, "nowrap": True},
        {
            "label": _API_SERVICES_ROW_LABEL,
            "cells": [metered_line, metered_line, dash, dash],
        },
        {
            "label": _("Agents"),
            "cells": [agents_line, agents_line, dash, dash],
        },
        {
            "label": _("Model API"),
            "cells": [
                per_service_api_line,
                per_service_api_line,
                dash,
                dash,
            ],
        },
    ]

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


def _self_hosted_text(value: bool) -> str:
    if value is not True:
        raise ValueError(f"unknown self_hosted value {value!r}")
    return _(
        "Runs on your own hardware — CPU, RAM, GPU and storage are yours"
    )


# Self-hosted license contrast (AGPL vs Commercial). The table renders one
# "(AGPL) / (Commercial)" cell per term from BOTH rows' SSOT dicts, so the
# incentives can never drift from the catalogue. Values are closed enums:
# an unknown value is a red ValueError, not a silently wrong cell.
# NOTE: module-level display dicts use gettext_lazy — plain gettext here would
# freeze English at import time and every JA page would show English cells
# (measured live: "Rate-limited" stayed English under ja until this fix).
_LICENSE_TERM_DISPLAY = {
    "commercial_use": {
        "with-disclosure": _lazy("Source disclosure required"),
        "unrestricted": _lazy("No restrictions"),
    },
    "support": {
        "community": _lazy("Community"),
        "included": _lazy("Included"),
    },
    "sla": {
        "none": _lazy("—"),
        "included": _lazy("Included"),
    },
}

_LICENSE_TERM_LABELS = {
    "commercial_use": _lazy("Commercial use"),
    "support": _lazy("Support"),
    "sla": _lazy("SLA"),
}


def _license_terms_text(value: dict[str, Any]) -> str:
    unknown_keys = set(value) - set(_LICENSE_TERM_DISPLAY)
    if unknown_keys:
        raise ValueError(
            f"unknown license_terms keys {sorted(unknown_keys)}; extend "
            "_LICENSE_TERM_DISPLAY deliberately."
        )
    for key, allowed in _LICENSE_TERM_DISPLAY.items():
        if value.get(key) not in allowed:
            raise ValueError(
                f"unknown license_terms[{key!r}] value {value.get(key)!r}; "
                "extend _LICENSE_TERM_DISPLAY deliberately."
            )
    # Card line: a single fixed literal so JA has one msgid to translate
    # (a runtime join would compose an untranslatable string). Only the
    # exact commercial set renders a card line; anything else is table-only
    # (no template renders license included-lists today, so the dash is
    # inert — but the renderer stays total by construction).
    if value == {
        "commercial_use": "unrestricted",
        "support": "included",
        "sla": "included",
    }:
        return _("Commercial use with no restrictions, support and SLA included")
    return _("—")


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
    "self_hosted": _self_hosted_text,
    "license_terms": _license_terms_text,
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


def table_notes() -> list[str]:
    """Footnotes under the comparison table, kept minimal on purpose.

    Everything a visitor needs to decide is in the cells: the academic
    discount sits in the Pro price cell, tier speeds sit under the tier
    names. What remains here are the two facts that fit no cell (what a
    Compute Credit buys, VRAM bundled in GPU-hours) plus the one-line
    honesty note behind the speed figures. Tier wording still comes from
    rate_card.storage_tiers so the table can never drift from the
    catalogue.
    """
    card = load_pricing()["rate_card"]
    for tier in card.get("storage_tiers") or []:
        if not tier.get("name") or not tier.get("meaning"):
            raise ValueError(
                f"storage_tiers entry {tier!r} needs name and meaning; "
                "fix pricing.json."
            )
    return [
        _("Each Compute Credit is worth %(one)s of metered usage: "
          "CPU, memory and GPU hours, plus API calls.")
        % {"one": format_usd(1)},
        _("There is no separate VRAM rate: GPU-hour pricing already "
          "includes memory by model."),
        _("Storage speeds are approximate live measurements; actual "
          "throughput varies with workload, network, concurrent use, "
          "caching, disk fill, drive media, and time of day."),
    ]


def plan_comparison(today=None):
    """Plan comparison table for the landing page, one page, SSOT-rendered.

    Three tiers in one table: SciTeX Cloud Free, SciTeX Cloud Pro, SciTeX
    Self-Hosted. Academic is not a fourth column: it is Pro at 50% off, said
    once in a footnote under the table. Self-Hosted spans both license rows
    (AGPL free, Commercial priced): hosted resources are yours, so every
    resource cell renders the SSOT self-hosted line instead of a dash.

    Rows follow the operator's sketched organization: Price, Resources (CPU
    / RAM / GPU), Compute Credits, and Storage split by tier (Hot /
    Warm / Cool / Cold) so each plan's included storage lands in its tier
    row, plus a Self-hosted license group contrasting AGPL vs Commercial on
    Commercial use, Support and SLA. GPU VRAM is not a separate row: it is
    bundled into each metered GPU class, said once in a footnote.

    Every cell renders from its row's own SSOT attributes through the same
    wording registry the cards and the legal page use, so the table can
    never disagree with them. A missing attribute renders as an em dash: a
    gap in the table is a gap in the SSOT, shown honestly rather than
    papered over.
    """
    rows = {
        r["id"]: r
        for r in published_price_rows(today)
        if r["id"]
        in (
            "subscription-free",
            "subscription-general",
            "subscription-student",
            "selfhosted-agpl",
            "selfhosted-commercial",
        )
    }
    need = (
        "subscription-free",
        "subscription-general",
        "subscription-student",
        "selfhosted-agpl",
        "selfhosted-commercial",
    )
    if any(k not in rows for k in need):
        raise ValueError(
            "plan_comparison needs Free, Pro, Academic, AGPL and Commercial rows published; "
            f"found {sorted(rows)}"
        )
    free = rows["subscription-free"]
    pro = rows["subscription-general"]
    academic = rows["subscription-student"]
    agpl = rows["selfhosted-agpl"]
    commercial = rows["selfhosted-commercial"]

    def limits(row):
        return row["attributes"].get("workspace_limits") or {}

    def cpu_cell(row):
        return str(limits(row)["cpu"]) if "cpu" in limits(row) else _("—")

    def ram_cell(row):
        return (
            _("%(gb)s GB") % {"gb": limits(row)["memory_gb"]}
            if "memory_gb" in limits(row)
            else _("—")
        )

    def gpu_cell(row):
        if "gpu" not in limits(row):
            return _("—")
        return _("GPU included") if limits(row)["gpu"] else _("No GPU")

    def credit_cell(row):
        if "included_compute_credit" not in row["attributes"]:
            return _("—")
        return _credit_text(row["attributes"]["included_compute_credit"])

    def tier_cell(row, tier):
        storage = row["attributes"].get("included_storage") or {}
        if storage.get("tier") != tier:
            return _("—")
        return _("%(gb)s GB included") % {"gb": storage["amount"]}

    def tier_label(tier):
        """Row label: tier name, meaning, and measured speed in the cell.

        Speeds are approximate references from direct-I/O measurements
        (host names deliberately abstracted — backends change as disks are
        added). Reads are true uncached reads, not page-cache numbers.
        """
        approx = {
            "Hot": _("~4 GB/s read / ~4 GB/s write"),
            "Warm": _("~700 MB/s read / ~450 MB/s write"),
            "Cool": _("~550 MB/s read / ~200 MB/s write"),
            "Cold": _("~110 MB/s read / ~90 MB/s write"),
        }
        meaning = next(
            (t.get("meaning", "") for t in load_pricing()["rate_card"].get("storage_tiers", []) if t.get("name") == tier),
            "",
        )
        return _("%(tier)s\n%(meaning)s\n%(speed)s") % {
            "tier": _(tier),
            # Wrapped so the table renders meaning and speed de-emphasized
            # (smaller, lighter) under the tier name.
            "meaning": '<span class="tier-sub">%s</span>' % meaning,
            "speed": '<span class="tier-speed">%s</span>' % approx[tier],
        }

    hosted_line = _("Your own hardware")
    # Table-local short line: the catalogue sentence ("Runs on your own
    # hardware — ...", kept for cards and the legal page) repeated in every
    # resource cell grew rows 3-4x tall and walled the right column.
    agpl_terms = agpl["attributes"].get("license_terms") or {}
    comm_terms = commercial["attributes"].get("license_terms") or {}

    def license_value(terms, term):
        """One side's display value, validated against the closed enum."""
        if term not in _LICENSE_TERM_DISPLAY:
            raise ValueError(
                f"unknown license term {term!r}; extend _LICENSE_TERM_DISPLAY."
            )
        display = _LICENSE_TERM_DISPLAY[term]
        if terms.get(term) not in display:
            raise ValueError(
                f"license_terms[{term!r}] is {terms.get(term)!r}; "
                "fix pricing.json."
            )
        return display[terms[term]]

    license_rows = [
        {
            "label": _LICENSE_TERM_LABELS["commercial_use"],
            "cells": [
                _("—"),
                _("—"),
                license_value(agpl_terms, "commercial_use"),
                license_value(comm_terms, "commercial_use"),
            ],
        },
        {
            "label": _LICENSE_TERM_LABELS["support"],
            "cells": [
                _("—"),
                _("—"),
                license_value(agpl_terms, "support"),
                license_value(comm_terms, "support"),
            ],
        },
        {
            "label": _LICENSE_TERM_LABELS["sla"],
            "cells": [
                _("—"),
                _("—"),
                license_value(agpl_terms, "sla"),
                license_value(comm_terms, "sla"),
            ],
        },
    ]
    price_cells = [
        free["price"],
        # Academic is Pro at half price, said in the cell — not a fourth
        # column, not a footnote.
        _("%(pro)s\n%(acad_price)s academic (50%% off)")
        % {"pro": pro["price"], "acad_price": academic["price"]},
        agpl["price"],
        commercial["price"],
    ]
    coupons = load_pricing().get("coupons") or {}
    coupon_display = {
        "none": _("—"),
        "accepted": _("Coupon codes accepted"),
        "on-request": _("On request"),
    }
    coupon_cells = []
    for key in ("free", "pro", "self_hosted_agpl", "self_hosted_enterprise"):
        value = coupons.get(key, "none")
        if value not in coupon_display:
            raise ValueError(
                f"coupons[{key!r}] is {value!r} in pricing.json; "
                "extend coupon_display deliberately."
            )
        coupon_cells.append(coupon_display[value])
    if coupons.get("coming_soon"):
        coupon_cells[:2] = [
            coming_soon(c) if c != _("—") else c for c in coupon_cells[:2]
        ]
    spec = [
        {"label": _("Price"), "cells": price_cells},
        {"label": _("Coupons"), "cells": coupon_cells},
        {"group": _("Resources")},
        {
            "label": _("CPU"),
            "cells": [cpu_cell(free), cpu_cell(pro), hosted_line, hosted_line],
        },
        {
            "label": _("RAM"),
            "cells": [ram_cell(free), ram_cell(pro), hosted_line, hosted_line],
        },
        {
            "label": _("GPU"),
            "cells": [gpu_cell(free), gpu_cell(pro), hosted_line, hosted_line],
        },
        {
            "label": _("Compute credits"),
            "cells": [credit_cell(free), credit_cell(pro), hosted_line, hosted_line],
        },
        {"group": _("Storage")},
        {
            "label": tier_label("Hot"),
            "cells": [tier_cell(free, "Hot"), tier_cell(pro, "Hot"), hosted_line, hosted_line],
        },
        {
            "label": tier_label("Warm"),
            "cells": [tier_cell(free, "Warm"), tier_cell(pro, "Warm"), hosted_line, hosted_line],
        },
        {
            "label": tier_label("Cool"),
            "cells": [tier_cell(free, "Cool"), tier_cell(pro, "Cool"), hosted_line, hosted_line],
        },
        {
            "label": tier_label("Cold"),
            "cells": [tier_cell(free, "Cold"), tier_cell(pro, "Cold"), hosted_line, hosted_line],
        },
    ] + license_rows + _metered_and_api_rows()
    from django.urls import reverse

    return {
        "columns": [
            {
                "label": _("SciTeX™ Cloud Free"),
                "recommended": False,
                "cta_label": _("Create a free account"),
                "cta_url": reverse("auth_app:signup"),
                "cta_primary": False,
            },
            {
                "label": _("SciTeX™ Cloud Pro"),
                "recommended": True,
                "cta_label": _("Start with Pro"),
                "cta_url": reverse("auth_app:signup"),
                "cta_primary": True,
            },
            {
                "label": _("SciTeX™ Self-Hosted (AGPL)"),
                "recommended": False,
                "cta_label": _("Get the source"),
                "cta_url": load_pricing()["links"]["self_hosted_source"],
                "cta_primary": False,
                "cta_external": True,
            },
            {
                "label": _("SciTeX™ Self-Hosted (Enterprise)"),
                "recommended": False,
                "cta_label": _("Contact us"),
                "cta_url": reverse("public_app:contact"),
                "cta_primary": False,
            },
        ],
        "rows": [
            ({"group": entry["group"]} if "group" in entry else entry)
            for entry in spec
        ],
        "notes": table_notes(),
    }


cloud_plan_comparison = plan_comparison


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
