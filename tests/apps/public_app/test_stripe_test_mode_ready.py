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
def test_verified_signup_without_stripe_keys_lands_on_profile(settings, django_user_model):
    # Arrange
    settings.STRIPE_SECRET_KEY = ""
    user = django_user_model.objects.create_user(username="nokeys", password="x")
    # Act
    url = post_signup_redirect_url(user)
    # Assert
    assert url == "/nokeys/"


@pytest.mark.django_db
def test_verified_signup_with_stripe_key_goes_to_add_card(settings, django_user_model):
    # Arrange
    settings.STRIPE_SECRET_KEY = FAKE_TEST_KEY
    user = django_user_model.objects.create_user(username="withkeys", password="x")
    # Act
    url = post_signup_redirect_url(user)
    # Assert
    assert url == reverse("accounts_app:billing") + "?welcome=1"


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
    csrf_enforcing_client = Client(enforce_csrf_checks=True)
    payload = json.dumps({"id": "evt_anonymous", "type": "invoice.paid"}).encode()
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
    settings.STRIPE_SECRET_KEY = ""
    PlanSubscription.objects.create(user=user_with_card, provider_subscription_id="sub_live", status="active")
    event = {
        "id": "evt_sub_deleted",
        "type": "customer.subscription.deleted",
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
# Subscription: continuing during the trial bills from the registration date
# ---------------------------------------------------------------------------
@pytest.mark.django_db
def test_subscription_during_trial_is_backdated_to_registration(user_with_card):
    # Arrange
    stripe_client = FakeStripeClient()
    # Act
    _provider(stripe_client).start_subscription(user_with_card, pricing_id="subscription-general")
    # Assert
    assert stripe_client.Subscription.created[0].backdate_start_date == int(user_with_card.date_joined.timestamp())


@pytest.mark.django_db
def test_subscription_after_trial_starts_today_without_backdating(user_with_card):
    # Arrange
    user_with_card.date_joined = timezone.now() - timedelta(days=45)
    user_with_card.save(update_fields=["date_joined"])
    stripe_client = FakeStripeClient()
    # Act
    _provider(stripe_client).start_subscription(user_with_card, pricing_id="subscription-general")
    # Assert
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
