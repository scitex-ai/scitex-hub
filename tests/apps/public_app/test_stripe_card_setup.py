#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Card registration through Stripe-hosted Checkout in setup mode.

Real Postgres via pytest-django; the Stripe client is a hand-rolled fake passed
as ``stripe_client=`` (no mocks). Event payloads follow Stripe's real shape: a
completed setup-mode Checkout Session names its ``setup_intent``, and the card
is read back from that SetupIntent.
"""

import hashlib
import hmac
import json
import time

import pytest
from django.urls import reverse

from apps.infra.public_app.models import BillingEvent, PaymentMethod
from apps.infra.public_app.services import stripe_setup

WEBHOOK_SECRET = "whsec_test_for_card_setup"


class _StripeObject:
    def __init__(self, id, **fields):
        self.id = id
        for name, value in fields.items():
            setattr(self, name, value)


class _CheckoutSessions:
    def __init__(self, fake):
        self._fake = fake
        self.Session = self

    def create(self, **kwargs):
        self._fake.session_calls.append(kwargs)
        return _StripeObject("cs_test_fake", url="https://checkout.stripe.com/c/pay/cs_test_fake")


class _Customers:
    def __init__(self, fake):
        self._fake = fake

    def create(self, **kwargs):
        self._fake.customer_calls.append(kwargs)
        return _StripeObject(f"cus_{len(self._fake.customer_calls)}")


class _SetupIntents:
    def retrieve(self, setup_intent_id):
        return _StripeObject(setup_intent_id, payment_method=f"pm_of_{setup_intent_id}")


class _PaymentMethods:
    def retrieve(self, payment_method_id):
        card = _StripeObject("", brand="visa", last4="4242", exp_month=12, exp_year=2034)
        return _StripeObject(payment_method_id, card=card)


class _Subscriptions:
    def __init__(self, fake):
        self._fake = fake

    def create(self, **kwargs):
        self._fake.subscription_calls.append(kwargs)
        return _StripeObject(
            f"sub_{len(self._fake.subscription_calls)}",
            customer=kwargs.get("customer"),
            status="trialing",
            trial_start=kwargs.get("trial_end"),
            trial_end=kwargs.get("trial_end"),
            metadata=kwargs.get("metadata") or {},
            cancel_at_period_end=False,
        )


class FakeStripeClient:
    """Records Stripe API calls and returns canned objects (no network)."""

    def __init__(self):
        self.customer_calls = []
        self.session_calls = []
        self.subscription_calls = []
        self.checkout = _CheckoutSessions(self)
        self.Customer = _Customers(self)
        self.SetupIntent = _SetupIntents()
        self.PaymentMethod = _PaymentMethods()
        self.Subscription = _Subscriptions(self)


def _completed_setup_event(
    user_pk, setup_intent_id="seti_1", customer_id="cus_1", mode="setup", pricing_id=""
):
    return {
        "id": f"evt_{setup_intent_id}",
        "type": "checkout.session.completed",
        "livemode": False,
        "data": {
            "object": {
                "id": f"cs_{setup_intent_id}",
                "mode": mode,
                "setup_intent": setup_intent_id,
                "customer": customer_id,
                "client_reference_id": str(user_pk),
                "metadata": {"pricing_id": pricing_id} if pricing_id else {},
            }
        },
    }


def _signed_webhook_post(client, event, secret=WEBHOOK_SECRET):
    payload = json.dumps(event).encode()
    timestamp = int(time.time())
    digest = hmac.new(secret.encode(), f"{timestamp}.".encode() + payload, hashlib.sha256).hexdigest()
    return client.post(
        reverse("public_app:stripe_webhook"),
        data=payload,
        content_type="application/json",
        HTTP_STRIPE_SIGNATURE=f"t={timestamp},v1={digest}",
    )


def _start_setup(user, fake, pricing_id="subscription-general"):
    """Open a hosted setup session for an allowlisted plan.

    ``pricing_id`` is required by the service since PR #934 review blocker 5:
    the plan is bound to the session's metadata so the webhook activates the plan
    the user was shown, instead of being re-decided later.
    """
    stripe_setup.start_card_setup(
        user,
        pricing_id=pricing_id,
        stripe_client=fake,
        success_url="https://s",
        cancel_url="https://c",
    )
    return fake.session_calls[0]


@pytest.fixture
def logged_in_client(client, django_user_model):
    django_user_model.objects.create_user(
        username="card-user", password="test-password-123", email="card@example.com"
    )
    client.login(username="card-user", password="test-password-123")
    return client


def test_build_stripe_client_returns_none_without_a_key():
    # Arrange
    missing_key = ""
    # Act
    client = stripe_setup.build_stripe_client(missing_key)
    # Assert
    assert client is None


def test_build_stripe_client_returns_the_sdk_with_a_key():
    # Arrange
    key = "sk_test_placeholder"
    # Act
    client = stripe_setup.build_stripe_client(key)
    # Assert
    assert hasattr(client, "checkout")


@pytest.mark.django_db
class TestStartCardSetup:
    def test_creates_a_customer_when_the_user_has_none(self, django_user_model):
        # Arrange
        user = django_user_model.objects.create_user(username="u1", password="x")
        fake = FakeStripeClient()
        # Act
        session_kwargs = _start_setup(user, fake)
        # Assert
        assert session_kwargs["customer"] == "cus_1"

    def test_opens_the_session_in_setup_mode(self, django_user_model):
        # Arrange
        user = django_user_model.objects.create_user(username="u2", password="x")
        fake = FakeStripeClient()
        # Act
        session_kwargs = _start_setup(user, fake)
        # Assert
        assert session_kwargs["mode"] == "setup"

    def test_passes_the_currency_stripe_requires_in_setup_mode(self, django_user_model):
        # Arrange
        user = django_user_model.objects.create_user(username="u3", password="x")
        fake = FakeStripeClient()
        # Act
        session_kwargs = _start_setup(user, fake)
        # Assert
        assert session_kwargs["currency"] == "usd"

    def test_maps_the_session_back_to_the_user(self, django_user_model):
        # Arrange
        user = django_user_model.objects.create_user(username="u4", password="x")
        fake = FakeStripeClient()
        # Act
        session_kwargs = _start_setup(user, fake)
        # Assert
        assert session_kwargs["client_reference_id"] == str(user.pk)

    def test_reuses_the_stored_customer(self, django_user_model):
        # Arrange
        user = django_user_model.objects.create_user(username="u5", password="x")
        PaymentMethod.objects.create(
            user=user, stripe_payment_method_id="pm_existing", stripe_customer_id="cus_existing"
        )
        fake = FakeStripeClient()
        # Act
        session_kwargs = _start_setup(user, fake)
        # Assert
        assert session_kwargs["customer"] == "cus_existing"


@pytest.mark.django_db
class TestApplySetupCompleted:
    def test_stores_the_payment_method_named_by_the_setup_intent(self, django_user_model):
        # Arrange
        user = django_user_model.objects.create_user(username="p1", password="x")
        # Act
        row = stripe_setup.apply_setup_completed(
            _completed_setup_event(user.pk, setup_intent_id="seti_abc"), stripe_client=FakeStripeClient()
        )
        # Assert
        assert row.stripe_payment_method_id == "pm_of_seti_abc"

    def test_marks_the_card_usable(self, django_user_model):
        # Arrange
        user = django_user_model.objects.create_user(username="p2", password="x")
        # Act
        row = stripe_setup.apply_setup_completed(
            _completed_setup_event(user.pk), stripe_client=FakeStripeClient()
        )
        # Assert
        assert row.is_usable is True

    def test_stores_brand_and_last4_for_display(self, django_user_model):
        # Arrange
        user = django_user_model.objects.create_user(username="p3", password="x")
        # Act
        row = stripe_setup.apply_setup_completed(
            _completed_setup_event(user.pk), stripe_client=FakeStripeClient()
        )
        # Assert
        assert (row.brand, row.last4) == ("visa", "4242")

    def test_model_has_no_field_for_the_card_number(self, django_user_model):
        # Arrange
        user = django_user_model.objects.create_user(username="p4", password="x")
        row = stripe_setup.apply_setup_completed(
            _completed_setup_event(user.pk), stripe_client=FakeStripeClient()
        )
        # Act
        field_names = {field.name for field in row._meta.get_fields()}
        # Assert
        assert field_names.isdisjoint({"card_number", "number", "cvc"})

    def test_ignores_a_payment_mode_session(self, django_user_model):
        # Arrange
        user = django_user_model.objects.create_user(username="p5", password="x")
        # Act
        row = stripe_setup.apply_setup_completed(
            _completed_setup_event(user.pk, mode="payment"), stripe_client=FakeStripeClient()
        )
        # Assert
        assert row is None

    def test_ignores_an_unknown_user(self, django_user_model):
        # Arrange
        unknown_user_pk = 999999
        # Act
        row = stripe_setup.apply_setup_completed(
            _completed_setup_event(unknown_user_pk), stripe_client=FakeStripeClient()
        )
        # Assert
        assert row is None

    def test_stores_nothing_without_a_stripe_client(self, django_user_model):
        # Arrange
        user = django_user_model.objects.create_user(username="p6", password="x")
        # Act
        row = stripe_setup.apply_setup_completed(_completed_setup_event(user.pk), stripe_client=None)
        # Assert
        assert row is None

    def test_demotes_the_previous_default_card(self, django_user_model):
        # Arrange
        user = django_user_model.objects.create_user(username="p7", password="x")
        stripe_setup.apply_setup_completed(
            _completed_setup_event(user.pk, setup_intent_id="seti_old"), stripe_client=FakeStripeClient()
        )
        # Act
        stripe_setup.apply_setup_completed(
            _completed_setup_event(user.pk, setup_intent_id="seti_new"), stripe_client=FakeStripeClient()
        )
        # Assert
        assert PaymentMethod.objects.get(stripe_payment_method_id="pm_of_seti_old").is_default is False


@pytest.mark.django_db
class TestStartCardSetupView:
    def test_anonymous_post_redirects_to_login(self, client):
        # Arrange
        url = reverse("public_app:billing_start_setup")
        # Act
        response = client.post(url)
        # Assert
        assert "login" in response.url

    def test_get_is_not_allowed(self, logged_in_client):
        # Arrange
        url = reverse("public_app:billing_start_setup")
        # Act
        response = logged_in_client.get(url)
        # Assert
        assert response.status_code == 405

    def test_post_without_a_stripe_key_returns_503(self, logged_in_client, settings):
        # Arrange
        settings.STRIPE_SECRET_KEY = ""
        settings.STRIPE_PRICE_IDS = {"subscription-general": "price_test_general"}
        # The endpoint is scoped to funnel accounts (PR #934 review, blocker 1),
        # so the probe has to BE one before the provider check is reached.
        from django.contrib.auth import get_user_model

        from apps.infra.auth_app.onboarding import begin_social_signup

        begin_social_signup(get_user_model().objects.get(username="card-user"), "email")
        # Act
        response = logged_in_client.post(
            reverse("public_app:billing_start_setup"), {"plan": "subscription-general"}
        )
        # Assert
        assert response.status_code == 503

    def test_an_established_account_is_sent_to_billing_instead(self, client, django_user_model):
        """Outside the funnel this endpoint is not the way to add a card (blocker 1)."""
        # Arrange
        django_user_model.objects.create_user(
            username="established", password="test-password-123"
        )
        client.login(username="established", password="test-password-123")
        # Act
        response = client.post(
            reverse("public_app:billing_start_setup"), {"plan": "subscription-general"}
        )
        # Assert
        assert response.status_code in (301, 302)
        assert response["Location"] == reverse("accounts_app:billing")


@pytest.mark.django_db
class TestSetupIsIdempotent:
    """Two clicks before the webhook must not make two customers or two sessions.

    PR #934 review, blocker 4. Measured before this change: two calls created two
    Stripe customers, two sessions, different customer ids and no idempotency keys.
    """

    def _user(self, django_user_model, username):
        return django_user_model.objects.create_user(username=username, password="x")

    def test_two_post_requests_reuse_one_customer_and_one_session(self, django_user_model):
        # Arrange
        user = self._user(django_user_model, "dup-1")
        fake = FakeStripeClient()
        # Act
        first = stripe_setup.start_card_setup(
            user, pricing_id="subscription-general", stripe_client=fake,
            success_url="https://s", cancel_url="https://c",
        )
        second = stripe_setup.start_card_setup(
            user, pricing_id="subscription-general", stripe_client=fake,
            success_url="https://s", cancel_url="https://c",
        )
        # Assert
        assert len(fake.customer_calls) == 1, "a second Stripe customer was created"
        assert len(fake.session_calls) == 1, "a second Stripe session was created"
        assert first.url == second.url
        assert second.reused is True

    def test_both_provider_calls_carry_deterministic_idempotency_keys(self, django_user_model):
        # Arrange
        user = self._user(django_user_model, "dup-2")
        fake = FakeStripeClient()
        # Act
        stripe_setup.start_card_setup(
            user, pricing_id="subscription-general", stripe_client=fake,
            success_url="https://s", cancel_url="https://c",
        )
        # Assert
        assert fake.customer_calls[0]["idempotency_key"] == stripe_setup.customer_idempotency_key(user)
        assert fake.session_calls[0]["idempotency_key"] == stripe_setup.session_idempotency_key(
            user, "subscription-general", 0
        )

    def test_a_cancelled_attempt_opens_a_new_session_but_keeps_the_customer(self, django_user_model):
        # Arrange
        user = self._user(django_user_model, "dup-3")
        fake = FakeStripeClient()
        stripe_setup.start_card_setup(
            user, pricing_id="subscription-general", stripe_client=fake,
            success_url="https://s", cancel_url="https://c",
        )
        # Act
        stripe_setup.mark_setup_cancelled(user)
        second = stripe_setup.start_card_setup(
            user, pricing_id="subscription-general", stripe_client=fake,
            success_url="https://s", cancel_url="https://c",
        )
        # Assert
        assert len(fake.customer_calls) == 1, "the retry minted a second customer"
        assert len(fake.session_calls) == 2, "the retry did not open a fresh session"
        assert second.reused is False
        assert second.attempt == 1

    def test_changing_plan_does_not_reuse_the_other_plans_session(self, django_user_model):
        # Arrange
        user = self._user(django_user_model, "dup-4")
        fake = FakeStripeClient()
        stripe_setup.start_card_setup(
            user, pricing_id="subscription-general", stripe_client=fake,
            success_url="https://s", cancel_url="https://c",
        )
        # Act
        stripe_setup.start_card_setup(
            user, pricing_id="subscription-student", stripe_client=fake,
            success_url="https://s", cancel_url="https://c",
        )
        # Assert
        assert len(fake.session_calls) == 2
        assert fake.session_calls[1]["metadata"]["pricing_id"] == "subscription-student"


@pytest.mark.django_db
class TestWebhook:
    """The webhook applies each event ONCE (PR #934 review, blockers 5 and 6)."""

    @pytest.fixture(autouse=True)
    def _test_mode_provider(self, settings, monkeypatch):
        """A signed test-mode webhook with a fake Stripe client.

        The mode must be a RECOGNISABLE test key: an event whose livemode cannot
        be compared against the configured key is refused rather than applied.
        """
        settings.STRIPE_WEBHOOK_SECRET = WEBHOOK_SECRET
        settings.STRIPE_SECRET_KEY = "sk_test_card_setup_fixture"
        settings.STRIPE_PRICE_IDS = {"subscription-general": "price_test_general"}
        monkeypatch.setattr(stripe_setup, "build_stripe_client", lambda key: FakeStripeClient())
        return settings

    def test_signed_setup_completion_is_acknowledged(self, client, django_user_model):
        # Arrange
        user = django_user_model.objects.create_user(username="w1", password="x")
        # Act
        response = _signed_webhook_post(client, _completed_setup_event(user.pk, setup_intent_id="seti_w1"))
        # Assert
        assert response.status_code == 200
        assert response.json()["processed"] is True

    def test_signed_setup_completion_is_recorded(self, client, django_user_model):
        # Arrange
        user = django_user_model.objects.create_user(username="w2", password="x")
        # Act
        _signed_webhook_post(client, _completed_setup_event(user.pk, setup_intent_id="seti_w2"))
        # Assert
        assert BillingEvent.objects.filter(event_id="evt_seti_w2").exists()

    def test_a_replayed_event_is_not_applied_twice(self, client, django_user_model):
        """The defect: ``get_or_create`` deduplicated the row, the handler ran anyway."""
        # Arrange
        user = django_user_model.objects.create_user(username="w4", password="x")
        event = _completed_setup_event(user.pk, setup_intent_id="seti_replay")
        # Act
        first = _signed_webhook_post(client, event)
        second = _signed_webhook_post(client, event)
        # Assert
        assert first.json()["processed"] is True
        assert second.status_code == 200
        assert second.json()["processed"] is False
        assert BillingEvent.objects.filter(event_id="evt_seti_replay").count() == 1

    def test_a_live_event_on_a_test_key_is_refused(self, client, django_user_model):
        """Test/live consistency (blocker 5): the mode must agree with the key."""
        # Arrange
        user = django_user_model.objects.create_user(username="w5", password="x")
        event = _completed_setup_event(user.pk, setup_intent_id="seti_live")
        event["livemode"] = True
        # Act
        response = _signed_webhook_post(client, event)
        # Assert
        assert response.status_code == 400
        assert response.json()["error"] == "mode_mismatch"
        row = BillingEvent.objects.get(event_id="evt_seti_live")
        assert row.is_processed is False

    def test_bad_signature_is_rejected(self, client, django_user_model):
        # Arrange
        user = django_user_model.objects.create_user(username="w3", password="x")
        # Act
        response = _signed_webhook_post(
            client, _completed_setup_event(user.pk, setup_intent_id="seti_evil"), secret="whsec_wrong"
        )
        # Assert
        assert response.status_code == 400
