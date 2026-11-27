"""The landing-page plan comparison table, rendered from the catalogue.

Split out of :mod:`apps.infra.public_app.pricing`, which re-exports it. The
catalogue is always reached through that module (``_catalog()``), so a test
that patches ``pricing.load_pricing`` reaches this table too.
"""

from __future__ import annotations

from typing import Any

from django.utils.translation import gettext as _

from .pricing_attributes import (
    _LICENSE_TERM_DISPLAY,
    _LICENSE_TERM_LABELS,
    _credit_text,
)
from .pricing_format import coming_soon, format_amount, format_usd
from .pricing_metered import _catalog, _metered_and_api_rows, _priority_cells


def _merge_repeated_cells(spec: list[dict]) -> None:
    """Collapse vertical runs of identical cells with rowspan, in place.

    The self-hosted columns repeat one line ("Your own hardware", or "—"
    where nothing applies) down whole sections. Rendering every copy turns
    the table into a wall of repetition, so a run of 3+ identical cells in
    one column becomes a single cell with rowspan. Two-row runs stay
    unmerged: a rowspan cell suppresses the intermediate row border in the
    collapsed-border model, leaving a visible gap (Coupons, Support/SLA).
    Runs never cross a
    group header. The first row gets ``rs2``/``rs3`` spans; the covered
    rows get ``skip2``/``skip3`` flags (flat keys keep the template free
    of dict lookups). ``cells`` stay plain strings (tests read them);
    the template consults the annotations.
    """
    MERGEABLE_COLS = (2, 3)  # the two self-hosted plan columns
    run_value: dict[int, str | None] = dict.fromkeys(MERGEABLE_COLS)
    run_start: dict[int, int] = {}
    labeled = [e for e in spec if "cells" in e]

    def flush(col: int, end: int) -> None:
        start = run_start.get(col)
        if start is None or end - start < 3:
            return
        labeled[start][f"rs{col}"] = end - start
        for i in range(start + 1, end):
            labeled[i][f"skip{col}"] = True

    idx = 0
    for entry in spec:
        if "cells" not in entry:
            for col in MERGEABLE_COLS:
                flush(col, idx)
                run_value[col] = None
                run_start.pop(col, None)
            continue
        for col in MERGEABLE_COLS:
            value = str(entry["cells"][col])
            if value and value == run_value[col]:
                pass
            else:
                flush(col, idx)
                run_value[col] = value or None
                run_start[col] = idx
        idx += 1
    for col in MERGEABLE_COLS:
        flush(col, idx)


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
    card = _catalog().load_pricing()["rate_card"]
    for tier in card.get("storage_tiers") or []:
        if not tier.get("name") or not tier.get("meaning"):
            raise ValueError(
                f"storage_tiers entry {tier!r} needs name and meaning; "
                "fix pricing.json."
            )
    return [
        _(
            "Each Compute Credit is worth %(one)s of metered usage: "
            "CPU, memory and GPU hours, plus API calls."
        )
        % {"one": format_usd(1)},
        _(
            "There is no separate VRAM rate: GPU-hour pricing already "
            "includes memory by model."
        ),
        _(
            "Storage speeds are approximate live measurements; actual "
            "throughput varies with workload, network, concurrent use, "
            "caching, disk fill, drive media, and time of day."
        ),
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
        for r in _catalog().published_price_rows(today)
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

    def cpu_cell(row, optional=False):
        if "cpu" not in limits(row):
            return _("—")
        text = str(limits(row)["cpu"])
        return _("%(n)s (+ optional)") % {"n": text} if optional else text

    def ram_cell(row, optional=False):
        if "memory_gb" not in limits(row):
            return _("—")
        text = _("%(gb)s GB") % {"gb": limits(row)["memory_gb"]}
        return _("%(n)s (+ optional)") % {"n": text} if optional else text

    def gpu_cell(row):
        if "gpu" not in limits(row):
            return _("—")
        return _("GPU included") if limits(row)["gpu"] else _("No GPU")

    def credit_cell(row):
        if "included_compute_credit" not in row["attributes"]:
            return _("—")
        return _credit_text(row["attributes"]["included_compute_credit"])

    def tier_cell(row, tier, optional=False):
        storage = row["attributes"].get("included_storage") or {}
        if storage.get("tier") != tier:
            return _("Optional") if optional else _("—")
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
            (
                t.get("meaning", "")
                for t in _catalog().load_pricing()["rate_card"].get("storage_tiers", [])
                if t.get("name") == tier
            ),
            "",
        )
        return _("%(tier)s\n%(meaning)s\n%(speed)s") % {
            "tier": _(tier),
            # Wrapped so the table renders meaning and speed de-emphasized
            # (smaller, lighter) under the tier name. The meaning comes from
            # pricing.json but is translated here so the JA table does not
            # fall back to English for the one line with no cell of its own.
            "meaning": '<span class="tier-sub">%s</span>' % _(meaning),
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
                f"license_terms[{term!r}] is {terms.get(term)!r}; fix pricing.json."
            )
        return display[terms[term]]

    license_rows = [
        {"group": _("Self-hosted license")},
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
    coupons = _catalog().load_pricing().get("coupons") or {}
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
    coupon_codes = [
        {
            "code": c["code"],
            "description": c.get("description", ""),
            "price": format_amount(c["monthly_price"], c.get("unit", "month")),
        }
        for c in coupons.get("codes", [])
        if c.get("code") and c.get("monthly_price") is not None
    ]
    spec = (
        [
            {"label": _("Price"), "cells": price_cells, "code": "price"},
            {
                "label": _("Coupons"),
                "cells": coupon_cells,
                "code": "coupons",
                # The coupon input + Apply live directly in this column's cell
                # (0=Free, 1=Pro, 2=AGPL, 3=Enterprise) — no detached form.
                "coupon_input_col": 1,
            },
            {
                "label": _("Queue priority"),
                "cells": _priority_cells(),
                "nowrap": True,
            },
            {"group": _("Resources")},
            {
                "label": _("CPU"),
                "cells": [
                    cpu_cell(free),
                    cpu_cell(pro, optional=True),
                    hosted_line,
                    hosted_line,
                ],
            },
            {
                "label": _("RAM"),
                "cells": [
                    ram_cell(free),
                    ram_cell(pro, optional=True),
                    hosted_line,
                    hosted_line,
                ],
            },
            {
                "label": _("GPU"),
                "cells": [gpu_cell(free), gpu_cell(pro), hosted_line, hosted_line],
            },
            {
                "label": _("Compute credits"),
                "cells": [
                    credit_cell(free),
                    credit_cell(pro),
                    hosted_line,
                    hosted_line,
                ],
            },
            {"group": _("Storage")},
            {
                "label": tier_label("Hot"),
                "cells": [
                    tier_cell(free, "Hot"),
                    tier_cell(pro, "Hot", optional=True),
                    hosted_line,
                    hosted_line,
                ],
            },
            {
                "label": tier_label("Warm"),
                "cells": [
                    tier_cell(free, "Warm"),
                    tier_cell(pro, "Warm", optional=True),
                    hosted_line,
                    hosted_line,
                ],
            },
            {
                "label": tier_label("Cool"),
                "cells": [
                    tier_cell(free, "Cool"),
                    tier_cell(pro, "Cool"),
                    hosted_line,
                    hosted_line,
                ],
            },
            {
                "label": tier_label("Cold"),
                "cells": [
                    tier_cell(free, "Cold"),
                    tier_cell(pro, "Cold", optional=True),
                    hosted_line,
                    hosted_line,
                ],
            },
        ]
        + license_rows
        + _metered_and_api_rows()
    )
    _merge_repeated_cells(spec)
    from django.urls import reverse

    return {
        "columns": [
            {
                "label": _("SciTeX® Cloud Free"),
                "recommended": False,
                "cta_label": _("Create a free account"),
                "cta_url": reverse("auth_app:signup"),
                "cta_primary": False,
            },
            {
                "label": _("SciTeX® Cloud Pro"),
                "recommended": True,
                "cta_label": _("Start with Pro"),
                "cta_url": reverse("auth_app:signup"),
                "cta_primary": True,
            },
            {
                "label": _("SciTeX® Self-Hosted (AGPL)"),
                "recommended": False,
                "cta_label": _("Get the source"),
                "cta_url": _catalog().load_pricing()["links"]["self_hosted_source"],
                "cta_primary": False,
                "cta_external": True,
            },
            {
                "label": _("SciTeX® Self-Hosted (Enterprise)"),
                "recommended": False,
                "cta_label": _("Contact us"),
                "cta_url": reverse("public_app:contact"),
                "cta_primary": False,
            },
        ],
        "rows": [
            ({"group": entry["group"]} if "group" in entry else entry) for entry in spec
        ],
        "notes": table_notes(),
        "coupon_codes": coupon_codes,
    }


cloud_plan_comparison = plan_comparison
