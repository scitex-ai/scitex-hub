#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Inline card setup (Stripe.js Elements) — SetupIntent mint + confirm.

Real Postgres via pytest-django; the Stripe client is a hand-rolled fake
(no network). The browser confirms the intent with Stripe.js; the server
only ever sees the SetupIntent id and verifies it (succeeded + customer and
plan bound to this user) before persisting anything.
"""

import pytest

from apps.infra.public_app.models import BillingSetupSession, PaymentMethod
from apps.infra.public_app.services import stripe_setup


class _StripeObject:
    def __init__(self, id, **fields):
        self.id = id
        for name, value in fields.items():
            setattr(self, name, value)


class _InlineSetupIntents:
    def __init__(self, fake):
        self._fake = fake

    def create(self, **kwargs):
        self._fake.intent_calls.append(kwargs)
        n = len(self._fake.intent_calls)
        return _StripeObject(
            f"seti_{n}",
            client_secret=f"seti_{n}_secret",
            status="requires_payment_method",
        )

    def retrieve(self, setup_intent_id):
        return self._fake.intents.get(
            setup_intent_id,
            _StripeObject(setup_intent_id, status="requires_payment_method"),
        )


class _InlineCustomers:
    def __init__(self, fake):
        self._fake = fake

    def create(self, **kwargs):
        self._fake.customer_calls.append(kwargs)
        return _StripeObject(f"cus_{len(self._fake.customer_calls)}")


class _InlinePaymentMethods:
    def retrieve(self, payment_method_id):
        card = _StripeObject("", brand="visa", last4="4242", exp_month=12, exp_year=2034)
        return _StripeObject(payment_method_id, card=card)


class FakeInlineStripeClient:
    def __init__(self):
        self.customer_calls = []
        self.intent_calls = []
        self.intents = {}
        self.Customer = _InlineCustomers(self)
        self.SetupIntent = _InlineSetupIntents(self)
        self.PaymentMethod = _InlinePaymentMethods()

    def succeed(self, setup_intent_id, user, customer_id="cus_1", pricing_id="subscription-general"):
        self.intents[setup_intent_id] = _StripeObject(
            setup_intent_id,
            status="succeeded",
            customer=customer_id,
            payment_method="pm_of_%s" % setup_intent_id,
            metadata={"user_pk": str(user.pk), "pricing_id": pricing_id},
        )


@pytest.mark.django_db
class TestCreateCardSetupIntent:
    def test_mints_an_intent_and_stores_it_on_the_row(self, django_user_model):
        user = django_user_model.objects.create_user(username="inline1", password="x")
        fake = FakeInlineStripeClient()

        setup_intent_id, client_secret = stripe_setup.create_card_setup_intent(
            user, pricing_id="subscription-general", stripe_client=fake
        )

        assert setup_intent_id == "seti_1"
        assert client_secret == "seti_1_secret"
        row = BillingSetupSession.objects.get(user=user)
        assert row.session_id == "seti_1"
        assert row.status == BillingSetupSession.Status.OPEN
        assert fake.intent_calls[0]["customer"] == "cus_1"
        assert fake.intent_calls[0]["metadata"]["user_pk"] == str(user.pk)

    def test_a_second_call_reuses_the_customer_but_mints_a_new_intent(self, django_user_model):
        user = django_user_model.objects.create_user(username="inline2", password="x")
        fake = FakeInlineStripeClient()

        stripe_setup.create_card_setup_intent(
            user, pricing_id="subscription-general", stripe_client=fake
        )
        second_id, _ = stripe_setup.create_card_setup_intent(
            user, pricing_id="subscription-general", stripe_client=fake
        )

        assert second_id == "seti_2"
        assert len(fake.customer_calls) == 1


@pytest.mark.django_db
class TestConfirmCardSetup:
    def test_succeeded_bound_intent_persists_a_usable_default_card(self, django_user_model):
        user = django_user_model.objects.create_user(username="inline3", password="x")
        fake = FakeInlineStripeClient()
        setup_intent_id, _ = stripe_setup.create_card_setup_intent(
            user, pricing_id="subscription-general", stripe_client=fake
        )
        fake.succeed(setup_intent_id, user, customer_id="cus_1")

        card = stripe_setup.confirm_card_setup(
            user, setup_intent_id=setup_intent_id, stripe_client=fake
        )

        assert card is not None
        assert card.is_usable and card.is_default
        assert card.last4 == "4242"
        row = BillingSetupSession.objects.get(user=user)
        assert row.status == BillingSetupSession.Status.COMPLETED

    def test_unconfirmed_intent_persists_nothing(self, django_user_model):
        user = django_user_model.objects.create_user(username="inline4", password="x")
        fake = FakeInlineStripeClient()
        setup_intent_id, _ = stripe_setup.create_card_setup_intent(
            user, pricing_id="subscription-general", stripe_client=fake
        )

        assert stripe_setup.confirm_card_setup(
            user, setup_intent_id=setup_intent_id, stripe_client=fake
        ) is None
        assert PaymentMethod.objects.filter(user=user).count() == 0

    def test_intent_for_another_user_persists_nothing(self, django_user_model):
        user = django_user_model.objects.create_user(username="inline5", password="x")
        other = django_user_model.objects.create_user(username="inline6", password="x")
        fake = FakeInlineStripeClient()
        setup_intent_id, _ = stripe_setup.create_card_setup_intent(
            user, pricing_id="subscription-general", stripe_client=fake
        )
        fake.succeed(setup_intent_id, other, customer_id="cus_1")

        assert stripe_setup.confirm_card_setup(
            user, setup_intent_id=setup_intent_id, stripe_client=fake
        ) is None
        assert PaymentMethod.objects.filter(user=user).count() == 0
