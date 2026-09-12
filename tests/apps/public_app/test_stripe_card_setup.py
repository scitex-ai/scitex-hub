#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for real card registration + usability validation (Stripe-hosted setup).

Covers the new machinery added on top of the existing commerce scaffold:

- ``stripe_setup.build_stripe_client``  — None while unconfigured (the 503 signal).
- ``stripe_setup.start_card_setup``      — creates/reuses the Stripe customer and
  opens a ``mode="setup"`` session mapped back to the user via
  ``client_reference_id``. Card data never passes through us.
- ``stripe_setup.apply_setup_completed`` — persists ONLY Stripe identifiers +
  safe display metadata, marks the card usable, demotes the prior default.
- ``start_card_setup`` view              — login-gated, POST-only, 503 unconfigured
  (guard layers only — the Stripe SDK call itself is exercised at the service
  layer, matching test_commerce.py's convention of never hitting the live SDK
  from a view test).

No mocks (STX-NM001): real Postgres via pytest-django, and the Stripe client is
a hand-rolled fake collaborator passed as a plain keyword (``stripe_client=``),
the same pattern as ``tests/apps/console_app/services/terminal_broker/
test_terminal_provider.py``. Webhook tests reuse the hand-rolled HMAC scheme.
"""

import hashlib
import hmac
import json
import time

import pytest
from django.urls import reverse

from apps.infra.public_app.services import stripe_setup


# ---------------------------------------------------------------------------
# Hand-rolled Stripe client fake (records calls, returns canned objects)
# ---------------------------------------------------------------------------
class _IdObject:
    def __init__(self, id, **extra):
        self.id = id
        for k, v in extra.items():
            setattr(self, k, v)


class _Checkout:
    def __init__(self, fake):
        self._fake = fake
        # Real SDK shape is stripe.checkout.Session.create(...); the service
        # calls it that way, so expose ourselves under `.Session`.
        self.Session = self

    def create(self, **kwargs):
        self._fake.session_calls.append(kwargs)
        return _IdObject("cs_test_fake", url="https://checkout.stripe.com/c/pay/cs_test_fake")


class _Customer:
    def __init__(self, fake):
        self._fake = fake

    def create(self, **kwargs):
        self._fake.customer_calls.append(kwargs)
        return _IdObject(f"cus_{len(self._fake.customer_calls)}")


class _PaymentMethod:
    def __init__(self, fake):
        self._fake = fake

    def retrieve(self, pm_id):
        self._fake.retrieve_calls.append(pm_id)
        card = _IdObject("", brand="visa", last4="4242", exp_month=12, exp_year=2030)
        return _IdObject(pm_id, card=card)


class FakeStripeClient:
    """Records Stripe API calls and returns canned objects (no network)."""

    def __init__(self):
        self.customer_calls = []
        self.session_calls = []
        self.retrieve_calls = []
        self.checkout = _Checkout(self)
        self.Customer = _Customer(self)
        self.PaymentMethod = _PaymentMethod(self)


def _stripe_signature(payload: bytes, secret: str, timestamp: int = None) -> str:
    """Hand-rolled Stripe-Signature header (documented v1 scheme)."""
    ts = int(time.time()) if timestamp is None else timestamp
    signed_payload = f"{ts}.".encode() + payload
    mac = hmac.new(secret.encode(), signed_payload, hashlib.sha256).hexdigest()
    return f"t={ts},v1={mac}"


def _post_webhook(client, payload: bytes, signature: str):
    return client.post(
        reverse("public_app:stripe_webhook"),
        data=payload,
        content_type="application/json",
        HTTP_STRIPE_SIGNATURE=signature,
    )


@pytest.fixture
def logged_in_client(client, django_user_model):
    django_user_model.objects.create_user(
        username="card-user", password="test-password-123", email="card@example.com"
    )
    client.login(username="card-user", password="test-password-123")
    return client


# ---------------------------------------------------------------------------
# build_stripe_client
# ---------------------------------------------------------------------------
def test_build_stripe_client_returns_none_when_unconfigured():
    assert stripe_setup.build_stripe_client("") is None
    assert stripe_setup.build_stripe_client(None) is None


def test_build_stripe_client_returns_callable_client_when_keyed():
    client = stripe_setup.build_stripe_client("sk_test_live_key_here")
    # The real SDK module is returned and usable (imported, not mocked).
    assert client is not None
    assert hasattr(client, "checkout") and hasattr(client, "Customer")


# ---------------------------------------------------------------------------
# start_card_setup (service) — real DB, fake Stripe client
# ---------------------------------------------------------------------------
@pytest.mark.django_db
class TestStartCardSetup:
    def test_creates_customer_when_user_has_none(self, django_user_model):
        user = django_user_model.objects.create_user(username="u1", password="x")
        fake = FakeStripeClient()
        stripe_setup.start_card_setup(
            user, stripe_client=fake, success_url="https://s", cancel_url="https://c"
        )
        assert len(fake.customer_calls) == 1
        assert fake.session_calls[0]["mode"] == "setup"
        assert fake.session_calls[0]["client_reference_id"] == str(user.pk)
        # The session references the customer we just created (cus_1).
        assert fake.session_calls[0]["customer"] == "cus_1"

    def test_session_mode_is_setup_not_payment(self, django_user_model):
        user = django_user_model.objects.create_user(username="u2", password="x")
        fake = FakeStripeClient()
        stripe_setup.start_card_setup(
            user, stripe_client=fake, success_url="https://s", cancel_url="https://c"
        )
        assert fake.session_calls[0]["mode"] == "setup"

    def test_reuses_existing_customer_without_new_create(self, django_user_model):
        from apps.infra.public_app.models import PaymentMethod

        user = django_user_model.objects.create_user(username="u3", password="x")
        PaymentMethod.objects.create(
            user=user,
            stripe_payment_method_id="pm_existing",
            stripe_customer_id="cus_existing",
        )
        fake = FakeStripeClient()
        stripe_setup.start_card_setup(
            user, stripe_client=fake, success_url="https://s", cancel_url="https://c"
        )
        # No new customer — reuses the stored one.
        assert fake.customer_calls == []
        assert fake.session_calls[0]["customer"] == "cus_existing"


# ---------------------------------------------------------------------------
# apply_setup_completed (service) — real DB, fake Stripe client
# ---------------------------------------------------------------------------
def _completed_setup_event(user_pk, pm_id="pm_1", cus_id="cus_1", mode="setup"):
    return {
        "id": f"evt_{pm_id}",
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "mode": mode,
                "payment_method": pm_id,
                "customer": cus_id,
                "client_reference_id": str(user_pk),
            }
        },
    }


@pytest.mark.django_db
class TestApplySetupCompleted:
    def test_persists_validated_card_with_display_metadata(self, django_user_model):
        from apps.infra.public_app.models import PaymentMethod

        user = django_user_model.objects.create_user(username="p1", password="x")
        fake = FakeStripeClient()
        row = stripe_setup.apply_setup_completed(
            _completed_setup_event(user.pk), stripe_client=fake
        )
        assert row is not None
        assert row.stripe_payment_method_id == "pm_1"
        assert row.stripe_customer_id == "cus_1"
        assert row.is_usable is True
        assert row.is_default is True
        # Safe display metadata fetched from Stripe and stored.
        assert row.brand == "visa"
        assert row.last4 == "4242"
        assert row.exp_month == 12
        assert row.exp_year == 2030
        assert fake.retrieve_calls == ["pm_1"]

    def test_stores_only_ids_and_safe_metadata_not_pan(self, django_user_model):
        from apps.infra.public_app.models import PaymentMethod

        user = django_user_model.objects.create_user(username="p2", password="x")
        stripe_setup.apply_setup_completed(
            _completed_setup_event(user.pk), stripe_client=FakeStripeClient()
        )
        row = PaymentMethod.objects.get(user=user)
        fields = {f.name for f in row._meta.get_fields()}
        assert "card_number" not in fields and "cvc" not in fields
        assert "stripe_payment_method_id" in fields

    def test_ignores_non_setup_session(self, django_user_model):
        user = django_user_model.objects.create_user(username="p3", password="x")
        row = stripe_setup.apply_setup_completed(
            _completed_setup_event(user.pk, mode="payment"), stripe_client=FakeStripeClient()
        )
        assert row is None

    def test_ignores_unknown_user(self, django_user_model):
        django_user_model.objects.create_user(username="p4", password="x")
        row = stripe_setup.apply_setup_completed(
            _completed_setup_event(999999), stripe_client=FakeStripeClient()
        )
        assert row is None

    def test_demotes_previous_default_card(self, django_user_model):
        from apps.infra.public_app.models import PaymentMethod

        user = django_user_model.objects.create_user(username="p5", password="x")
        stripe_setup.apply_setup_completed(
            _completed_setup_event(user.pk, pm_id="pm_old", cus_id="cus_old"),
            stripe_client=FakeStripeClient(),
        )
        stripe_setup.apply_setup_completed(
            _completed_setup_event(user.pk, pm_id="pm_new", cus_id="cus_new"),
            stripe_client=FakeStripeClient(),
        )
        old = PaymentMethod.objects.get(stripe_payment_method_id="pm_old")
        new = PaymentMethod.objects.get(stripe_payment_method_id="pm_new")
        assert new.is_default is True
        assert old.is_default is False

    def test_marks_usable_even_without_stripe_client(self, django_user_model):
        from apps.infra.public_app.models import PaymentMethod

        user = django_user_model.objects.create_user(username="p6", password="x")
        row = stripe_setup.apply_setup_completed(
            _completed_setup_event(user.pk), stripe_client=None
        )
        assert row is not None
        assert row.is_usable is True
        # No client -> no display metadata fetched, but the card is recorded.
        assert row.brand == ""


# ---------------------------------------------------------------------------
# start_card_setup (view) — guard layers only (STX-NM001: no live SDK call)
# ---------------------------------------------------------------------------
@pytest.mark.django_db
class TestStartCardSetupView:
    def test_anonymous_is_redirected_to_login(self, client):
        resp = client.post(reverse("public_app:billing_start_setup"))
        assert resp.status_code in (302, 303)
        assert "login" in resp.url

    def test_get_returns_405(self, logged_in_client):
        assert logged_in_client.get(reverse("public_app:billing_start_setup")).status_code == 405

    def test_post_without_stripe_key_returns_503(self, logged_in_client, settings):
        settings.STRIPE_SECRET_KEY = ""
        resp = logged_in_client.post(reverse("public_app:billing_start_setup"))
        assert resp.status_code == 503
        assert "SCITEX_HUB_STRIPE_SECRET_KEY" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# Webhook end-to-end: signed setup completion persists a usable card
# ---------------------------------------------------------------------------
@pytest.mark.django_db
class TestWebhookPersistsValidatedCard:
    def test_signed_setup_completed_marks_card_usable(self, client, settings, django_user_model):
        from apps.infra.public_app.models import PaymentMethod

        settings.STRIPE_WEBHOOK_SECRET = "whsec_test_for_card_setup"
        settings.STRIPE_SECRET_KEY = ""  # no client -> core row + is_usable only
        user = django_user_model.objects.create_user(
            username="w1", password="x", email="w1@example.com"
        )
        event = _completed_setup_event(user.pk, pm_id="pm_webhook", cus_id="cus_webhook")
        payload = json.dumps(event).encode()
        sig = _stripe_signature(payload, "whsec_test_for_card_setup")
        resp = _post_webhook(client, payload, sig)
        assert resp.status_code == 200
        row = PaymentMethod.objects.filter(stripe_payment_method_id="pm_webhook").first()
        assert row is not None
        assert row.user_id == user.pk
        assert row.is_usable is True

    def test_bad_signature_does_not_persist_card(self, client, settings, django_user_model):
        from apps.infra.public_app.models import PaymentMethod

        settings.STRIPE_WEBHOOK_SECRET = "whsec_test_for_card_setup"
        settings.STRIPE_SECRET_KEY = ""
        user = django_user_model.objects.create_user(
            username="w2", password="x", email="w2@example.com"
        )
        payload = json.dumps(_completed_setup_event(user.pk, pm_id="pm_evil")).encode()
        sig = _stripe_signature(payload, "whsec_wrong_secret")
        resp = _post_webhook(client, payload, sig)
        assert resp.status_code == 400
        assert not PaymentMethod.objects.filter(
            stripe_payment_method_id="pm_evil"
        ).exists()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
