#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Page-level views of the pricing SSOT: rate card, policies, shared context.

``pricing.py`` owns the catalogue rows and how one price is formatted; this
module assembles what the /pricing/, /services/ and /tokushoho/ pages render
beyond the rows — the metered rate card (SSOT §3-5), the Academic License
boundary (§1) and the beta service-quality policies (§2, §6-8) — plus the one
context builder /pricing/ and /services/ share so they cannot drift apart.
"""

from __future__ import annotations

from typing import Any

from django.utils.translation import gettext as _

from .pricing import format_usd, load_pricing, published_price_groups, tier_rows

__all__ = [
    "academic_license_boundary",
    "beta_policies",
    "pricing_page_context",
    "rate_card",
    "shared_included",
]


def rate_card() -> dict[str, Any]:
    """The metered rates (storage tiers, network, compute), formatted.

    Tier names only — pricing.json carries no internal hardware mapping, so
    nothing here can leak one. Compute billing is not live: every compute line
    is returned with ``coming_soon`` so the template labels it.
    """
    card = load_pricing()["rate_card"]
    storage = []
    for tier in card["storage_tiers"]:
        if tier.get("included_with_compute"):
            price = _("Included with active compute")
        else:
            price = _("%(price)s / GB-month") % {"price": format_usd(tier["amount"])}
        storage.append(
            {
                "name": tier["name"],
                "meaning": _(tier["meaning"]),
                "price": price,
                "note": _(tier["note"]),
            }
        )
    net = card["network"]
    network = [
        {"label": _("Internet ingress"), "price": _("Free")},
        {"label": _("Transfer inside SciTeX infrastructure"), "price": _("Free")},
        {
            "label": _("Internet egress included per paid billing cycle"),
            "price": f"{net['included_egress_gb']} GB",
        },
        {
            "label": _("Egress above included amount"),
            "price": _("%(price)s / GB") % {"price": format_usd(net["egress_over_amount"])},
        },
    ]
    comp = card["compute"]
    rate = comp["cpu_unit_rate"]
    cpu_sizes = [
        {
            "name": f"CPU {n}",
            "resources": f"{n} vCPU + {4 * n} GiB",
            "price": format_usd(round(rate * n, 3)) + "/h",
        }
        for n in comp["cpu_sizes"]
    ]
    gpus = [
        {
            "name": gpu["name"],
            "price": _("%(price)s / GPU-hour") % {"price": format_usd(gpu["amount"])},
        }
        for gpu in comp["gpus"]
    ]
    compute = {
        "coming_soon": bool(comp.get("coming_soon")),
        "credit_line": _("1 Compute Credit = %(price)s of metered SciTeX compute usage.")
        % {"price": format_usd(1)},
        "cpu_unit_line": _("1 CPU Unit = 1 vCPU + 4 GiB RAM, at %(price)s per CPU Unit-hour.")
        % {"price": format_usd(rate)},
        "memory_line": _("Additional memory beyond the standard ratio: %(price)s / GiB-hour.")
        % {"price": format_usd(comp["memory_addon_rate"])},
        "gpu_line": _(
            "GPU is billed by GPU model-hour; standard host CPU/RAM for normal GPU use is included."
        ),
        "external_line": _(
            "If a resource is unavailable at the published rate, you may choose external "
            "compute: actual provider cost + %(pct)s%% service fee, shown and locked before "
            "the job starts."
        )
        % {"pct": comp["external_fee_percent"]},
        "cpu_sizes": cpu_sizes,
        "gpus": gpus,
    }
    # The template adds the "Coming soon" badge next to this heading.
    compute["label"] = _("Compute billing")
    return {"storage": storage, "network": network, "compute": compute}


def shared_included(rows: list[dict[str, Any]]) -> list[str]:
    """One "what's included" list for rows that mostly share it (Cloud Academic
    and Cloud Standard). An item every row carries is listed once; an item only
    some rows carry (Academic eligibility) is prefixed with that row's label."""
    lists = [row["included"] for row in rows]
    out: list[str] = []
    for row in rows:
        for item in row["included"]:
            if all(item in other for other in lists):
                if item not in out:
                    out.append(item)
            else:
                out.append(f"{_(row['label'])} — {item}")
    return out


def pricing_page_context() -> dict[str, Any]:
    """Everything /pricing/ and /services/ render from the SSOT, in the active
    language. Both pages call this, so they cannot show different numbers."""
    data = load_pricing()
    tiers = tier_rows()
    cloud = next((t for t in tiers if t["id"] == "cloud"), None)
    return {
        "tiers": tiers,
        "published_price_groups": published_price_groups(),
        "cloud_included": shared_included(cloud["rows"]) if cloud else [],
        "rate_card": rate_card(),
        "academic_license_boundary": academic_license_boundary(),
        "beta_policies": beta_policies(),
        "tax_note": data.get("tax_note", ""),
        "pricing_notes": data["notes"],
    }


def academic_license_boundary() -> list[str]:
    """SSOT §1 Academic License boundary, translated."""
    return [_(line) for line in load_pricing()["academic_license_boundary"]]


def beta_policies() -> list[str]:
    """SSOT §2/§4/§5/§7/§8 beta service-quality and price policies, translated."""
    return [_(line) for line in load_pricing()["beta_policies"]]
