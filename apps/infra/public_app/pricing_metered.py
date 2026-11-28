"""Metered-rate and API rows of the plan comparison table.

Split out of :mod:`apps.infra.public_app.pricing`. The catalogue is reached
through that module (``_catalog()``) so ``pricing.load_pricing`` patches apply.
"""

from __future__ import annotations

from typing import Any

from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy as _lazy

from .pricing_format import coming_soon, format_usd


def _catalog():
    from apps.infra.public_app import pricing

    return pricing


# Metered compute rates + API services for the comparison table. Rates are
# provider-wide (identical in every tier column); Self-Hosted runs on your
# own hardware so metered cells render a dash there. GPU-hour pricing bundles
# VRAM by model (no standalone VRAM rate exists in the SSOT), and per-service
# API credit costs are not set yet — the services row states the billing
# mechanism (Compute Credits + margin, coming soon) instead of inventing
# numbers. Closed enums throughout: unknown SSOT values raise loudly.
_API_KEY_DISPLAY = {
    "rate-limited": _lazy("Standard rate limits"),
    "priority-limited": _lazy("Priority rate limits"),
    "not-applicable": _lazy("—"),
}

_API_PRIORITY_DISPLAY = {
    "standard": _lazy("Standard queue"),
    "priority": _lazy("Priority queue"),
    "not-applicable": _lazy("—"),
}

# Individual apps are never named in the pricing table: Scholar, Stats,
# FigRecipe, Writer and friends are all just Applications, billed at the
# metered compute rates like everything else.


def _metered_and_api_rows() -> list[dict[str, Any]]:
    card = _catalog().load_pricing()["rate_card"]
    comp = card["compute"]
    api = card.get("api") or {}
    margin = card["payg_margin_pct"]

    keys = api.get("keys") or {}
    for tier in ("free", "pro", "self_hosted"):
        if keys.get(tier) not in _API_KEY_DISPLAY:
            raise ValueError(
                f"api.keys[{tier!r}] is {keys.get(tier)!r} in pricing.json; "
                "extend _API_KEY_DISPLAY deliberately."
            )
    priority_cells = _priority_cells()

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
        _("Follow the metered compute rates — no separate fee")
    )
    agents_pct = api.get("agents_fee_percent", 10)
    agents_line = coming_soon(
        _("Metered compute + model API × %(factor)s")
        % {"factor": f"{100 + agents_pct}%"}
    )
    per_service_api_line = coming_soon(
        _("Follow the metered compute rates")
    )
    return [
        {"group": coming_soon(_("Compute"))},
        {
            "label": _("CPU"),
            "cells": [cpu_cell, cpu_cell, dash, dash],
            "nowrap": True,
        },
        {
            "label": _("Memory"),
            "cells": [mem_cell, mem_cell, dash, dash],
            "nowrap": True,
        },
        *({**r, "nowrap": True} for r in gpu_rows),
        {"group": _("Applications")},
        {"label": _("API keys"), "cells": key_cells, "nowrap": True},
        {
            "label": _("Applications"),
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

def _priority_cells() -> list[Any]:
    """Queue-priority cells, same for every shared resource.

    Pro requests jump ahead of Free when the system is busy — compute,
    storage, apps, API alike. Priority only: no per-minute numbers are
    claimed because none are enforced yet.
    """
    api = (_catalog().load_pricing()["rate_card"].get("api") or {})
    priority = api.get("priority") or {}
    for tier in ("free", "pro", "self_hosted"):
        if priority.get(tier) not in _API_PRIORITY_DISPLAY:
            raise ValueError(
                f"api.priority[{tier!r}] is {priority.get(tier)!r} in pricing.json; "
                "extend _API_PRIORITY_DISPLAY deliberately."
            )
    return [
        _API_PRIORITY_DISPLAY[priority["free"]],
        _API_PRIORITY_DISPLAY[priority["pro"]],
        _API_PRIORITY_DISPLAY[priority["self_hosted"]],
        _API_PRIORITY_DISPLAY[priority["self_hosted"]],
    ]
