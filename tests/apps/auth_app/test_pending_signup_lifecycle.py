#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Pending-signup / OTP lifecycle P0.

Observed live evidence this file fixes and guards:
  * SignupForm.clean_username / clean_email rejected existing User rows BEFORE
    signup() could reach its inactive-account resume/expiry branch.
  * cleanup_unverified_users existed ONLY as an unscheduled manual command.
  * a live ACTIVE account carried a later EXPIRED EmailVerification with
    is_verified=False.

Disposable users only — nothing here reads, writes or reuses any real account
or any observed OTP.

THE NON-DB TESTS ARE DELIBERATELY NOT MARKED django_db. A module-level
pytestmark would force a database on all of them, and this container has no
postgres — so the source-level, rate-limit and non-enumeration guards would
all show up as ERRORS and prove nothing. They read source and the cache, and
they run here.
"""

from __future__ import annotations

from datetime import timedelta

import pytest
from django.contrib.auth.models import User
from django.core.cache import cache
from django.urls import reverse
from django.utils import timezone

from apps.infra.auth_app import pending_signup as ps

SIGNUP_FIELDS = {
    "username": "pending_probe",
    "email": "pending_probe@example.com",
    "password": "Gx7-quiet-harbour-42",
    # password2, NOT confirm_password: SignupForm.base_fields has no such key,
    # so posting it silently left the form INVALID and the 302 assertions below
    # could never be reached (PR #775 re-review). Guarded by
    # test_no_test_posts_a_field_the_form_ignores.
    "password2": "Gx7-quiet-harbour-42",
    "agree_terms": "on",
}


def _pending(email="pending_probe@example.com", username="pending_probe", age=None):
    """A disposable PENDING signup (inactive, unverified)."""
    user = User.objects.create_user(
        username=username, email=email, password="Gx7-quiet-harbour-42", is_active=False
    )
    if age is not None:
        # date_joined is auto_now_add: must be moved with an UPDATE.
        User.objects.filter(pk=user.pk).update(date_joined=timezone.now() - age)
        user.refresh_from_db()
    return user


def _active(email="pending_probe@example.com", username="pending_probe"):
    return User.objects.create_user(
        username=username, email=email, password="Gx7-quiet-harbour-42", is_active=True
    )


# ---------------------------------------------------------------------------
# No database required: source-level and cache-level guards.
# ---------------------------------------------------------------------------


def test_the_unreachable_dead_end_advice_is_gone_from_the_signup_view():
    # Arrange — the old text told users to "wait 1 hour for the account to
    # expire", advice that pointed at an expiry nothing performed. Kept as a
    # source-level guard because the failure mode was ADVICE, not an exception.
    from apps.infra.auth_app.views import authentication

    with open(authentication.__file__, encoding="utf-8") as handle:
        text = handle.read()

    # Act / Assert — the guard matches the USER-FACING sentence, not the bare
    # phrase: the comment left in place deliberately quotes the old advice, and
    # a guard that trips on its own explanatory comment would be a false alarm.
    assert (
        "Please check your inbox or wait 1 hour for the account to expire" not in text
    )


def test_the_view_decides_the_lifecycle_rather_than_the_form():
    # Arrange / Act — the request path must own the four-way decision.
    from apps.infra.auth_app.views import authentication

    with open(authentication.__file__, encoding="utf-8") as handle:
        text = handle.read()

    # Assert
    assert "classify_pending_signup" in text


def test_the_form_no_longer_rejects_existing_rows():
    # Arrange — the defect itself: a uniqueness error in the form made the
    # view's resume/expiry branch unreachable.
    from apps.infra.auth_app import forms

    with open(forms.__file__, encoding="utf-8") as handle:
        text = handle.read()

    # Assert — the RAISES are gone from the field validators. Matching the bare
    # message text would trip on the comment that documents the removal, so the
    # guard matches the raising statement itself.
    assert 'raise forms.ValidationError("This username is already taken.")' not in text
    assert (
        'raise forms.ValidationError("An account with this email already exists.")'
        not in text
    )


def test_the_cleanup_command_shares_the_window_rather_than_hard_coding_it():
    # Arrange — two copies of a lifecycle number is how they drift.
    from apps.infra.auth_app.management.commands import cleanup_unverified_users

    with open(cleanup_unverified_users.__file__, encoding="utf-8") as handle:
        text = handle.read()

    # Act / Assert
    assert "PENDING_SIGNUP_WINDOW" in text
    assert ps.PENDING_SIGNUP_WINDOW == timedelta(hours=1)


def test_the_resend_budget_blocks_after_the_limit():
    # Arrange
    cache.clear()
    email = "rate_limit_probe@example.com"

    # Act
    for _ in range(ps.RESENDS_ALLOWED_PER_WINDOW):
        assert ps.resend_allowed(email) is True
        ps.record_resend(email)

    # Assert — the next one is refused, and the refusal is a real limit
    assert ps.resend_allowed(email) is False


def test_the_resend_budget_is_per_address_not_global():
    # Arrange — a global budget would be a denial of service on every user.
    cache.clear()
    for _ in range(ps.RESENDS_ALLOWED_PER_WINDOW + 1):
        ps.record_resend("one@example.com")

    # Act / Assert
    assert ps.resend_allowed("one@example.com") is False
    assert ps.resend_allowed("two@example.com") is True


def test_clearing_the_budget_restores_it():
    # Arrange — used after a successful verification.
    cache.clear()
    for _ in range(ps.RESENDS_ALLOWED_PER_WINDOW + 1):
        ps.record_resend("three@example.com")
    assert ps.resend_allowed("three@example.com") is False

    # Act
    ps.clear_resend_budget("three@example.com")

    # Assert
    assert ps.resend_allowed("three@example.com") is True


def test_the_signup_response_never_confirms_or_denies_that_an_account_exists():
    # Arrange
    from apps.infra.auth_app.views import authentication

    message = authentication._SIGNUP_RESPONSE_MESSAGE

    # Assert — conditional, truthful in all five outcomes, and no claim that
    # anything was created.
    assert "If that address can be used" in message
    assert "Account created" not in message
    assert "already exists" not in message


def test_the_signup_response_does_not_echo_the_submitted_address():
    # Arrange — echoing the address is a weak oracle when combined with send
    # behaviour, and it is unnecessary in a conditional message.
    from apps.infra.auth_app.views import authentication

    # Act / Assert
    assert "@" not in authentication._SIGNUP_RESPONSE_MESSAGE


def test_the_budget_message_is_truthful_about_what_happened():
    # Arrange / Act
    message = ps.resend_budget_message()

    # Assert — it states a fact (we already sent several), not a promise.
    assert "already sent several" in message


# ---------------------------------------------------------------------------
# Classification — the four answers. These need a database (CI runs them).
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_an_unknown_address_is_a_fresh_signup():
    assert (
        ps.classify_pending_signup("nobody@example.com", "nobody")[0]
        is ps.SignupCollision.NONE
    )


@pytest.mark.django_db
def test_a_fresh_inactive_row_is_pending_and_live():
    # Arrange
    user = _pending()

    # Act
    collision, found = ps.classify_pending_signup(
        "pending_probe@example.com", "pending_probe"
    )

    # Assert
    assert collision is ps.SignupCollision.PENDING_LIVE
    assert found is not None and found.pk == user.pk


@pytest.mark.django_db
def test_an_old_inactive_row_is_pending_and_resumable_not_a_dead_end():
    # Arrange — this is the state the old form made unreachable.
    user = _pending(age=ps.PENDING_SIGNUP_WINDOW + timedelta(minutes=1))

    # Act
    collision, found = ps.classify_pending_signup(
        "pending_probe@example.com", "pending_probe"
    )

    # Assert
    assert collision is ps.SignupCollision.PENDING_EXPIRED
    assert found is not None and found.pk == user.pk


@pytest.mark.django_db
def test_an_active_row_is_active_and_never_pending():
    # Arrange
    _active()

    # Act
    collision, _found = ps.classify_pending_signup(
        "pending_probe@example.com", "pending_probe"
    )

    # Assert
    assert collision is ps.SignupCollision.ACTIVE


@pytest.mark.django_db
def test_email_belonging_to_one_account_and_username_to_another_is_split():
    # Arrange — resolving this by guessing would hijack a username or strand
    # an address, so it is reported instead.
    _active(email="first@example.com", username="first_user")
    _active(email="second@example.com", username="second_user")

    # Act
    collision, found = ps.classify_pending_signup("first@example.com", "second_user")

    # Assert
    assert collision is ps.SignupCollision.SPLIT
    assert found is None


# ---------------------------------------------------------------------------
# The end-to-end behaviours the invariants promise.
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_an_expired_pending_signup_can_be_resumed_by_signing_up_again(client):
    # Arrange — an abandoned, expired signup.
    stale = _pending(age=ps.PENDING_SIGNUP_WINDOW + timedelta(hours=2))
    stale_pk = stale.pk

    # Act
    response = client.post(reverse("auth_app:signup"), SIGNUP_FIELDS)

    # Assert — the signup is accepted (not "already exists"), the stale row is
    # replaced, and a NEW pending row exists.
    assert response.status_code == 302
    assert not User.objects.filter(pk=stale_pk).exists()
    assert User.objects.get(username="pending_probe").is_active is False


@pytest.mark.django_db
def test_a_live_pending_signup_is_resent_not_duplicated(client):
    # Arrange
    original = _pending()
    original_pk = original.pk

    # Act
    response = client.post(reverse("auth_app:signup"), SIGNUP_FIELDS)

    # Assert — same row, still inactive, no second account.
    assert response.status_code == 302
    assert User.objects.filter(email="pending_probe@example.com").count() == 1
    assert User.objects.filter(pk=original_pk).exists()


@pytest.mark.django_db
def test_an_active_account_is_neither_recreated_nor_deleted_by_a_signup(client):
    # Arrange — the invariant that matters most: a real account is untouched.
    existing = _active()
    existing_pk = existing.pk

    # Act
    response = client.post(reverse("auth_app:signup"), SIGNUP_FIELDS)

    # Assert
    assert response.status_code == 302
    remaining = User.objects.filter(email="pending_probe@example.com")
    assert remaining.count() == 1
    assert remaining.first().pk == existing_pk  # type: ignore[union-attr]
    assert remaining.first().is_active is True  # type: ignore[union-attr]


@pytest.mark.django_db
def test_the_resend_budget_is_enforced_through_the_signup_view(client):
    # Arrange — exhaust the budget for this address.
    _pending()
    cache.clear()
    for _ in range(ps.RESENDS_ALLOWED_PER_WINDOW):
        ps.record_resend("pending_probe@example.com")

    # Act
    response = client.post(reverse("auth_app:signup"), SIGNUP_FIELDS)

    # Assert — rate limited, and the account was not duplicated.
    assert response.status_code == 200
    assert User.objects.filter(email="pending_probe@example.com").count() == 1
