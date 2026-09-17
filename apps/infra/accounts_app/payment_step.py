#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The payment step's disclosures — the numbers a person needs BEFORE Stripe.

Card: hub-signup-email-stripe-funnel-20260917 (walkthrough 7929-7934).
SSOT: docs/product/PRIVATE_BETA_LOGIN_TO_WOW.md §2 — "Before Stripe, show plan,
price, amount due today, trial end/first charge date, auto-renewal, cancellation,
and tax treatment."

Why a module rather than copy in a template: these six facts are the commitment a
customer is being asked to make, and they must be identical in the payment step
and anywhere else we state them. The dates are derived from the SAME trial window
the account system uses (``billing_provider.trial_window``), so a change to the
trial length cannot leave the disclosure claiming the old date.

Nothing here talks to Stripe or decides entitlement: the provider's hosted page
takes the card, and the webhook owns the state (both backend, per the card's
boundary note). This is the surface that states terms and hands over.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

#: The facts the surface must show, in the order it shows them.
DISCLOSURE_FIELDS = (
    "plan_label",
    "price_per_month",
    "due_today",
    "trial_ends_on",
    "first_charge_on",
    "renewal",
    "cancellation",
    "tax",
)

#: What the step is doing, as the user sees it.
PENDING = "pending"                    # verified, no usable card yet
SETUP_CANCELLED = "setup_cancelled"    # came back from Stripe without finishing
USABLE = "usable"                      # a confirmed usable card exists
NOT_OPEN = "not_open"                  # provider not configured yet: no card can be taken
PLAN_UNSET = "plan_unset"              # catalog has no deterministic signup plan: do not guess

#: States the surface knows how to render.
STATES = (PENDING, SETUP_CANCELLED, USABLE, NOT_OPEN, PLAN_UNSET)

#: Catalog keys that would explicitly mark a plan as the one new signups get.
#: None of them exists in pricing.json today, which is why the step refuses to
#: choose a plan rather than showing whichever row happens to be first.
SIGNUP_DEFAULT_KEYS = ("signup_default", "default", "recommended")


def select_signup_plan(rows, explicit_id: Optional[str] = None, chargeable_ids=None):
    """The plan a new signup is placed on — or ``None``, never an arbitrary row.

    ``subscription_pricing_rows()`` returns the catalog in file order, so ``rows[0]``
    is arbitrary: today that would put every new signup on whichever of the two
    subscription rows the JSON lists first, silently.

    Four rules, in order, and only the first three can answer:

    1. an explicit ``explicit_id`` (carried through signup/OTP) that matches a row;
    2. exactly one row explicitly marked as the signup default in the catalog;
    3. exactly one row this deployment can actually CHARGE for (``chargeable_ids``,
       from the configured price ids) — quoting a plan nobody can pay for is its own
       bug, so "the only plan with a price" is determined rather than arbitrary;
    4. otherwise ``None``. The caller renders a "plan not set up" state instead of
       inventing a price, and ambiguity (two marked rows, two chargeable rows, an
       unknown explicit id) is also ``None``: refusing is recoverable, quoting the
       wrong plan to a customer is not.
    """
    if not rows:
        return None

    if explicit_id:
        return next((row for row in rows if row.get("id") == explicit_id), None)

    marked = [row for row in rows if any(row.get(key) is True for key in SIGNUP_DEFAULT_KEYS)]
    if len(marked) == 1:
        return marked[0]
    if len(marked) > 1:
        return None

    if chargeable_ids:
        chargeable = [row for row in rows if row.get("id") in set(chargeable_ids)]
        if len(chargeable) == 1:
            return chargeable[0]

    return None


@dataclass(frozen=True)
class Disclosures:
    """The terms, already formatted for display."""

    plan_label: str
    price_per_month: str
    due_today: str
    trial_ends_on: str
    first_charge_on: str
    renewal: str
    cancellation: str
    tax: str
    state: str

    def as_context(self) -> dict:
        return {field: getattr(self, field) for field in DISCLOSURE_FIELDS} | {
            "state": self.state
        }


def _usd(amount: float) -> str:
    return f"${amount:,.2f}"


def _date(dt: Optional[datetime]) -> str:
    return dt.strftime("%d %B %Y") if dt else ""


def payment_disclosures(
    *,
    plan_label: str,
    monthly_usd: float,
    trial_end: Optional[datetime],
    state: str = PENDING,
    now: Optional[datetime] = None,
) -> Disclosures:
    """Build the pre-payment disclosure block.

    ``due_today`` is always zero: the card is registered now and the first charge
    happens at the end of the trial. ``first_charge_on`` is the same instant as
    ``trial_ends_on`` because that is what "converts at the end of the trial"
    means — two labels, one date, and the surface says so rather than leaving the
    reader to infer it.
    """
    state = state if state in STATES else PENDING
    reference = now or datetime.now(trial_end.tzinfo if trial_end else None)

    if trial_end is None:
        # Without a trial window we cannot state dates honestly, so we state none
        # rather than a plausible-looking date someone might plan around.
        return Disclosures(
            plan_label=plan_label,
            price_per_month=_usd(monthly_usd),
            due_today=_usd(0),
            trial_ends_on="",
            first_charge_on="",
            renewal="billed monthly once the trial ends",
            cancellation="cancel any time before the first charge",
            tax="Sales tax or VAT is added at checkout where it applies.",
            state=state,
        )

    days_left = max(0, (trial_end - reference).days)
    return Disclosures(
        plan_label=plan_label,
        price_per_month=_usd(monthly_usd),
        due_today=_usd(0),
        trial_ends_on=_date(trial_end),
        first_charge_on=_date(trial_end),
        renewal=(
            "billed monthly, automatically, starting the day the trial ends"
        ),
        cancellation=(
            f"cancel any time before {_date(trial_end)} and you are not charged"
            + (f" ({days_left} days left in the trial)" if days_left else " (final day)")
        ),
        tax="Sales tax or VAT is added at checkout where it applies.",
        state=state,
    )


def trial_state(*, has_usable_card: bool, returned_from_setup: bool = False) -> str:
    """Which step state to render, from facts the backend already owns."""
    if has_usable_card:
        return USABLE
    return SETUP_CANCELLED if returned_from_setup else PENDING


# EOF
