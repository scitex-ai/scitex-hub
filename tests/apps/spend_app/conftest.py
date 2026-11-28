"""Shared fixtures for spend-control tests: real models, hand-rolled fakes."""

from datetime import timedelta
from decimal import Decimal

import pytest
from django.core.cache import cache
from django.utils import timezone


@pytest.fixture(autouse=True)
def _fresh_cache():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def user(django_user_model):
    return django_user_model.objects.create_user(
        username="spender", email="spender@example.org", password="pw-test-only",  # pragma: allowlist secret
    )


@pytest.fixture
def cap(user):
    """Set the holder's monthly cap (USD)."""
    from apps.infra.spend_app.models import SpendControl

    def _set(amount):
        SpendControl.objects.update_or_create(
            user=user, defaults={"monthly_cap_usd": Decimal(str(amount))}
        )

    return _set


@pytest.fixture
def workload(user):
    """A closed allocation of ``cpus`` x ``hours`` this month: one
    ``console_app.WorkloadSession`` row, the Hub's single launch record."""
    from apps.workspace.console_app.models import WorkloadSession

    def _make(*, cpus=2, memory_gb=4, hours=1.0, kind="terminal", open_=False, **kw):
        now = timezone.now()
        start = now - timedelta(hours=hours)
        return WorkloadSession.objects.create(
            user=user,
            workload=kind,
            host="test-host",
            cpus=cpus,
            memory_gb=memory_gb,
            started_at=start,
            stopped_at=None if open_ else now,
            **kw,
        )

    return _make


class FakeStripeResource:
    def __init__(self, name, calls, result):
        self._name = name
        self._calls = calls
        self._result = result

    def create(self, **kwargs):
        self._calls.append((f"{self._name}.create", kwargs))
        return self._result

    def cancel(self, sid, **kwargs):
        self._calls.append((f"{self._name}.cancel", {"id": sid, **kwargs}))
        return self._result


class FakeStripe:
    """Stands in for the ``stripe`` module: records every call it receives."""

    def __init__(self):
        self.calls = []
        self.InvoiceItem = FakeStripeResource(
            "InvoiceItem", self.calls, {"id": "ii_test_1"}
        )
        self.Subscription = FakeStripeResource(
            "Subscription",
            self.calls,
            {"id": "sub_test_1", "latest_invoice": "in_test_1"},
        )


class FakeProvider:
    def __init__(self, secret_key="sk_test_fake"):  # pragma: allowlist secret
        self.secret_key = secret_key
        self.stripe = FakeStripe()

    def _client(self):
        return self.stripe


@pytest.fixture
def fake_provider():
    return FakeProvider()


@pytest.fixture
def subscription(user):
    from apps.infra.public_app.models import PlanSubscription

    return PlanSubscription.objects.create(
        user=user,
        provider_subscription_id="sub_test_1",
        provider_customer_id="cus_test_1",
        pricing_id="subscription-student",
        status="trialing",
        trial_start=timezone.now() - timedelta(days=3),
        trial_end=timezone.now() + timedelta(days=27),
    )
