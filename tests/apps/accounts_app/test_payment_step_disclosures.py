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
from pathlib import Path

import pytest
from django.template.loader import render_to_string

from apps.infra.accounts_app.payment_step import (
    PENDING,
    PLAN_UNSET,
    SETUP_CANCELLED,
    SIGNUP_DEFAULT_KEYS,
    USABLE,
    payment_disclosures,
    select_signup_plan,
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


def test_the_plan_unset_render_quotes_no_price_and_offers_no_action():
    """No-DB mirror of the route's plan_unset branch.

    The route tests only run where a database exists (CI), which is exactly how the
    plan_unset/terms interaction first escaped me: locally they errored on the DB and
    CI was the first place they could disagree with the view. Rendering the same two
    states here makes the contract checkable without a database.
    """
    html = _render(state=PLAN_UNSET, plan_label="", monthly_usd=0.0, trial_end=None)

    assert 'data-payment-state="plan_unset"' in html
    assert 'data-payment-disclosure="due-today"' not in html
    assert 'data-payment-action="continue"' not in html


def test_the_determined_plan_render_shows_the_terms_and_the_action():
    html = _render(state=PENDING)

    assert 'data-payment-disclosure="due-today"' in html
    assert 'data-payment-action="continue"' in html


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
# the route itself (no database)
# ---------------------------------------------------------------------------


def test_the_payment_route_resolves_to_the_payment_view():
    """The step must keep winning its own URL.

    "/accounts/settings/payment/" is ambiguous: it ALSO matches project_app's
    "<str:username>/settings/<str:section>/" include with username="accounts", which
    renders a project settings page. Today the accounts include is listed first in
    config/urls.py and accounts_app's own route is declared before its siblings, so
    the step wins — but nothing else pins that, and a reorder would silently turn the
    payment step into somebody's project settings. This asserts it directly.
    """
    from django.urls import resolve

    match = resolve("/accounts/settings/payment/")

    assert match.view_name == "accounts_app:payment_step", (
        f"/accounts/settings/payment/ resolves to {match.view_name!r} instead of the "
        "payment step — check URL include order"
    )
    assert match.func.__name__ == "payment_step"


def test_the_billing_route_still_resolves_to_billing():
    """The sibling route must not be swallowed by the new one."""
    from django.urls import resolve

    assert resolve("/accounts/settings/billing/").view_name == "accounts_app:billing"


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

    def test_a_verified_user_without_a_card_sees_the_terms(self, monkeypatch, settings):
        """Forces registration OPEN so the terms path is asserted even in a CI
        environment with no provider keys — otherwise the keyless fallback renders
        and this test measures the wrong branch (which is exactly how it failed).

        It also has to state WHICH plan, because the terms only exist once the plan is
        determined: with the catalog unmarked and no price configured, the step rightly
        renders the plan_unset state instead. Relying on ambient configuration here is
        what made this test measure a branch nobody ships.
        """
        from django.test import Client

        from apps.infra.accounts_app.views import billing_views

        monkeypatch.setattr(billing_views, "card_registration_is_open", lambda: True)
        settings.STRIPE_PRICE_IDS = {"subscription-general": "price_general"}

        client = Client()
        client.force_login(self._user())
        response = client.get("/accounts/settings/payment/")

        assert response.status_code == 200
        assert b'data-payment-step="true"' in response.content
        assert b'data-payment-disclosure="due-today"' in response.content
        assert b'data-payment-action="continue"' in response.content

    def test_with_no_determined_plan_the_step_quotes_no_price_and_offers_nothing(
        self, monkeypatch, settings
    ):
        """The plan_unset branch, on the real route.

        The catalog lists two subscription rows and marks neither, so with no price
        configured there is no determined plan. The step must say so rather than quote
        a row it picked by file order, and it must not offer an action that would take
        a card for a plan it cannot name.
        """
        from django.test import Client

        from apps.infra.accounts_app.views import billing_views

        monkeypatch.setattr(billing_views, "card_registration_is_open", lambda: True)
        settings.STRIPE_PRICE_IDS = {}

        client = Client()
        client.force_login(self._user("payment-ambiguous"))
        response = client.get("/accounts/settings/payment/")

        assert response.status_code == 200
        assert b'data-payment-step="true"' in response.content
        assert b'data-payment-state="plan_unset"' in response.content
        assert b'data-payment-disclosure="due-today"' not in response.content
        assert b'data-payment-action="continue"' not in response.content

    def test_without_provider_keys_the_step_says_so_instead_of_borrowing_billing(
        self, monkeypatch
    ):
        """The funnel stays one step in every state.

        This view used to render the generic billing page when the provider was
        unconfigured, so the route answered 200 with no step marker at all — the
        state a keyless CI environment is in.
        """
        from django.test import Client

        from apps.infra.accounts_app.views import billing_views

        monkeypatch.setattr(billing_views, "card_registration_is_open", lambda: False)

        client = Client()
        client.force_login(self._user("payment-not-open"))
        response = client.get("/accounts/settings/payment/")

        assert response.status_code == 200
        assert b'data-payment-step="true"' in response.content
        assert b'data-payment-state="not_open"' in response.content
        assert b'data-payment-action="continue"' not in response.content, (
            "a step with no provider must not offer the card action"
        )

    def test_the_post_signup_redirect_is_the_same_in_every_provider_state(self):
        """No fail-open: a keyless environment must not hand the user the app.

        This test used to accept `/<username>/` when card registration was closed —
        exactly the bypass the PR-934 pre-review flagged (verified, no card, straight
        into the app, with copy saying the trial was already running).
        """
        from apps.infra.public_app.services.billing_provider import post_signup_redirect_url

        user = self._user("payment-redirect")
        target = post_signup_redirect_url(user)

        assert target == "/accounts/settings/payment/"
        assert user.username not in target


class TestSignupPlanIsDeterminedNeverArbitrary:
    """`rows[0]` is file order, not a decision — and the wrong price is quoted to a customer.

    Pre-review finding (4) on PR 934. The catalog today holds two subscription rows
    (Academic $19, Standard $39) and no marker, so the step must refuse rather than
    pick one. When a plan IS selected it must be marked or explicitly chosen, and the
    answer must not depend on the order the JSON happens to list rows in.
    """

    ROWS = [
        {"id": "subscription-student", "label": "SciTeX Cloud Academic", "amount": 19},
        {"id": "subscription-general", "label": "SciTeX Cloud Standard", "amount": 39},
    ]

    def test_an_unmarked_catalog_refuses_instead_of_taking_the_first_row(self):
        assert select_signup_plan(self.ROWS) is None

    def test_the_answer_does_not_depend_on_catalog_order(self):
        marked = {"id": "subscription-general", "label": "Standard", "default": True}
        forward = [marked] + [r for r in self.ROWS if r["id"] != marked["id"]]

        assert select_signup_plan(forward) == marked
        assert select_signup_plan(list(reversed(forward))) == marked

    def test_two_marked_rows_refuse_rather_than_tie_break(self):
        a = {**self.ROWS[0], "default": True}
        b = {**self.ROWS[1], "recommended": True}

        assert select_signup_plan([a, b]) is None
        assert select_signup_plan([b, a]) is None

    def test_an_explicit_selection_wins_and_survives_reordering(self):
        chosen = select_signup_plan(self.ROWS, "subscription-student")
        assert chosen is not None
        assert chosen["amount"] == 19

        reordered = select_signup_plan(list(reversed(self.ROWS)), "subscription-student")
        assert reordered == chosen

    def test_an_unknown_explicit_id_refuses_rather_than_falling_back(self):
        """A stale plan id in a signup link must not silently become rows[0]."""
        assert select_signup_plan(self.ROWS, "subscription-legacy") is None

    def test_an_empty_catalog_refuses(self):
        assert select_signup_plan([]) is None
        assert select_signup_plan(None) is None

    def test_falsey_markers_are_not_a_default(self):
        rows = [{**self.ROWS[0], "default": False}, {**self.ROWS[1], "default": None}]

        assert select_signup_plan(rows) is None

    def test_exactly_one_chargeable_plan_is_determined(self):
        """The plan a deployment can actually charge for is a decision, not file order."""
        assert select_signup_plan(self.ROWS, chargeable_ids={"subscription-general"}) == self.ROWS[1]
        assert (
            select_signup_plan(list(reversed(self.ROWS)), chargeable_ids={"subscription-general"})
            == self.ROWS[1]
        )

    def test_two_chargeable_plans_refuse(self):
        """Either could be right, so neither is quoted."""
        both = {"subscription-student", "subscription-general"}

        assert select_signup_plan(self.ROWS, chargeable_ids=both) is None
        assert select_signup_plan(list(reversed(self.ROWS)), chargeable_ids=both) is None

    def test_a_chargeable_id_matching_no_catalog_row_refuses(self):
        assert select_signup_plan(self.ROWS, chargeable_ids={"subscription-legacy"}) is None

    def test_a_catalog_marker_wins_over_the_chargeable_set(self):
        marked = {**self.ROWS[0], "default": True}
        rows = [marked, self.ROWS[1]]

        assert select_signup_plan(rows, chargeable_ids={"subscription-general"}) == marked

    def test_an_explicit_selection_wins_over_the_chargeable_set(self):
        assert (
            select_signup_plan(
                self.ROWS, explicit_id="subscription-student", chargeable_ids={"subscription-general"}
            )
            == self.ROWS[0]
        )

    def test_no_chargeable_information_refuses(self):
        assert select_signup_plan(self.ROWS, chargeable_ids=set()) is None
        assert select_signup_plan(self.ROWS, chargeable_ids=None) is None

    def test_the_live_catalog_is_never_selected_by_file_order(self):
        """Pins the real pricing.json: a selection must be marked, never merely first.

        Also with the live configured prices: whatever it returns must be a row the
        deployment can charge for, and never a row it merely listed first.
        """
        from django.conf import settings

        from apps.infra.public_app.services.billing_provider import subscription_pricing_rows

        rows = subscription_pricing_rows()
        selection = select_signup_plan(rows)

        if selection is not None:
            assert any(selection.get(key) is True for key in SIGNUP_DEFAULT_KEYS), (
                "a plan was selected without an explicit catalog marker — that is file "
                "order pretending to be a decision"
            )

        live = select_signup_plan(rows, chargeable_ids=set(settings.STRIPE_PRICE_IDS))
        if live is not None:
            assert live["id"] in set(settings.STRIPE_PRICE_IDS), (
                "quoted a plan this deployment has no configured price for"
            )
            assert live is not rows[0], "file order decided the plan"


class TestStepCopyStatesTheTruth:
    """The states that are NOT the happy path must not overclaim.

    Pre-review finding (2): with the provider unavailable the step said the trial was
    running and offered the billing page — a claim nothing enforced plus a bypass.
    """

    SOURCE = (
        Path(__file__).resolve().parents[3]
        / "apps/infra/accounts_app/templates/accounts_app/payment_step.html"
    )

    def _branch(self, state: str) -> str:
        src = self.SOURCE.read_text()
        start = src.index(f"state == '{state}'")
        rest = src[start:]
        ends = [i for i in (rest.find("{% elif"), rest.find("{% else"), rest.find("{% endif")) if i != -1]
        return rest[: min(ends)]

    def test_not_open_never_claims_a_running_trial(self):
        branch = self._branch("not_open")

        assert "trial is running" not in branch
        assert "not started" in branch or "has not started" in branch

    def test_not_open_offers_no_app_or_billing_bypass(self):
        assert "{% url" not in self._branch("not_open"), (
            "an unavailable provider must not link users into the app or billing"
        )

    def test_not_open_says_the_retry_is_automatic(self):
        branch = self._branch("not_open").lower()

        assert "retry" in branch or "automatically" in branch
        assert "nothing is due" in branch or "nothing to pay" in branch

    def test_the_plan_unset_branch_quotes_no_price_or_dates(self):
        branch = self._branch("plan_unset")

        for field in ("price_per_month", "due_today", "first_charge_on", "trial_ends_on"):
            assert field not in branch, f"{field} shown for a plan nobody has chosen"


# EOF
