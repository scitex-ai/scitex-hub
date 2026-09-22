#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The payment step's disclosures and its state machine.

Card: hub-signup-email-stripe-funnel-20260917 (walkthrough 7929-7934).
SSOT: docs/product/PRIVATE_BETA_LOGIN_TO_WOW.md §2 — "Before Stripe, show plan,
price, amount due today, trial end/first charge date, auto-renewal, cancellation,
and tax treatment."

Why a module rather than copy in a template: these facts are the commitment a
customer is being asked to make, and they must be identical in the payment step
and anywhere else we state them. The dates come from the SAME window the webhook
activates (``billing_provider.trial_window``), so a change to the trial length —
or the arrival of a provider-confirmed subscription — cannot leave the surface
claiming an old date.

PR #934 review: the state machine below is what makes the funnel CONTINUOUS.
Every way a person can leave the provider's page (finished, cancelled, failed,
or returned before the webhook arrived) has a state, a truthful sentence, and
exactly one way forward; a state that offers no action must say why (a plan the
deployment cannot charge for, a provider that is not configured).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
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
SETUP_FAILED = "setup_failed"          # the provider call itself failed
PROCESSING = "processing"              # card saved, provider confirmation in flight
ACTIVATED = "activated"                # PROVIDER-confirmed trial: the product is open
NOT_OPEN = "not_open"                  # provider not configured yet: no card can be taken
PLAN_UNSET = "plan_unset"              # no allowlisted plan: do not guess

#: States the surface knows how to render.
STATES = (
    PENDING,
    SETUP_CANCELLED,
    SETUP_FAILED,
    PROCESSING,
    ACTIVATED,
    NOT_OPEN,
    PLAN_UNSET,
)

#: States in which the step must offer the continue action.
ACTIONABLE_STATES = (PENDING, SETUP_CANCELLED, SETUP_FAILED)

#: Catalog keys that would explicitly mark a plan as the one new signups get.
SIGNUP_DEFAULT_KEYS = ("signup_default", "default", "recommended")


def select_signup_plan(rows, explicit_id: Optional[str] = None, chargeable_ids=None):
    """The plan a new signup is placed on — or ``None``, never an arbitrary row.

    ``subscription_pricing_rows()`` returns the catalog in file order, so
    ``rows[0]`` is arbitrary: today that would put every new signup on whichever
    of the two subscription rows the JSON lists first, silently.

    Four rules, in order, and only the first three can answer:

    1. an explicit ``explicit_id`` (carried through signup/OTP) that matches a
       row THIS DEPLOYMENT CAN CHARGE FOR;
    2. exactly one row explicitly marked as the signup default in the catalog;
    3. exactly one row this deployment can actually CHARGE for
       (``chargeable_ids``, from the configured price ids) — quoting a plan
       nobody can pay for is its own bug, so "the only plan with a price" is
       determined rather than arbitrary;
    4. otherwise ``None``. The caller renders a "plan not set up" state instead
       of inventing a price, and ambiguity (two marked rows, two chargeable
       rows, an unknown explicit id) is also ``None``: refusing is recoverable,
       quoting the wrong plan to a customer is not.

    PR #934 review, blocker 5: ``explicit_id`` used to be accepted against the
    whole catalog, so ``?plan=<any row id>`` won even when the deployment had no
    configured Stripe Price for it — and the selection was then dropped before
    the POST. When ``chargeable_ids`` is supplied, a row outside it is refused.
    """
    if not rows:
        return None

    chargeable = set(chargeable_ids) if chargeable_ids is not None else None

    if explicit_id:
        match = next((row for row in rows if row.get("id") == explicit_id), None)
        if match is None:
            return None
        if chargeable is not None and match.get("id") not in chargeable:
            return None
        return match

    marked = [row for row in rows if any(row.get(key) is True for key in SIGNUP_DEFAULT_KEYS)]
    if len(marked) == 1:
        row = marked[0]
        # A marked plan this deployment holds no price for is a configuration
        # conflict, and refusing is the honest outcome: silently quoting the
        # other plan would put the customer on a price the catalog never chose
        # for signups (blocker 5).
        if chargeable is not None and row.get("id") not in chargeable:
            return None
        return row
    if len(marked) > 1:
        return None

    if chargeable:
        chargeable_rows = [row for row in rows if row.get("id") in chargeable]
        if len(chargeable_rows) == 1:
            return chargeable_rows[0]

    return None


def funnel_plan(user, requested_id: Optional[str] = None, price_ids=None) -> Optional[dict]:
    """The plan the FUNNEL will charge this account for. Refuses rather than guesses.

    One resolver for both the step and the POST, so the price a person is shown
    and the price the provider is asked for cannot come apart:

    1. an explicitly requested id must be on the allowlist;
    2. otherwise the plan already recorded on the account's onboarding authority;
    3. otherwise the academic-aware default (academic email → the student row,
       anyone else → the non-student row; ambiguity still refuses);
    4. otherwise a lone allowlisted plan;
    5. otherwise ``None`` — the step says it does not know, and the POST refuses.
    """
    from apps.infra.public_app.services.billing_provider import (
        resolve_signup_plan,
        signup_plan_allowlist,
    )

    allowlist = signup_plan_allowlist(price_ids)
    if not allowlist:
        return None
    if requested_id:
        return resolve_signup_plan(requested_id, price_ids)
    if user is not None:
        from apps.infra.auth_app.onboarding import state_for

        authority = state_for(user)
        if authority is not None and authority.pricing_id:
            recorded = resolve_signup_plan(authority.pricing_id, price_ids)
            if recorded is not None:
                return recorded
    # Academic-aware default (operator 2026-09-22): the signup page already
    # promises "Academic pricing applied" for academic emails, so the funnel
    # must quote the matching plan rather than strand everyone on
    # "plan_unset" now that two plans are chargeable. Academic → the student
    # row; everyone else → the non-student row. Ambiguity (zero or several
    # matches) still refuses — quoting the wrong plan is not recoverable.
    email = (getattr(user, "email", "") or "") if user is not None else ""
    try:
        from apps.infra.auth_app.models import is_academic_email

        academic = bool(email) and bool(is_academic_email(email))
    except Exception:
        academic = False
    if academic:
        matches = [row for row in allowlist if "student" in (row.get("id") or "")]
    else:
        matches = [row for row in allowlist if "student" not in (row.get("id") or "")]
    if len(matches) == 1:
        return matches[0]
    if len(allowlist) == 1:
        return allowlist[0]
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


def trial_state(
    *,
    has_usable_card: bool,
    has_confirmed_trial: bool = False,
    returned_from_setup: bool = False,
    setup_failed: bool = False,
) -> str:
    """Which step state to render, from facts the backend already owns.

    The ORDER is the whole point (PR #934 review, blockers 2 and 3):

    * a provider-confirmed subscription outranks everything — the funnel is
      finished, and the surface says so and moves the person on;
    * a saved card is NOT a running trial. Before this, a usable card rendered
      "your payment method is already set up" and offered nothing, which is
      exactly the hole a browser could fall into between the redirect back and
      the webhook: the card exists, the subscription does not, and the user was
      told to go to billing settings. It now says activation is in flight and
      retries automatically — the 3DS/async case;
    * otherwise the way the attempt ended (cancelled, failed, or not started)
      decides, and every one of those offers the continue action again.
    """
    if has_confirmed_trial:
        return ACTIVATED
    if has_usable_card:
        return PROCESSING
    if returned_from_setup:
        return SETUP_CANCELLED
    if setup_failed:
        return SETUP_FAILED
    return PENDING


# EOF
