"""Free vs trial funnel: plan stored at signup, honored at verification."""

import pytest
from django.contrib.auth.models import User

from apps.infra.auth_app.models import OnboardingState, PendingSignup
from apps.infra.auth_app.onboarding import mark_verified, payment_required


def _signup(username, plan):
    user = User.objects.create_user(username, f"{username}@example.com", "x")
    user.is_active = False
    user.save()
    PendingSignup.objects.create(user=user, email=user.email, plan=plan)
    return user


@pytest.mark.django_db
def test_free_verification_completes_funnel():
    user = _signup("free-u", "free")
    row = mark_verified(user, source="email")
    assert row.step == OnboardingState.Step.PRODUCT
    assert row.pricing_id == "subscription-free"
    assert not PendingSignup.objects.filter(user=user).exists()
    user.is_active = True
    user.save()
    assert payment_required(user) is False


@pytest.mark.django_db
def test_trial_verification_still_owes_payment():
    user = _signup("trial-u", "trial")
    row = mark_verified(user, source="email")
    assert row.step == OnboardingState.Step.PAYMENT
    assert not PendingSignup.objects.filter(user=user).exists()


@pytest.mark.django_db
def test_legacy_marker_without_plan_stays_trial():
    user = User.objects.create_user("legacy-u", "legacy-u@example.com", "x")
    user.is_active = False
    user.save()
    PendingSignup(user=user, email=user.email).save()  # default plan=trial
    row = mark_verified(user, source="email")
    assert row.step == OnboardingState.Step.PAYMENT
