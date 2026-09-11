#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Database-backed behavioural regressions for PR #775 (fifth review).

These are the regressions the review asked for by name. They are DATABASE tests:
each one drives a real endpoint through the Django test client with a FORM-VALID
payload and asserts on rows, so a pass means the behaviour was exercised, not
that a source guard happened to match.

EXECUTION NOTE, stated because it is the truth here: this container cannot run
them. The only reachable Postgres is 127.0.0.1:5433 and it rejects the dev
credentials (FATAL: password authentication failed for user "scitex_dev"); no
SCITEX_HUB_DB_PASSWORD_DEV is present and guessing a database password is not
something to do. They are written to be run by CI (or by anyone with the dev
credential). They have NOT been observed green.
"""

from __future__ import annotations

import json
import threading
from datetime import timedelta

import pytest
from django.contrib.auth.models import User
from django.core.cache import cache
from django.urls import reverse
from django.utils import timezone

from apps.infra.auth_app import pending_signup as ps
from apps.infra.auth_app.forms import SignupForm
from apps.infra.auth_app.models import MAX_CODE_ATTEMPTS, EmailVerification

pytestmark = pytest.mark.django_db

PASSWORD = "Gx7-quiet-harbour-42"


def _payload(username: str, email: str) -> dict:
    """A FORM-VALID signup payload.

    SignupForm expects ``password2``. A key the form ignores leaves the form
    INVALID and the request never reaches the branch under test, which is exactly
    how this suite's predecessor gave a false green. Asserted below rather than
    assumed.
    """
    return {
        "username": username,
        "email": email,
        "password": PASSWORD,
        "password2": PASSWORD,
        "agree_terms": "on",
    }


def _disabled(email="disabled@example.com", username="disabled_user"):
    """An ADMIN-DISABLED account: inactive, and NOT a signup."""
    return User.objects.create_user(
        username=username, email=email, password=PASSWORD, is_active=False
    )


def _pending(email="pending@example.com", username="pending_user", age=None):
    """A genuine pending signup: inactive AND with unverified evidence."""
    user = User.objects.create_user(
        username=username, email=email, password=PASSWORD, is_active=False
    )
    EmailVerification.objects.create(user=user, email=email)
    if age is not None:
        User.objects.filter(pk=user.pk).update(date_joined=timezone.now() - age)
        user.refresh_from_db()
    return user


def _codes(email: str):
    return EmailVerification.objects.filter(email__iexact=email)


# ---------------------------------------------------------------------------
# 0. The payloads must be form-valid, or nothing below means anything.
# ---------------------------------------------------------------------------


def test_the_payload_this_suite_posts_is_form_valid():
    form = SignupForm(data=_payload("payload_probe", "payload_probe@example.com"))
    assert form.is_valid(), form.errors


def test_the_endpoints_this_suite_drives_are_the_real_ones():
    # Assert each name RESOLVES to the endpoint this suite means to drive. The
    # stems are asserted rather than full strings: a mount-prefix change is not
    # what these regressions are about, and a test that reds for an unrelated
    # rename teaches nothing.
    assert reverse("auth_app:signup").endswith("/signup/")
    assert reverse("auth_app:api_resend_otp").endswith("/api/resend-otp/")
    assert reverse("auth_app:api_verify_email").endswith("/api/verify-email/")


def _resend(client, email: str):
    return client.post(
        reverse("auth_app:api_resend_otp"),
        data=json.dumps({"email": email}),
        content_type="application/json",
    )


def _verify(client, email: str, code: str):
    return client.post(
        reverse("auth_app:api_verify_email"),
        data=json.dumps({"email": email, "otp_code": code}),
        content_type="application/json",
    )


# ---------------------------------------------------------------------------
# 1. An admin-disabled account cannot mint, receive, or use a signup OTP.
# ---------------------------------------------------------------------------


def test_an_admin_disabled_account_cannot_mint_a_resend_code(client):
    """It has no pending signup behind it, so no code may be created for it."""
    # Arrange
    account = _disabled()
    cache.clear()
    codes_before = _codes(account.email).count()

    # Act
    response = _resend(client, account.email)

    # Assert — generic answer, and NO code minted.
    assert response.status_code == 200
    assert _codes(account.email).count() == codes_before


def test_an_admin_disabled_account_with_a_forged_code_is_not_reactivated(client):
    """The bypass: a code for an admin-disabled row used to switch it back on."""
    # Arrange — simulate the OTP having been minted by some other path.
    account = _disabled()
    verification = EmailVerification.objects.create(user=account, email=account.email)

    # Act — correct code, wrong account.
    response = _verify(client, account.email, verification.code)

    # Assert — refused, and STILL DISABLED.
    assert response.status_code == 400
    account.refresh_from_db()
    assert account.is_active is False


def test_the_signup_path_cannot_resume_an_admin_disabled_account(client):
    # Arrange
    account = _disabled()
    disabled_pk = account.pk

    # Act — the exact pair, submitted as a signup.
    response = client.post(
        reverse("auth_app:signup"), _payload(account.username, account.email)
    )

    # Assert — untouched: same row, still inactive, no code.
    assert response.status_code == 302
    assert User.objects.filter(pk=disabled_pk).exists()
    account.refresh_from_db()
    assert account.is_active is False
    assert _codes(account.email).count() == 0


# ---------------------------------------------------------------------------
# 2. Stale unverified history cannot reclassify an account as pending.
# ---------------------------------------------------------------------------


def test_stale_unverified_history_does_not_make_an_active_account_pending():
    """The live-account shape: verified once, unverified rows lingering after."""
    # Arrange — verified history, then an inactive (admin-disabled) state.
    account = User.objects.create_user(
        username="was_active", email="was_active@example.com", password=PASSWORD
    )
    EmailVerification.objects.create(
        user=account, email=account.email, is_verified=True
    )
    EmailVerification.objects.create(user=account, email=account.email)
    User.objects.filter(pk=account.pk).update(
        is_active=False, date_joined=timezone.now() - ps.PENDING_SIGNUP_WINDOW
    )

    # Act
    collision, found = ps.classify_pending_signup(account.email, account.username)

    # Assert — the verified history disqualifies it outright.
    assert collision is ps.SignupCollision.INACTIVE_NOT_PENDING
    assert found is None
    assert not ps.has_pending_evidence(account, account.email)


def test_evidence_for_a_different_address_does_not_count():
    # Arrange — an unverified row, but for somebody else's address.
    account = _disabled(email="mine@example.com", username="mine")
    EmailVerification.objects.create(user=account, email="someone_else@example.com")

    # Act / Assert
    assert ps.has_pending_evidence(account, "mine@example.com") is False


# ---------------------------------------------------------------------------
# 3. A failed resend must PRESERVE the previously valid code.
# ---------------------------------------------------------------------------


def test_a_failed_resend_preserves_the_previous_code(client, monkeypatch):
    # Arrange — a genuine pending signup with one already-delivered code.
    user = _pending()
    previous = _codes(user.email).get()
    previous_code = previous.code
    cache.clear()

    monkeypatch.setattr(
        "apps.infra.project_app.services.email_service.EmailService.send_otp_email",
        staticmethod(lambda **kwargs: (False, "smtp down")),
    )

    # Act
    response = _resend(client, user.email)

    # Assert — the generic answer, the old code still present and UNCHANGED, and
    # no orphaned replacement left behind.
    assert response.status_code == 200
    survivors = _codes(user.email)
    assert survivors.count() == 1
    assert survivors.get().code == previous_code


def test_a_successful_resend_retires_the_previous_code(client, monkeypatch):
    """Control: the ordering fix must not stop rotation from happening."""
    # Arrange
    user = _pending()
    previous_code = _codes(user.email).get().code
    cache.clear()
    monkeypatch.setattr(
        "apps.infra.project_app.services.email_service.EmailService.send_otp_email",
        staticmethod(lambda **kwargs: (True, "sent")),
    )

    # Act
    response = _resend(client, user.email)

    # Assert
    assert response.status_code == 200
    survivors = _codes(user.email)
    assert survivors.count() == 1
    assert survivors.get().code != previous_code


# ---------------------------------------------------------------------------
# 4. Atomic counters under concurrent use.
# ---------------------------------------------------------------------------


def test_the_resend_budget_holds_under_concurrent_callers():
    """Threads, because a mail-bomb is parallel and check-then-act is not."""
    # Arrange
    cache.clear()
    email = "concurrent@example.com"
    threads = ps.RESENDS_ALLOWED_PER_WINDOW * 4
    results: list[bool] = []
    lock = threading.Lock()

    def spend():
        allowed = ps.consume_resend_budget(email)
        with lock:
            results.append(allowed)

    # Act
    workers = [threading.Thread(target=spend) for _ in range(threads)]
    for worker in workers:
        worker.start()
    for worker in workers:
        worker.join()

    # Assert — exactly the cap got through, no matter the interleaving.
    assert len(results) == threads
    assert results.count(True) == ps.RESENDS_ALLOWED_PER_WINDOW


def test_the_attempt_counter_does_not_lose_an_update():
    """Two holders of a STALE copy each increment: both must land.

    With the old read-modify-write the second save wrote the first one's value
    plus one, so N parallel guesses never reached the cap.
    """
    # Arrange
    user = _pending()
    stale_a = EmailVerification.objects.get(user=user)
    stale_b = EmailVerification.objects.get(user=user)

    # Act
    stale_a.register_failed_attempt()
    stale_b.register_failed_attempt()

    # Assert — two increments, not one.
    fresh = EmailVerification.objects.get(pk=stale_a.pk)
    assert fresh.attempts == 2


def test_the_attempt_cap_burns_the_code():
    # Arrange
    user = _pending()
    verification = EmailVerification.objects.get(user=user)

    # Act
    for _ in range(MAX_CODE_ATTEMPTS):
        verification.register_failed_attempt()

    # Assert
    verification.refresh_from_db()
    assert verification.attempts >= MAX_CODE_ATTEMPTS
    assert verification.is_expired()


# ---------------------------------------------------------------------------
# 5. An expired pending resume must not delete/recreate the row.
# ---------------------------------------------------------------------------


def test_resuming_an_expired_pending_signup_keeps_the_same_row(client):
    """No destructive replacement: the identity survives, so there is no window
    in which the username is free for another request to take."""
    # Arrange — expired pending signup.
    user = _pending(age=ps.PENDING_SIGNUP_WINDOW + timedelta(hours=3))
    original_pk = user.pk
    rows_before = User.objects.filter(username__iexact=user.username).count()

    # Act
    response = client.post(
        reverse("auth_app:signup"), _payload(user.username, user.email)
    )

    # Assert — SAME pk, SAME count: re-armed in place, never replaced.
    assert response.status_code == 302
    assert User.objects.filter(pk=original_pk).exists(), "the row was deleted"
    assert User.objects.filter(username__iexact=user.username).count() == rows_before
    survivor = User.objects.get(pk=original_pk)
    assert survivor.username == user.username
    assert survivor.email == user.email
    assert survivor.is_active is False


def test_the_reclaim_service_never_deletes_anything():
    """Directly: the service reports an expired pending signup and mutates
    nothing, which is what removes the namespace gap."""
    # Arrange
    user = _pending(age=ps.PENDING_SIGNUP_WINDOW + timedelta(hours=3))
    original_pk = user.pk

    # Act
    collision, found = ps.classify_and_reclaim(user.email, user.username)

    # Assert
    assert collision is ps.SignupCollision.PENDING_EXPIRED
    assert found is not None and found.pk == original_pk
    assert User.objects.filter(pk=original_pk).exists()


# ---------------------------------------------------------------------------
# 6. The legitimate path still works end to end (controls).
# ---------------------------------------------------------------------------


def test_a_genuine_pending_signup_can_still_be_verified(client):
    """Control: the activation gate must not block the real flow."""
    # Arrange
    user = _pending()
    verification = EmailVerification.objects.get(user=user)

    # Act
    response = _verify(client, user.email, verification.code)

    # Assert
    assert response.status_code == 200
    user.refresh_from_db()
    assert user.is_active is True


def test_a_genuine_pending_signup_can_still_resend(client, monkeypatch):
    """Control: the evidence gate must not block the real flow."""
    # Arrange
    user = _pending()
    cache.clear()
    monkeypatch.setattr(
        "apps.infra.project_app.services.email_service.EmailService.send_otp_email",
        staticmethod(lambda **kwargs: (True, "sent")),
    )

    # Act
    response = _resend(client, user.email)

    # Assert
    assert response.status_code == 200
    assert _codes(user.email).count() == 1
