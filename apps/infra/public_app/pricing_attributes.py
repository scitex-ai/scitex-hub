"""How each catalogue attribute reads to a visitor (cards, 特商法 page).

Split out of :mod:`apps.infra.public_app.pricing`, which re-exports it.
"""

from __future__ import annotations

import functools
from typing import Any

from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy as _lazy

from .pricing_format import coming_soon, format_usd

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
    return _("Runs on your own hardware — CPU, RAM, GPU and storage are yours")


# Self-hosted license contrast (AGPL vs Commercial). The table renders one
# "(AGPL) / (Commercial)" cell per term from BOTH rows' SSOT dicts, so the
# incentives can never drift from the catalogue. Values are closed enums:
# an unknown value is a red ValueError, not a silently wrong cell.
# NOTE: module-level display dicts use gettext_lazy — plain gettext here would
# freeze English at import time and every JA page would show English cells
# (measured live: "Standard rate limits" stayed English under ja until this fix).
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


SPEND_CAP_KEYS = frozenset({"default_usd", "max_usd", "unit", "scope"})
SPEND_CAP_UNIT = "USD/billing-cycle"


def validate_spend_cap(value: Any) -> None:
    """``spend_cap``: a plan's default monthly usage cap and the most a holder
    may raise it to (USD per billing cycle, usage beyond the plan fee).

    Read by spend controls (``spend_app.services.catalog``). The values are
    mirrored from the scitex-affairs catalog, whose
    ``scripts/pricing/check_drift.py`` compares ``default_usd`` / ``max_usd``
    with this file.
    """
    if not isinstance(value, dict):
        raise ValueError(f"spend_cap must be an object, got {value!r}")
    unknown = set(value) - SPEND_CAP_KEYS
    if unknown:
        raise ValueError(
            f"unknown spend_cap keys {sorted(unknown)}; expected a subset of "
            f"{sorted(SPEND_CAP_KEYS)}."
        )
    default, maximum = value.get("default_usd"), value.get("max_usd")
    for key, amount in (("default_usd", default), ("max_usd", maximum)):
        if isinstance(amount, bool) or not isinstance(amount, (int, float)):
            raise ValueError(f"spend_cap.{key} must be a USD number, got {amount!r}")
    if not 0 <= default <= maximum:
        raise ValueError(
            f"spend_cap needs 0 <= default_usd <= max_usd, got {default} / {maximum}"
        )
    if value.get("unit", SPEND_CAP_UNIT) != SPEND_CAP_UNIT:
        raise ValueError(
            f"spend_cap.unit is {value.get('unit')!r}; spend controls enforce "
            f"only {SPEND_CAP_UNIT!r}."
        )


# Attributes the catalogue carries for the platform to ENFORCE, not for a page
# to state. Each one is validated and deliberately renders no phrase: the
# per-plan cap values are provisional and spend controls start in shadow mode,
# so the public pages keep saying only that the cap is user-set (coming soon,
# via ``monthly_limit_set_by``). Publishing one later means moving it to
# _ATTRIBUTE_TEXT with its wording, on purpose.
_ENFORCEMENT_ATTRIBUTES = {
    "spend_cap": validate_spend_cap,
}


def displayed_attributes(attributes: dict[str, Any]) -> dict[str, Any]:
    """``attributes`` minus the enforcement-only ones, each validated first."""
    shown = {}
    for key, value in attributes.items():
        if key in _ENFORCEMENT_ATTRIBUTES:
            _ENFORCEMENT_ATTRIBUTES[key](value)
        else:
            shown[key] = value
    return shown


def included_items(attributes: dict[str, Any], basis: str = "") -> list[str]:
    """What a row includes, one short phrase per attribute, in catalogue order.

    Raises on an attribute name this module does not know: the catalogue is
    committed with the code that renders it, so an unknown field is a red CI
    rather than a silently shorter legal page. Enforcement-only attributes
    (``_ENFORCEMENT_ATTRIBUTES``) are validated and contribute no phrase.
    """
    text = dict(_ATTRIBUTE_TEXT)
    if basis:
        text["included_storage"] = functools.partial(_storage_text, basis=basis)
        text["included_compute_credit"] = functools.partial(_credit_text, basis=basis)
    items = []
    for key, value in displayed_attributes(attributes).items():
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
