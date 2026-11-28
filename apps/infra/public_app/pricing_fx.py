"""The yen REFERENCE shown next to USD prices (USD is the only stored currency).

Split out of :mod:`apps.infra.public_app.pricing`, which re-exports it.
"""

from __future__ import annotations


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
