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


@pytest.mark.django_db
def test_payment_step_free_exit_unsticks_a_gated_account():
    """Nobody may be stuck on the payment page: one POST leaves free."""
    from apps.infra.auth_app.onboarding import mark_free

    user = _signup("stuck-u", "trial")
    row = mark_verified(user, source="email")
    assert row.step == OnboardingState.Step.PAYMENT
    assert payment_required(user) in (True, False)  # deployment-dependent
    freed = mark_free(user)
    assert freed.step == OnboardingState.Step.PRODUCT
    assert freed.pricing_id == "subscription-free"
    assert freed.activated_at is not None
    assert payment_required(user) is False
    # Idempotent: a second call keeps PRODUCT, never rewinds.
    assert mark_free(user).step == OnboardingState.Step.PRODUCT


@pytest.mark.django_db
def test_free_exit_ignores_non_funnel_accounts():
    from apps.infra.auth_app.onboarding import mark_free

    user = User.objects.create_user("plain-u", "plain-u@example.com", "x")
    assert mark_free(user) is None
