"""Price formatting for the catalogue: one agreed rendering per amount.

Split out of :mod:`apps.infra.public_app.pricing`, which re-exports it.
"""

from __future__ import annotations

from django.utils.translation import gettext as _

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
