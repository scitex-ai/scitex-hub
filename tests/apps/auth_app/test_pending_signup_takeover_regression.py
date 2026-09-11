#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Account-takeover regression suite for the pending-signup resume path.

SECURITY HOLD on PR #775. Independent review found that
``classify_pending_signup`` treated a ONE-SIDED collision as the pending user:

    POST attacker_email + victim_pending_username
      -> email_user=None, username_user=victim
      -> (PENDING_LIVE, victim)            # the victim's row, handed to a stranger
      -> EmailVerification(user=victim, email=attacker_email)
      -> the OTP is MAILED TO THE ATTACKER and VERIFIES THE VICTIM

Past the window the same input reached the delete-and-recreate branch, letting
the attacker delete the victim's pending row and take the username with their
own credentials.

The existing tests covered the EXACT pair and the crossed TWO-ROW case; the
one-sided mismatches — the actual attack — were untested. This file tests them,
and tests the negative space too: not just "the right branch was taken" but
"NOTHING was mutated, minted, sent or logged in".

The positive control at the bottom matters as much as the attacks: a fix that
simply refuses every resume would pass every attack test while destroying the
feature, so the exact pair must still resume.
"""

from __future__ import annotations

import logging
from datetime import timedelta

import pytest
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone

from apps.infra.auth_app import pending_signup as ps
from apps.infra.auth_app.models import EmailVerification
from apps.infra.auth_app.views import authentication

pytestmark = pytest.mark.django_db

ATTACKER_EMAIL = "attacker@evil.example"
ATTACKER_PASSWORD = "Gx7-quiet-harbour-42"


def _attacker_fields(victim_username: str) -> dict:
    """The attack payload: the attacker's own email, the victim's username."""
    return {
        "username": victim_username,
        "email": ATTACKER_EMAIL,
        "password": ATTACKER_PASSWORD,
        # password2, NOT confirm_password — see the note in
        # test_pending_signup_lifecycle.py. A key the form ignores makes the
        # form invalid, so the request never reaches the branch under test.
        "password2": ATTACKER_PASSWORD,
        "agree_terms": "on",
    }


def _victim(username="victim_pending", email="victim@example.com", age=None):
    """A disposable PENDING row owned by the victim."""
    user = User.objects.create_user(
        username=username,
        email=email,
        password="victim-original-password-1",
        is_active=False,
    )
    if age is not None:
        User.objects.filter(pk=user.pk).update(date_joined=timezone.now() - age)
        user.refresh_from_db()
    return user


def _snapshot(user: User) -> dict:
    """Everything an attacker would want to change about a row."""
    return {
        "pk": user.pk,
        "username": user.username,
        "email": user.email,
        "is_active": user.is_active,
        "password": user.password,  # the HASH: asserts no password rotation
        "date_joined": user.date_joined,
        "last_login": user.last_login,
    }


def _assert_no_new_verification(before_ids: set[int]) -> None:
    """No OTP may be minted at all — not for the victim, not for anyone."""
    after = set(EmailVerification.objects.values_list("id", flat=True))
    assert after == before_ids, (
        "a verification code was minted during a collision attempt: "
        f"{sorted(after - before_ids)}"
    )


def _assert_not_authenticated(client) -> None:
    assert "_auth_user_id" not in client.session, (
        "the collision attempt logged someone in"
    )


# ---------------------------------------------------------------------------
# THE REPORTED ATTACK: username-only collision, live window.
# ---------------------------------------------------------------------------


def test_username_only_collision_never_mails_the_victim_a_code_the_attacker_can_read(
    client,
):
    # Arrange — the victim's live pending row, and the attacker who knows only
    # the victim's USERNAME.
    victim = _victim(username="victim_pending", email="victim@example.com")
    before = _snapshot(victim)
    otps_before = set(EmailVerification.objects.values_list("id", flat=True))

    # Act — attacker email + victim username.
    response = client.post(
        reverse("auth_app:signup"), _attacker_fields("victim_pending")
    )

    # Assert — the response is the generic one, and NO code exists that could
    # verify the victim.
    assert response.status_code == 302
    _assert_no_new_verification(otps_before)
    victim.refresh_from_db()
    assert _snapshot(victim) == before


def test_username_only_collision_does_not_create_an_account_for_the_attacker(client):
    # Arrange
    _victim()
    users_before = set(User.objects.values_list("id", flat=True))

    # Act
    client.post(reverse("auth_app:signup"), _attacker_fields("victim_pending"))

    # Assert — no account appears, in either direction.
    assert set(User.objects.values_list("id", flat=True)) == users_before
    assert not User.objects.filter(email=ATTACKER_EMAIL).exists()
    _assert_not_authenticated(client)


def test_username_only_collision_classifies_as_one_sided_with_no_user():
    # Arrange
    victim = _victim()

    # Act
    collision, found = ps.classify_pending_signup(ATTACKER_EMAIL, "victim_pending")

    # Assert — the classifier itself refuses to name a row it has not proven.
    assert collision is ps.SignupCollision.ONE_SIDED
    assert found is None
    assert victim.is_active is False  # sanity: the row really was pending


# ---------------------------------------------------------------------------
# THE MIRROR ATTACK: email-only collision.
# ---------------------------------------------------------------------------


def test_email_only_collision_does_not_send_an_otp_to_the_victim_on_a_stranger_s_request(
    client,
):
    # Arrange — the attacker knows only the victim's EMAIL and asks under a
    # username nobody holds.
    victim = _victim(username="victim_pending", email="victim@example.com")
    before = _snapshot(victim)
    otps_before = set(EmailVerification.objects.values_list("id", flat=True))

    # Act
    fields = _attacker_fields("attacker_chosen_name")
    fields["email"] = "victim@example.com"
    response = client.post(reverse("auth_app:signup"), fields)

    # Assert
    assert response.status_code == 302
    _assert_no_new_verification(otps_before)
    victim.refresh_from_db()
    assert _snapshot(victim) == before


def test_email_only_collision_classifies_as_one_sided_with_no_user():
    # Arrange
    _victim()

    # Act
    collision, found = ps.classify_pending_signup(
        "victim@example.com", "nobody_holds_this"
    )

    # Assert
    assert collision is ps.SignupCollision.ONE_SIDED
    assert found is None


# ---------------------------------------------------------------------------
# THE CROSSED CASE: two different rows, one per submitted value.
# ---------------------------------------------------------------------------


def test_crossed_two_user_collision_touches_neither_row(client):
    # Arrange — A holds the email, B holds the username. Neither submitted pair
    # proves ownership of either row.
    row_a = _victim(username="row_a", email="a@example.com")
    row_b = _victim(username="row_b", email="b@example.com")
    before_a, before_b = _snapshot(row_a), _snapshot(row_b)
    otps_before = set(EmailVerification.objects.values_list("id", flat=True))

    # Act — A's email with B's username.
    fields = _attacker_fields("row_b")
    fields["email"] = "a@example.com"
    response = client.post(reverse("auth_app:signup"), fields)

    # Assert
    assert response.status_code == 302
    _assert_no_new_verification(otps_before)
    row_a.refresh_from_db()
    row_b.refresh_from_db()
    assert _snapshot(row_a) == before_a
    assert _snapshot(row_b) == before_b
    _assert_not_authenticated(client)


def test_crossed_two_user_collision_is_still_reported_as_split():
    # Arrange
    _victim(username="row_a", email="a@example.com")
    _victim(username="row_b", email="b@example.com")

    # Act
    collision, found = ps.classify_pending_signup("a@example.com", "row_b")

    # Assert
    assert collision is ps.SignupCollision.SPLIT
    assert found is None


# ---------------------------------------------------------------------------
# THE EXPIRED CASE, where the old code DELETED the victim's row.
# ---------------------------------------------------------------------------


def test_expired_username_only_collision_does_not_delete_the_victim(client):
    # Arrange — the victim's row is past the window, so the old code fell into
    # the delete-and-recreate branch.
    victim = _victim(username="victim_pending", email="victim@example.com")
    User.objects.filter(pk=victim.pk).update(
        date_joined=timezone.now() - ps.PENDING_SIGNUP_WINDOW - timedelta(hours=3)
    )
    victim.refresh_from_db()
    victim_pk = victim.pk
    before = _snapshot(victim)

    # Act
    client.post(reverse("auth_app:signup"), _attacker_fields("victim_pending"))

    # Assert — the row SURVIVES and is untouched.
    assert User.objects.filter(pk=victim_pk).exists(), "the victim's row was deleted"
    victim.refresh_from_db()
    assert _snapshot(victim) == before


def test_the_attacker_cannot_take_an_expired_victims_username(client):
    # Arrange
    victim = _victim(username="victim_pending", email="victim@example.com")
    User.objects.filter(pk=victim.pk).update(
        date_joined=timezone.now() - ps.PENDING_SIGNUP_WINDOW - timedelta(hours=3)
    )

    # Act
    client.post(reverse("auth_app:signup"), _attacker_fields("victim_pending"))

    # Assert — the username is still the victim's, and the attacker got nothing.
    holder = User.objects.filter(username__iexact="victim_pending")
    assert holder.count() == 1
    assert holder.first().email == "victim@example.com"
    assert not User.objects.filter(email=ATTACKER_EMAIL).exists()


def test_an_expired_one_sided_collision_mints_no_code_either(client):
    # Arrange
    victim = _victim()
    User.objects.filter(pk=victim.pk).update(
        date_joined=timezone.now() - ps.PENDING_SIGNUP_WINDOW - timedelta(hours=3)
    )
    otps_before = set(EmailVerification.objects.values_list("id", flat=True))

    # Act
    client.post(reverse("auth_app:signup"), _attacker_fields("victim_pending"))

    # Assert
    _assert_no_new_verification(otps_before)


# ---------------------------------------------------------------------------
# THE SECOND LINE OF DEFENCE: the helper itself.
# ---------------------------------------------------------------------------


def test_the_send_helper_refuses_a_row_whose_own_email_is_not_the_target():
    # Arrange — call the helper the way the buggy caller would have: a victim
    # row, an attacker's address.
    victim = _victim()
    otps_before = set(EmailVerification.objects.values_list("id", flat=True))

    # Act — no request needed; the guard must fire on the arguments alone.
    sent = authentication._send_pending_signup_code(
        None, victim, ATTACKER_EMAIL, logging.getLogger("test.takeover")
    )

    # Assert
    assert sent is False
    _assert_no_new_verification(otps_before)


# ---------------------------------------------------------------------------
# POSITIVE CONTROL — the fix must not have destroyed the feature.
# ---------------------------------------------------------------------------


def test_the_exact_pair_still_resumes_an_expired_pending_signup(client):
    # Arrange — the same person, submitting BOTH of their own values.
    victim = _victim(username="victim_pending", email="victim@example.com")
    User.objects.filter(pk=victim.pk).update(
        date_joined=timezone.now() - ps.PENDING_SIGNUP_WINDOW - timedelta(hours=3)
    )
    stale_pk = victim.pk

    # Act
    fields = _attacker_fields("victim_pending")
    fields["email"] = "victim@example.com"
    response = client.post(reverse("auth_app:signup"), fields)

    # Assert — the resume path still works: the stale row is replaced and a
    # fresh pending row exists under the same identity.
    assert response.status_code == 302
    assert not User.objects.filter(pk=stale_pk).exists()
    fresh = User.objects.get(username="victim_pending")
    assert fresh.email == "victim@example.com"
    assert fresh.is_active is False


def test_the_exact_pair_still_classifies_as_pending_and_resumable():
    # Arrange
    live = _victim(username="live_one", email="live@example.com")
    expired = _victim(username="old_one", email="old@example.com")
    User.objects.filter(pk=expired.pk).update(
        date_joined=timezone.now() - ps.PENDING_SIGNUP_WINDOW - timedelta(hours=3)
    )

    # Act / Assert — both directions of the legitimate path.
    live_collision, live_user = ps.classify_pending_signup(
        "live@example.com", "live_one"
    )
    expired_collision, expired_user = ps.classify_pending_signup(
        "old@example.com", "old_one"
    )
    assert live_collision is ps.SignupCollision.PENDING_LIVE
    assert live_user is not None and live_user.pk == live.pk
    assert expired_collision is ps.SignupCollision.PENDING_EXPIRED
    assert expired_user is not None and expired_user.pk == expired.pk


# ---------------------------------------------------------------------------
# PR #775 re-review blockers 1 and 2: the LIVE resend endpoint and the guess
# counter. These need the database and run in CI.
# ---------------------------------------------------------------------------


def test_the_resend_endpoint_is_no_longer_csrf_exempt():
    """It was @csrf_exempt: a state-changing POST (mints a code, sends mail)
    that any third-party page could fire on a visitor's behalf."""
    # Arrange
    import json

    from django.test import Client

    csrf_enforcing = Client(enforce_csrf_checks=True)

    # Act
    response = csrf_enforcing.post(
        reverse("auth_app:api_resend_otp"),
        data=json.dumps({"email": "victim@example.com"}),
        content_type="application/json",
    )

    # Assert — no token, no action.
    assert response.status_code == 403


def test_the_resend_response_is_identical_whether_or_not_the_account_exists(client):
    """Different bodies for found/not-found made it an enumeration oracle."""
    # Arrange
    import json

    _victim()

    # Act
    existing = client.post(
        reverse("auth_app:api_resend_otp"),
        data=json.dumps({"email": "victim@example.com"}),
        content_type="application/json",
    )
    missing = client.post(
        reverse("auth_app:api_resend_otp"),
        data=json.dumps({"email": "nobody_at_all@example.com"}),
        content_type="application/json",
    )

    # Assert — byte-for-byte the same answer either way.
    assert existing.status_code == 200
    assert missing.status_code == 200
    assert existing.json() == missing.json()


def test_the_resend_endpoint_is_rate_limited_and_rotates_at_most_one_code(client):
    """It was unlimited: a mail-bomb, and a way to invalidate a victim's
    outstanding code at will."""
    # Arrange
    import json

    from django.core.cache import cache

    from apps.infra.auth_app import pending_signup

    victim = _victim()
    cache.clear()

    # Act — far more requests than the budget allows.
    responses = [
        client.post(
            reverse("auth_app:api_resend_otp"),
            data=json.dumps({"email": victim.email}),
            content_type="application/json",
        )
        for _ in range(pending_signup.RESENDS_ALLOWED_PER_WINDOW + 4)
    ]

    # Assert — uniform answers (no oracle), and the budget really did stop the
    # sends: rotation means at most ONE outstanding code exists.
    assert {r.status_code for r in responses} == {200}
    assert EmailVerification.objects.filter(email=victim.email).count() <= 1
    assert pending_signup.resend_allowed(victim.email) is False


def test_five_wrong_guesses_burn_the_code(client):
    """A 6-digit code is 10**6 possibilities. With no counter, guessing was
    free and unlimited for the whole validity window."""
    # Arrange
    import json

    from apps.infra.auth_app.models import MAX_CODE_ATTEMPTS

    victim = _victim()
    verification = EmailVerification.objects.create(user=victim, email=victim.email)

    # Act — guess wrong, repeatedly, with a code that is not the real one.
    wrong = "000000" if verification.code != "000000" else "111111"
    last = None
    for _ in range(MAX_CODE_ATTEMPTS):
        last = client.post(
            reverse("auth_app:api_verify_email"),
            data=json.dumps({"email": victim.email, "otp_code": wrong}),
            content_type="application/json",
        )

    # Assert — the code is burned and the attempts are on the ROW, so a restart
    # or a second worker cannot reset the budget.
    assert last is not None and last.status_code == 429
    verification.refresh_from_db()
    assert verification.attempts >= MAX_CODE_ATTEMPTS
    assert verification.is_expired()


def test_a_correct_guess_still_verifies_after_the_throttle_exists(client):
    """The control: throttling must not block the legitimate owner."""
    # Arrange
    import json

    victim = _victim()
    verification = EmailVerification.objects.create(user=victim, email=victim.email)

    # Act
    response = client.post(
        reverse("auth_app:api_verify_email"),
        data=json.dumps({"email": victim.email, "otp_code": verification.code}),
        content_type="application/json",
    )

    # Assert
    assert response.status_code == 200
    verification.refresh_from_db()
    assert verification.is_verified is True


# ---------------------------------------------------------------------------
# PR #775 third review: evidence, locking, and races. These need the database.
# ---------------------------------------------------------------------------


def test_an_inactive_NON_PENDING_row_is_never_deleted_by_the_resume_path(client):
    """An administrator-disabled account is inactive, has no pending signup
    behind it, and used to satisfy the expired branch — which DELETED it."""
    # Arrange — inactive, past the window, and NO verification row at all.
    disabled = User.objects.create_user(
        username="disabled_user",
        email="disabled@example.com",
        password="Gx7-quiet-harbour-42",
        is_active=False,
    )
    User.objects.filter(pk=disabled.pk).update(
        date_joined=timezone.now() - ps.PENDING_SIGNUP_WINDOW - timedelta(hours=3)
    )
    assert not EmailVerification.objects.filter(user=disabled).exists()
    disabled_pk = disabled.pk

    fields = _attacker_fields("disabled_user")
    fields["email"] = "disabled@example.com"

    # Act
    client.post(reverse("auth_app:signup"), fields)

    # Assert — the row SURVIVES. is_active=False was never proof of a signup.
    assert User.objects.filter(pk=disabled_pk).exists(), (
        "an inactive NON-PENDING row was deleted by the resume path"
    )


def test_a_proven_pending_row_IS_reclaimed():
    """Control: the evidence requirement must not stop a real reclaim."""
    # Arrange — inactive, expired, and WITH an unverified verification row.
    victim = _victim()
    User.objects.filter(pk=victim.pk).update(
        date_joined=timezone.now() - ps.PENDING_SIGNUP_WINDOW - timedelta(hours=3)
    )
    EmailVerification.objects.create(user=victim, email=victim.email)

    # Act
    collision, _user = ps.classify_and_reclaim(victim.email, victim.username)

    # Assert
    assert collision is ps.SignupCollision.NONE
    assert not User.objects.filter(pk=victim.pk).exists()


def test_the_reclaim_service_cannot_double_delete():
    """Two callers racing the same expired row: the second must find nothing
    rather than acting on a stale classification."""
    # Arrange
    victim = _victim()
    User.objects.filter(pk=victim.pk).update(
        date_joined=timezone.now() - ps.PENDING_SIGNUP_WINDOW - timedelta(hours=3)
    )
    EmailVerification.objects.create(user=victim, email=victim.email)

    # Act
    first, _ = ps.classify_and_reclaim(victim.email, victim.username)
    second, _ = ps.classify_and_reclaim(victim.email, victim.username)

    # Assert — idempotent, and the row is gone exactly once.
    assert first is ps.SignupCollision.NONE
    assert second is ps.SignupCollision.NONE
    assert not User.objects.filter(pk=victim.pk).exists()


def test_a_row_verified_inside_the_window_is_not_reclaimed():
    """The revalidation's whole reason for existing: a verification that lands
    between the classification and the lock must WIN, not be deleted."""
    # Arrange — the row LOOKS expired, but its verification is complete.
    victim = _victim()
    User.objects.filter(pk=victim.pk).update(
        date_joined=timezone.now() - ps.PENDING_SIGNUP_WINDOW - timedelta(hours=3)
    )
    EmailVerification.objects.create(user=victim, email=victim.email, is_verified=True)

    # Act
    collision, _user = ps.classify_and_reclaim(victim.email, victim.username)

    # Assert — untouched.
    assert collision is ps.SignupCollision.INACTIVE_NOT_PENDING
    assert User.objects.filter(pk=victim.pk).exists()
