#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The payment step states the terms before anyone is asked for a card.

Card: hub-signup-email-stripe-funnel-20260917 (walkthrough 7929-7934).
SSOT §2: "Before Stripe, show plan, price, amount due today, trial end/first
charge date, auto-renewal, cancellation, and tax treatment." And the trust line
the same section demands: raw card data never reaches SciTeX.

Measured before this change: a verified user was sent to the general billing
settings page (`post_signup_redirect_url` -> /accounts/settings/billing/?welcome=1),
which lists saved cards and plans but never states the trial's terms as a step —
there was no single surface that said what is due today, when the trial ends, when
the first charge lands, and how to cancel before it.

The template tests need no database; the route tests are gated for CI.
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone as tz

import pytest
from django.template.loader import render_to_string

from apps.infra.accounts_app.payment_step import (
    PENDING,
    SETUP_CANCELLED,
    USABLE,
    payment_disclosures,
    trial_state,
)

TEMPLATE = "accounts_app/payment_step.html"
TRIAL_END = datetime(2026, 10, 17, 9, 0, tzinfo=tz.utc)
NOW = datetime(2026, 9, 17, 9, 0, tzinfo=tz.utc)


def _disclosures(**overrides):
    kwargs = dict(plan_label="Academic Cloud", monthly_usd=20.0,
                  trial_end=TRIAL_END, now=NOW)
    kwargs.update(overrides)
    return payment_disclosures(**kwargs)


def _text(html: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html)).strip()


# ---------------------------------------------------------------------------
# the disclosures themselves (no database)
# ---------------------------------------------------------------------------


def test_every_required_disclosure_is_present():
    context = _disclosures().as_context()

    for field in ("plan_label", "price_per_month", "due_today", "trial_ends_on",
                  "first_charge_on", "renewal", "cancellation", "tax"):
        assert context.get(field), f"missing disclosure: {field}"


def test_nothing_is_due_today_and_the_first_charge_is_the_trial_end():
    context = _disclosures().as_context()

    assert context["due_today"] == "$0.00", context["due_today"]
    assert context["first_charge_on"] == context["trial_ends_on"], (
        "the first charge must be the day the trial ends, not a different date"
    )
    assert context["trial_ends_on"] == "17 October 2026"
    assert "20.00" in context["price_per_month"]


def test_cancellation_names_the_deadline_and_the_days_left():
    context = _disclosures().as_context()

    assert "17 October 2026" in context["cancellation"]
    assert "30 days left" in context["cancellation"]


def test_the_renewal_and_tax_lines_say_what_they_do():
    context = _disclosures().as_context()

    assert "monthly" in context["renewal"].lower()
    assert "automatically" in context["renewal"].lower()
    assert "tax" in context["tax"].lower() or "vat" in context["tax"].lower()


def test_without_a_trial_window_no_date_is_invented():
    """A plausible-looking date is worse than none: people plan around dates."""
    context = payment_disclosures(plan_label="Academic Cloud", monthly_usd=20.0,
                                  trial_end=None).as_context()

    assert context["trial_ends_on"] == ""
    assert context["first_charge_on"] == ""
    assert context["due_today"] == "$0.00"
    assert context["cancellation"]


def test_the_step_state_follows_the_account_facts():
    assert trial_state(has_usable_card=True) == USABLE
    assert trial_state(has_usable_card=False) == PENDING
    assert trial_state(has_usable_card=False, returned_from_setup=True) == SETUP_CANCELLED


# ---------------------------------------------------------------------------
# the surface (no database)
# ---------------------------------------------------------------------------


def _render(**overrides) -> str:
    return render_to_string(TEMPLATE, _disclosures(**overrides).as_context())


def test_the_surface_shows_all_six_facts_to_the_reader():
    html = _render()

    assert 'data-payment-step="true"' in html
    for marker in ("plan", "price", "due-today", "trial-end", "first-charge",
                   "renewal", "cancellation", "tax"):
        assert f'data-payment-disclosure="{marker}"' in html, f"missing {marker} in the page"

    text = _text(html)
    assert "Academic Cloud" in text
    assert "$0.00" in text
    assert "17 October 2026" in text


def test_the_only_action_is_an_explicit_continue_to_the_provider():
    html = _render()

    form = re.search(r"<form[^>]*action=\"([^\"]+)\"[^>]*>(.*?)</form>", html, re.S)
    assert form, "no continue form"
    assert form.group(1) == "/billing/start-setup/", form.group(1)
    assert 'data-payment-action="continue"' in form.group(0)
    assert "Continue to secure Stripe" in form.group(0)
    # A guarded submit: the UI half of the duplicate-session blocker.
    assert 'data-submit-guard="true"' in form.group(0)


def test_the_page_never_asks_for_card_details():
    """Card data is entered on the provider's page, never here."""
    html = _render()

    for forbidden in ('name="card', 'name="cvc', 'name="number"', 'name="expiry',
                      "autocomplete=\"cc-number\"", "autocomplete=\"cc-csc\""):
        assert forbidden not in html, f"the payment step renders a card field: {forbidden}"

    assert "never sees or stores them" in _text(html), (
        "the page does not say who holds the card details"
    )


def test_a_cancelled_setup_says_nothing_was_charged():
    html = _render(state=SETUP_CANCELLED)

    assert 'data-payment-state="setup_cancelled"' in html
    assert 'data-payment-notice="setup_cancelled"' in html
    text = _text(html).lower()
    assert "not been charged" in text
    assert "nothing was created" in text


def test_a_user_with_a_usable_card_is_not_asked_again():
    html = _render(state=USABLE)

    assert 'data-payment-state="usable"' in html
    assert 'data-payment-action="continue"' not in html, (
        "someone with a usable card must not be pushed at the card page again"
    )
    assert "/accounts/settings/billing/" in html


def test_the_three_steps_are_shown_with_payment_current():
    html = _render()

    assert html.count("payment-steps-item") >= 3
    assert 'aria-current="step"' in html


# ---------------------------------------------------------------------------
# the route (database gate, runs in CI)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestPaymentStepRoute:
    def _user(self, username="payment-probe"):
        from django.contrib.auth import get_user_model

        return get_user_model().objects.create_user(
            username=username, email=f"{username}@example.com", password="TestPass123!"
        )

    def test_the_step_requires_a_signed_in_user(self):
        from django.test import Client

        response = Client().get("/accounts/settings/payment/")
        assert response.status_code in (301, 302)
        assert "/auth/" in response["Location"]

    def test_a_verified_user_without_a_card_sees_the_terms(self):
        from django.test import Client

        client = Client()
        client.force_login(self._user())
        response = client.get("/accounts/settings/payment/")

        assert response.status_code == 200
        assert b'data-payment-step="true"' in response.content
        assert b'data-payment-disclosure="due-today"' in response.content

    def test_the_post_signup_redirect_points_at_this_step(self):
        from apps.infra.public_app.services.billing_provider import (
            card_registration_is_open,
            post_signup_redirect_url,
        )

        user = self._user("payment-redirect")
        target = post_signup_redirect_url(user)

        if card_registration_is_open():
            assert target == "/accounts/settings/payment/"
        else:
            assert target == f"/{user.username}/"


# EOF
