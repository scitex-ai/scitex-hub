#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The paid journey is ready for Stripe TEST mode and degrades without keys.

No mocks (STX-NM001): real Postgres via pytest-django, settings via the
pytest-django ``settings`` fixture, and a hand-rolled Stripe fake passed to the
provider as ``stripe_client=`` (the pattern of test_stripe_card_setup.py).
"""

import hashlib
import hmac
import json
import time
from datetime import timedelta

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from apps.infra.public_app.management.commands.stripe_bootstrap_test import (
    bootstrap_catalog,
)
from apps.infra.public_app.services.billing_provider import post_signup_redirect_url
from apps.infra.public_app.services.stripe_provider import StripeBillingProvider

FAKE_TEST_KEY = "sk_test_fake-for-unit-tests"
FAKE_LIVE_KEY = "sk_live_fake-for-unit-tests"
FAKE_WEBHOOK_SECRET = "whsec_fake-for-unit-tests"


class _Record:
    def __init__(self, **fields):
        self.__dict__.update(fields)


class _ListResult:
    def __init__(self, data):
        self.data = data


class _FakeResource:
    """One Stripe resource: records create/modify calls, serves list lookups."""

    def __init__(self, prefix, match_field):
        self.prefix = prefix
        self.match_field = match_field
        self.created = []
        self.modified = []

    def create(self, **fields):
        fields.setdefault("id", f"{self.prefix}_{len(self.created) + 1}")
        record = _Record(**fields)
        self.created.append(record)
        return record

    def list(self, **filters):
        wanted = filters.get("ids") or filters.get("lookup_keys") or []
        return _ListResult([r for r in self.created if getattr(r, self.match_field, None) in wanted])

    def modify(self, record_id, **fields):
        self.modified.append((record_id, fields))
        return {"id": record_id, "status": "active", **fields}


class FakeStripeClient:
    def __init__(self):
        self.Product = _FakeResource("prod", "id")
        self.Price = _FakeResource("price", "lookup_key")
        self.Subscription = _FakeResource("sub", "id")


def _signature(payload: bytes, secret: str) -> str:
    timestamp = int(time.time())
    digest = hmac.new(secret.encode(), f"{timestamp}.".encode() + payload, hashlib.sha256).hexdigest()
    return f"t={timestamp},v1={digest}"


@pytest.fixture
def user_with_card(django_user_model):
    from apps.infra.public_app.models import PaymentMethod

    user = django_user_model.objects.create_user(username="trial-user", password="x", email="t@example.com")
    PaymentMethod.objects.create(
        user=user,
        stripe_customer_id="cus_trial",
        stripe_payment_method_id="pm_trial",
        is_usable=True,
        is_default=True,
    )
    return user


def _provider(stripe_client):
    return StripeBillingProvider(
        secret_key=FAKE_TEST_KEY,
        webhook_secret=FAKE_WEBHOOK_SECRET,
        price_ids={"subscription-general": "price_general"},
        stripe_client=stripe_client,
    )


# ---------------------------------------------------------------------------
# No keys: signup and billing degrade gracefully
# ---------------------------------------------------------------------------
@pytest.mark.django_db
def test_signup_page_without_stripe_keys_returns_200(client, settings):
    # Arrange
    settings.STRIPE_SECRET_KEY = ""
    # Act
    response = client.get(reverse("auth_app:signup"))
    # Assert
    assert response.status_code == 200


@pytest.mark.django_db
def test_verified_signup_without_stripe_keys_still_lands_on_the_payment_step(
    settings, django_user_model
):
    """The card-required redirect must not fail open when the provider is unavailable.

    This asserted `url == "/nokeys/"` until the pre-review on PR 934 called it out:
    with no provider keys, a verified-but-cardless signup was sent straight into the
    app and the step's old copy told them their trial was already running. The gate
    is "no usable webhook-confirmed card -> no app", so the destination is the SAME
    in every provider state and the step explains the wait. A regression here is
    silent — nothing errors, users just bypass the funnel.

    PR #934 review, blocker 7: the destination now comes from the durable
    onboarding authority, so the probe has to be an account the OTP handler has
    actually verified — which is exactly the state `mark_verified` writes.
    """
    # Arrange
    from apps.infra.auth_app.onboarding import begin_social_signup, mark_verified

    settings.STRIPE_SECRET_KEY = ""
    user = django_user_model.objects.create_user(username="nokeys", password="x")
    mark_verified(user, source="email")
    # Act
    url = post_signup_redirect_url(user)
    # Assert
    assert url == reverse("accounts_app:payment_step")
    assert "nokeys" not in url, "the app-route fallback is exactly the bypass we removed"

    # An account the authority does NOT put in the funnel is not enrolled by a
    # redirect either; it keeps the ordinary post-login destination.
    assert post_signup_redirect_url(user) == reverse("accounts_app:payment_step")
    assert begin_social_signup(user, "email") is not None

    outsider = django_user_model.objects.create_user(username="not-in-funnel", password="x")
    assert post_signup_redirect_url(outsider) == "/"


@pytest.mark.django_db
def test_verified_signup_with_stripe_key_goes_to_add_card(settings, django_user_model):
    # Arrange
    from apps.infra.auth_app.onboarding import mark_verified

    settings.STRIPE_SECRET_KEY = FAKE_TEST_KEY
    user = django_user_model.objects.create_user(username="withkeys", password="x")
    mark_verified(user, source="email")
    # Act
    url = post_signup_redirect_url(user)
    # Assert
    # The dedicated payment step, not the billing settings page: it states the trial
    # terms before the provider's page and carries the single "Continue to secure
    # Stripe" action (card hub-signup-email-stripe-funnel-20260917). Billing remains
    # one click away, and this is the ONLY redirect policy for a verified signup —
    # post_signup_redirect_url delegates to the onboarding authority, which the OTP
    # handler and the social adapter both consult, so there is no second rule to
    # keep in step.
    assert url == reverse("accounts_app:payment_step")


@pytest.mark.django_db
def test_billing_page_without_stripe_keys_says_card_registration_opens_soon(client, settings, django_user_model):
    # Arrange
    settings.STRIPE_SECRET_KEY = ""
    user = django_user_model.objects.create_user(username="billing-nokeys", password="x")
    client.force_login(user)
    # Act
    response = client.get(reverse("accounts_app:billing"), HTTP_ACCEPT_LANGUAGE="en")
    # Assert
    assert "Card registration opens soon" in response.content.decode()


@pytest.mark.django_db
def test_billing_page_with_test_key_and_card_offers_configured_plan(client, settings, user_with_card):
    # Arrange
    settings.STRIPE_SECRET_KEY = FAKE_TEST_KEY
    settings.STRIPE_PRICE_IDS = {"subscription-general": "price_general"}
    client.force_login(user_with_card)
    # Act
    response = client.get(reverse("accounts_app:billing"), HTTP_ACCEPT_LANGUAGE="en")
    # Assert
    assert 'value="subscription-general"' in response.content.decode()


# ---------------------------------------------------------------------------
# Bootstrap command
# ---------------------------------------------------------------------------
def test_bootstrap_command_refuses_live_key_without_live_flag(settings):
    # Arrange
    settings.STRIPE_SECRET_KEY = FAKE_LIVE_KEY
    # Act
    try:
        call_command("stripe_bootstrap_test")
        refusal = ""
    except CommandError as exc:
        refusal = str(exc)
    # Assert
    assert "LIVE key" in refusal


def test_bootstrap_catalog_second_run_creates_no_new_price():
    # Arrange
    stripe_client = FakeStripeClient()
    bootstrap_catalog(stripe_client)
    prices_after_first_run = len(stripe_client.Price.created)
    # Act
    bootstrap_catalog(stripe_client)
    # Assert
    assert len(stripe_client.Price.created) == prices_after_first_run


def test_bootstrap_catalog_creates_usd_prices_for_a_jpy_default_account():
    # Arrange
    stripe_client = FakeStripeClient()
    # Act
    bootstrap_catalog(stripe_client)
    # Assert
    assert {price.currency for price in stripe_client.Price.created} == {"usd"}


def test_bootstrap_catalog_prints_price_env_lines_only():
    # Arrange
    stripe_client = FakeStripeClient()
    # Act
    env_lines = bootstrap_catalog(stripe_client)
    # Assert
    assert env_lines == [
        "SCITEX_HUB_STRIPE_PRICE_SUBSCRIPTION_STUDENT=price_1",
        "SCITEX_HUB_STRIPE_PRICE_SUBSCRIPTION_GENERAL=price_2",
    ]


# ---------------------------------------------------------------------------
# Webhook
# ---------------------------------------------------------------------------
@pytest.mark.django_db
def test_webhook_rejects_bad_signature(client, settings):
    # Arrange
    settings.STRIPE_WEBHOOK_SECRET = FAKE_WEBHOOK_SECRET
    payload = json.dumps({"id": "evt_bad", "type": "invoice.paid"}).encode()
    # Act
    response = client.post(
        reverse("public_app:stripe_webhook"),
        data=payload,
        content_type="application/json",
        HTTP_STRIPE_SIGNATURE=_signature(payload, "whsec_wrong"),
    )
    # Assert
    assert response.status_code == 400


@pytest.mark.django_db
def test_webhook_accepts_signed_anonymous_post_with_csrf_enforced(settings):
    # Arrange
    settings.STRIPE_WEBHOOK_SECRET = FAKE_WEBHOOK_SECRET
    # PR #934 review, blocker 5: the event's livemode is compared against the
    # configured key, so a webhook test needs a RECOGNISABLE key of the matching
    # mode and an event that says which mode it came from.
    settings.STRIPE_SECRET_KEY = FAKE_TEST_KEY
    csrf_enforcing_client = Client(enforce_csrf_checks=True)
    payload = json.dumps(
        {"id": "evt_anonymous", "type": "invoice.paid", "livemode": False}
    ).encode()
    # Act
    response = csrf_enforcing_client.post(
        reverse("public_app:stripe_webhook"),
        data=payload,
        content_type="application/json",
        HTTP_STRIPE_SIGNATURE=_signature(payload, FAKE_WEBHOOK_SECRET),
    )
    # Assert
    assert response.status_code == 200


@pytest.mark.django_db
def test_signed_subscription_deleted_webhook_marks_plan_canceled(client, settings, user_with_card):
    # Arrange
    from apps.infra.public_app.models import PlanSubscription

    settings.STRIPE_WEBHOOK_SECRET = FAKE_WEBHOOK_SECRET
    settings.STRIPE_SECRET_KEY = FAKE_TEST_KEY
    PlanSubscription.objects.create(user=user_with_card, provider_subscription_id="sub_live", status="active")
    event = {
        "id": "evt_sub_deleted",
        "type": "customer.subscription.deleted",
        "livemode": False,
        "data": {"object": {"id": "sub_live", "customer": "cus_trial", "status": "canceled"}},
    }
    payload = json.dumps(event).encode()
    # Act
    client.post(
        reverse("public_app:stripe_webhook"),
        data=payload,
        content_type="application/json",
        HTTP_STRIPE_SIGNATURE=_signature(payload, FAKE_WEBHOOK_SECRET),
    )
    # Assert
    assert PlanSubscription.objects.get(provider_subscription_id="sub_live").status == "canceled"


# ---------------------------------------------------------------------------
# Subscription: the trial window is the provider's, and conversion bills from it
# ---------------------------------------------------------------------------
@pytest.mark.django_db
def test_choosing_a_plan_while_a_provider_trial_runs_is_refused(user_with_card):
    """A second subscription while one is live is a refusal, not a silent double bill.

    PR #934 review, blocker 2. This test used to assert that choosing a plan
    during a trial backdated the first period to ``date_joined`` — the signup
    FORM's date, for a trial that did not exist at the provider. The trial now
    exists at the provider (``activate_trial``), it is a current subscription,
    and this guard refuses before anything is created.
    """
    # Arrange
    from apps.infra.public_app.models import PlanSubscription
    from apps.infra.public_app.services.billing_provider import BillingOperationRefused

    stripe_client = FakeStripeClient()
    PlanSubscription.objects.create(
        user=user_with_card,
        provider_subscription_id="sub_trialing",
        status="trialing",
        trial_start=timezone.now(),
        trial_end=timezone.now() + timedelta(days=30),
    )
    # Act
    refusal = ""
    try:
        _provider(stripe_client).start_subscription(user_with_card, pricing_id="subscription-general")
    except BillingOperationRefused as exc:
        refusal = str(exc)
    # Assert
    assert "already have an active plan" in refusal
    assert stripe_client.Subscription.created == []


@pytest.mark.django_db
def test_choosing_a_plan_without_a_trial_never_backdates_to_the_signup_date(user_with_card):
    """No current subscription -> the new one starts now.

    The 特商法 rule ("a converted trial bills from the trial's start") is
    satisfied by the trial itself: it is created with the provider's own
    ``trial_end`` at activation, so Stripe bills the period from that start.
    Backdating here would bill a period that began before the account had a card.
    """
    # Arrange
    user_with_card.date_joined = timezone.now() - timedelta(days=45)
    user_with_card.save(update_fields=["date_joined"])
    stripe_client = FakeStripeClient()
    # Act
    _provider(stripe_client).start_subscription(user_with_card, pricing_id="subscription-general")
    # Assert
    assert stripe_client.Subscription.created
    assert not hasattr(stripe_client.Subscription.created[0], "backdate_start_date")


@pytest.mark.django_db
def test_cancel_subscription_stops_renewal_at_period_end(user_with_card):
    # Arrange
    stripe_client = FakeStripeClient()
    provider = _provider(stripe_client)
    subscription = provider.start_subscription(user_with_card, pricing_id="subscription-general")
    # Act
    canceled = provider.cancel_subscription(subscription)
    # Assert
    assert canceled.cancel_at_period_end is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
