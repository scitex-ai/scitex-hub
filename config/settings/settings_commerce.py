#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: config/settings/settings_commerce.py
"""Commerce / legal-compliance settings for SciTeX Hub.

Single source of truth for:

1. Company information rendered on the 特定商取引法に基づく表記
   (Specified Commercial Transactions Act) page. Any value that is not
   finalized MUST stay unset — the page then renders an explicit
   「準備中」 notice instead of a fake value (no-fake-data principle).
   As of 2026-07-30 every field is operator-confirmed, so nothing here
   renders 準備中; each default below cites the confirmation that
   settled it, and a test in tests/apps/public_app/views/
   test_tokushoho.py pins it.

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
- ``SCITEX_HUB_COMPANY_REPRESENTATIVE``  運営統括責任者 (default: 渡邉 裕亮)
- ``SCITEX_HUB_COMPANY_ADDRESS``         所在地 (default: the REGISTERED
                                         office, 〒420-0857 静岡県静岡市葵区御幸町３－２１ペガサートビル７階静岡市コ・クリエーションスペース内
                                         — taken byte-for-byte from the 国税庁
                                         record for 法人番号 4080001027758,
                                         2026-08-28. Full-width ３－２１ is
                                         U+FF0D and ７階 is U+FF17; do NOT
                                         normalise to ASCII, Stripe's
                                         corporate review compares this
                                         against the registry.)
- ``SCITEX_HUB_COMPANY_PHONE``           電話番号 (default: 080-4022-3567
                                         — operator-confirmed 2026-07-18)
- ``SCITEX_HUB_COMPANY_CONTACT_EMAIL``   公開メールアドレス (default:
                                         info@scitex.ai — operator-confirmed
                                         2026-07-30)
- ``SCITEX_HUB_SERVICES_INQUIRY_EMAIL``  /services 問い合わせ通知先 (default:
                                         info@scitex.ai — operator-confirmed
                                         2026-07-30. Unset = persist to the DB
                                         and notify nobody; never recruit@)
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
- ``SCITEX_HUB_STRIPE_PRICE_<PRICING_ID>`` Stripe price id per pricing.json
                                         subscription row, e.g.
                                         SCITEX_HUB_STRIPE_PRICE_SUBSCRIPTION_GENERAL
- ``SCITEX_HUB_BILLING_PROVIDER``        billing provider name (default: stripe)

Setup + demo script: docs/ops/stripe-test-mode.md
"""

import json
import os

from config._env import getenv_with_legacy_alias as _getenv_alias

# ---------------------------------------
# Company information (特定商取引法に基づく表記)
# ---------------------------------------
COMPANY_NAME = _getenv_alias("SCITEX_HUB_COMPANY_NAME", "株式会社ＳｃｉＴｅＸ") or ""
COMPANY_REPRESENTATIVE = (
    _getenv_alias("SCITEX_HUB_COMPANY_REPRESENTATIVE", "渡邉 裕亮") or ""
)
# REGISTERED address, and the default is deliberately the real one.
# Updated 2026-08-28: the previous default (〒420-0839 葵区鷹匠2-8-10) was
# operator-confirmed 2026-07-18, three weeks BEFORE incorporation on
# 2026-08-08, so it never matched the registry. That office is also being
# given up at the end of 2026-08, so the old default was about to name a
# location that does not exist.
#
# This value is copied from the 国税庁 public record for 法人番号
# 4080001027758 rather than retyped, because the characters that differ are
# invisible: ３－２１ uses U+FF0D (FULLWIDTH HYPHEN-MINUS, not U+2212) and
# ７階 uses U+FF17. Stripe's corporate review compares the published address
# against that record, so a glyph-width "tidy-up" here is a compliance
# regression, not a formatting change.
#
# The DEFAULT is the correct value on purpose: an environment that forgets
# SCITEX_HUB_COMPANY_ADDRESS must publish the right registered office, not a
# stale one. Prod may still override; keep it in sync if it does.
COMPANY_ADDRESS = (
    _getenv_alias(
        "SCITEX_HUB_COMPANY_ADDRESS",
        "〒420-0857 静岡県静岡市葵区御幸町３－２１ペガサートビル７階静岡市コ・クリエーションスペース内",
    )
    or ""
)
# Representative phone — operator-confirmed 2026-07-18 (Telegram 1536).
COMPANY_PHONE = _getenv_alias("SCITEX_HUB_COMPANY_PHONE", "+81-80-4022-3567") or ""
# Public contact for the 特定商取引法 disclosure — operator-confirmed
# 2026-07-30 (「メールは info@scitex.ai で大丈夫です」), and they had already
# confirmed the mailbox delivers (「info@scitex.ai はもちろん届きますよ」).
# Both mattered: a 特商法 contact that bounces is a compliance defect, not a
# broken link, so the address was left empty (→ 準備中) until delivery was
# established rather than filled in with a plausible guess.
#
# Deliberately NOT read from ``config.branding.CONTACT_EMAIL``, which is the
# general/product enquiry address and currently holds the same value. They are
# the same string today and are NOT the same fact: this one is a statutory
# declaration and may only change when the operator says so, while the other is
# a product decision. Pointing this at branding would let a future contact
# refactor silently rewrite a legal filing. See config/branding.py, which
# carries the matching warning.
COMPANY_CONTACT_EMAIL = (
    _getenv_alias("SCITEX_HUB_COMPANY_CONTACT_EMAIL", "info@scitex.ai") or ""
)

# Services-page inquiry destination — operator-confirmed 2026-07-30
# (「OK, がんがんいきましょう、info@scitex.ai です」, after being told this setting
# was one of the two still empty). Deliberately SEPARATE from recruit@ (the
# hiring inbox) — mixing sales inquiries into hiring loses leads.
#
# Setting this CHANGES BEHAVIOUR rather than a displayed string, so it is worth
# being explicit about what it turns on. Empty meant /services persisted every
# inquiry to the DB (ServiceInquiry, readable in admin) and notified NOBODY, so
# a lead was only ever found by someone remembering to open the admin. With an
# address set, the inquiry is still persisted FIRST and the mail is best-effort
# on top: public_app/views/pages.py:110-137 returns early when unset, and logs
# loudly (never swallows) when a send fails. The DB stays the record either way,
# which is why enabling this can add a notification but cannot lose an inquiry.
SERVICES_INQUIRY_EMAIL = (
    _getenv_alias("SCITEX_HUB_SERVICES_INQUIRY_EMAIL", "info@scitex.ai") or ""
)

# The OPERATOR, told about every new inquiry at once (scitex-hub#1235): all 8
# prod inquiries sat unhandled because only the shared info@ box was mailed,
# and through an SMTP login prod refused. Delivery goes through
# scitex-notification (public_app/services/inquiry_notification.py), the same
# agent -> operator route the fleet uses. info@ above is still copied.
# Comma-separated for more than one address.
INQUIRY_NOTIFY_TO = (
    _getenv_alias("SCITEX_HUB_INQUIRY_NOTIFY_TO", "ywatanabe@scitex.ai") or ""
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

# Which BillingProvider implementation serves card setup and subscriptions.
BILLING_PROVIDER = os.environ.get("SCITEX_HUB_BILLING_PROVIDER", "stripe") or "stripe"

# SCITEX_HUB_STRIPE_PRICE_SUBSCRIPTION_GENERAL=price_... maps to the pricing.json
# row "subscription-general"; `manage.py stripe_bootstrap_test` prints these lines.
STRIPE_PRICE_ENV_PREFIX = "SCITEX_HUB_STRIPE_PRICE_"
STRIPE_PRICE_IDS = {
    name[len(STRIPE_PRICE_ENV_PREFIX) :].lower().replace("_", "-"): value
    for name, value in os.environ.items()
    if name.startswith(STRIPE_PRICE_ENV_PREFIX) and value
}

# ---------------------------------------
# Spend controls (apps/infra/spend_app)
# ---------------------------------------
# The CAP VALUES (default and maximum per plan) are prices, so they live in the
# price catalog (scitex-affairs -> pricing.json ``spend_cap``), not here. These
# are the Hub's operational knobs.


def _spend_int(name: str, default: int) -> int:
    raw = os.environ.get(name, "")
    return int(raw) if raw.strip() else default


def _spend_mode() -> str:
    mode = (os.environ.get("SCITEX_HUB_SPEND_CONTROLS_MODE", "") or "enforce").strip()
    if mode not in ("enforce", "shadow"):
        raise ValueError(
            "SCITEX_HUB_SPEND_CONTROLS_MODE must be 'enforce' or 'shadow', "
            f"not {mode!r}"
        )
    return mode


SPEND_CONTROLS = {
    # enforce: refuse/stop at the cap. shadow: compute, alert and log the
    # decision, but never refuse (for rollout); the UI says which is active.
    "mode": _spend_mode(),
    # Running work at 100 %: how long it keeps running after the warning.
    "running_grace_minutes": _spend_int("SCITEX_HUB_SPEND_RUNNING_GRACE_MINUTES", 15),
    # Failed payment: days of grace before the account is restricted.
    "payment_grace_days": _spend_int("SCITEX_HUB_BILLING_PAYMENT_GRACE_DAYS", 7),
    # Reminder emails, as days after the first failure (0 = at once).
    "payment_reminder_days": [
        int(d)
        for d in (
            os.environ.get("SCITEX_HUB_BILLING_PAYMENT_REMINDER_DAYS", "") or "0,3,6"
        ).split(",")
        if d.strip()
    ],
    # Cancellation billed on actual usage, from the subscription's start.
    "cancellation_window_days": _spend_int(
        "SCITEX_HUB_BILLING_CANCELLATION_WINDOW_DAYS", 30
    ),
    # Interactive sessions with no input or output for this long are stopped.
    "idle_stop_minutes": _spend_int("SCITEX_HUB_INTERACTIVE_IDLE_STOP_MINUTES", 30),
    "idle_warning_minutes": _spend_int(
        "SCITEX_HUB_INTERACTIVE_IDLE_WARNING_MINUTES", 5
    ),
    # How long a computed usage snapshot is reused by the request-path gate.
    "usage_cache_seconds": _spend_int("SCITEX_HUB_SPEND_USAGE_CACHE_SECONDS", 120),
}

# EOF
