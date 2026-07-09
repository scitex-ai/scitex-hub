#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: config/settings/settings_commerce.py
"""Commerce / legal-compliance settings for SciTeX Hub.

Single source of truth for:

1. Company information rendered on the 特定商取引法に基づく表記
   (Specified Commercial Transactions Act) page. Values that are not
   finalized yet (office address, phone number, public contact email)
   MUST stay unset in the environment — the page then renders an
   explicit 「準備中」 notice instead of a fake value (no-fake-data
   principle).

2. The config-driven paid-plan list for the pricing page. While no
   plans are configured (the default), the pricing page renders the
   honest alpha-free / 準備中 state. Prices are ALWAYS tax-inclusive
   (総額表示義務 — Consumption Tax Act requires 税込 display for
   consumer-facing prices).

3. Stripe scaffold keys. Checkout / webhook endpoints return an
   explicit 503 while these are unset (fail loud, no silent fallback).
   Secret values come ONLY from the environment (SECRET/.env.{dev,nas})
   and are never logged.

Environment keys (document in SECRET/.env.nas when finalized):

- ``SCITEX_HUB_COMPANY_NAME``            販売業者 (default: 株式会社 SciTeX)
- ``SCITEX_HUB_COMPANY_REPRESENTATIVE``  運営統括責任者 (default: 渡邉 裕亮 —
                                         operator: please confirm this is
                                         the legally correct kanji for
                                         your name before this page is
                                         relied on for real filings; a
                                         different rendering, 渡邊裕亮, has
                                         also been used elsewhere)
- ``SCITEX_HUB_COMPANY_ADDRESS``         所在地 — NOT YET DETERMINED (blocked
                                         on operator input; see cards
                                         s2sell-hub-tokushoho-page /
                                         hub-tokushoho-legal-email-wire).
                                         特定商取引法 requires the
                                         registered place of business
                                         precise to room/apartment number
                                         — stricter than what corporate
                                         registration (登記) requires, and
                                         a DIFFERENT value than any
                                         residential address used
                                         elsewhere (e.g. Terms of
                                         Use/Privacy Policy contact
                                         address). Never fabricate or
                                         reuse an unrelated address here
                                         — unset until the operator
                                         supplies the exact registered
                                         address → template renders 準備中.
- ``SCITEX_HUB_COMPANY_PHONE``           電話番号 — NOT YET DETERMINED. A
                                         personal candidate number was
                                         floated in
                                         hub-tokushoho-legal-email-wire
                                         but explicitly marked pending
                                         operator confirmation (personal
                                         vs. company line) — deliberately
                                         NOT wired here. Unset → 準備中.
- ``SCITEX_HUB_COMPANY_CONTACT_EMAIL``   公開メールアドレス (default:
                                         legal@scitex.ai — the operator's
                                         confirmed company email, already
                                         live on the Terms of Use /
                                         Privacy Policy pages; resolves
                                         hub-tokushoho-legal-email-wire).
                                         Override via env if it ever
                                         changes.
- ``SCITEX_HUB_BILLING_PLANS``           JSON list of plan objects, each:
                                         {"name": str,
                                          "price_tax_included": int,
                                          "currency": "jpy",
                                          "interval": "month"|"year"|"once",
                                          "stripe_price_id": str}
- ``SCITEX_HUB_STRIPE_SECRET_KEY``       Stripe secret key (sk_test_... /
                                         sk_live_...)
- ``SCITEX_HUB_STRIPE_WEBHOOK_SECRET``   Stripe webhook signing secret
                                         (whsec_...)
"""

import json

from config._env import getenv_with_legacy_alias as _getenv_alias

# ---------------------------------------
# Company information (特定商取引法に基づく表記)
# ---------------------------------------
COMPANY_NAME = _getenv_alias("SCITEX_HUB_COMPANY_NAME", "株式会社 SciTeX") or ""
COMPANY_REPRESENTATIVE = (
    _getenv_alias("SCITEX_HUB_COMPANY_REPRESENTATIVE", "渡邉 裕亮") or ""
)
# PLACEHOLDER — office address not yet determined by the operator.
# 特定商取引法 requires room/apartment-number precision (stricter than
# 登記/corporate registration) and this MUST NOT be guessed, invented,
# or backfilled from an unrelated address (e.g. a personal residence
# used elsewhere for Terms of Use/Privacy Policy contact purposes).
# Leave unset until the operator supplies the exact registered address
# — the tokushoho page then renders an explicit 準備中 notice instead
# of a fake value (no-fake-data principle). See cards:
# s2sell-hub-tokushoho-page, hub-tokushoho-legal-email-wire.
COMPANY_ADDRESS = _getenv_alias("SCITEX_HUB_COMPANY_ADDRESS", "") or ""
# PLACEHOLDER — phone number not yet determined. A personal number was
# floated as a candidate in hub-tokushoho-legal-email-wire but marked
# explicitly pending (personal vs. company line undecided) — do not
# wire it here without operator confirmation. Leave unset → 準備中.
COMPANY_PHONE = _getenv_alias("SCITEX_HUB_COMPANY_PHONE", "") or ""
# RESOLVED — legal@scitex.ai is the operator's confirmed company email
# (freee 会社設立 account; already public on Terms of Use/Privacy
# Policy). Resolves hub-tokushoho-legal-email-wire. Override via env
# if this ever changes.
COMPANY_CONTACT_EMAIL = (
    _getenv_alias("SCITEX_HUB_COMPANY_CONTACT_EMAIL", "legal@scitex.ai") or ""
)

# ---------------------------------------
# Billing plans (config-driven; empty = 準備中)
# ---------------------------------------
_BILLING_PLAN_REQUIRED_KEYS = {
    "name",
    "price_tax_included",
    "currency",
    "interval",
    "stripe_price_id",
}
_BILLING_PLAN_INTERVALS = {"month", "year", "once"}


def _load_billing_plans() -> list:
    """Parse SCITEX_HUB_BILLING_PLANS (JSON). Fail loud on bad config."""
    raw = _getenv_alias("SCITEX_HUB_BILLING_PLANS", "") or ""
    if not raw.strip():
        return []
    try:
        plans = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(
            "SCITEX_HUB_BILLING_PLANS is not valid JSON. Expected a JSON "
            "list of plan objects with keys: "
            f"{sorted(_BILLING_PLAN_REQUIRED_KEYS)}. Error: {exc}"
        ) from exc
    if not isinstance(plans, list):
        raise ValueError(
            "SCITEX_HUB_BILLING_PLANS must be a JSON list of plan objects, "
            f"got {type(plans).__name__}."
        )
    for idx, plan in enumerate(plans):
        if not isinstance(plan, dict):
            raise ValueError(
                f"SCITEX_HUB_BILLING_PLANS[{idx}] must be an object, "
                f"got {type(plan).__name__}."
            )
        missing = _BILLING_PLAN_REQUIRED_KEYS - set(plan)
        if missing:
            raise ValueError(
                f"SCITEX_HUB_BILLING_PLANS[{idx}] is missing required "
                f"keys: {sorted(missing)}. Prices must be tax-inclusive "
                "(総額表示義務) — use 'price_tax_included'."
            )
        if plan["interval"] not in _BILLING_PLAN_INTERVALS:
            raise ValueError(
                f"SCITEX_HUB_BILLING_PLANS[{idx}]['interval'] must be one "
                f"of {sorted(_BILLING_PLAN_INTERVALS)}, "
                f"got {plan['interval']!r}."
            )
    return plans


BILLING_PLANS = _load_billing_plans()

# ---------------------------------------
# Stripe scaffold (env-only secrets; never logged)
# ---------------------------------------
STRIPE_SECRET_KEY = _getenv_alias("SCITEX_HUB_STRIPE_SECRET_KEY", "") or ""
STRIPE_WEBHOOK_SECRET = _getenv_alias("SCITEX_HUB_STRIPE_WEBHOOK_SECRET", "") or ""

# EOF
