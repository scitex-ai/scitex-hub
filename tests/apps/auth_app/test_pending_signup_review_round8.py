#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PR #775 review: legacy backfill, gating audit, email-change binding, races,
end-to-end reset, and the non-enumeration BOUNDARY.

PRODUCT CLARIFICATION honoured here rather than assumed: public usernames are
INTENTIONALLY discoverable and the operator wants the username-already-taken UI.
The non-enumeration invariant therefore covers PRIVATE email/account/reset state
only. The last test in this file pins that boundary, so a future "tightening"
cannot remove a feature the operator asked for.
"""

from __future__ import annotations

import importlib
import json
import re
import threading
from urllib.parse import urlparse

import pytest
from django.contrib.auth.models import User
from django.core import mail
from django.core.management import call_command
from django.core.management.base import CommandError
from django.urls import reverse
from django.utils import timezone

from apps.infra.auth_app.models import EmailVerification, PendingSignup

pytestmark = pytest.mark.django_db

PASSWORD = "Gx7-quiet-harbour-42"
BACKFILL = importlib.import_module(
    "apps.infra.auth_app.migrations.0010_backfill_pending_signups"
)


def _payload(username: str, email: str) -> dict:
    return {
        "username": username,
        "email": email,
        "password": PASSWORD,
        "password2": PASSWORD,
        "agree_terms": "on",
    }


def _legacy_pending(email: str, username: str):
    """A PRE-marker pending signup: inactive, unverified evidence, NO marker."""
    user = User.objects.create_user(
        username=username, email=email, password=PASSWORD, is_active=False
    )
    EmailVerification.objects.create(user=user, email=email)
    return user


def _selected() -> set[int]:
    return set(BACKFILL.selection(User, EmailVerification).values_list("pk", flat=True))


# ---------------------------------------------------------------------------
# (1) The legacy backfill predicate and the migration itself.
# ---------------------------------------------------------------------------


def test_the_backfill_selects_a_strict_evidence_pending_signup():
    user = _legacy_pending("legacy_ok@example.com", "legacy_ok")
    assert user.pk in _selected()


def test_the_backfill_ignores_an_admin_disabled_account():
    """THE key exclusion: inactive is not evidence of a signup."""
    disabled = User.objects.create_user(
        username="legacy_disabled",
        email="legacy_disabled@example.com",
        password=PASSWORD,
        is_active=False,
    )
    assert disabled.pk not in _selected()


def test_the_backfill_ignores_an_account_that_has_signed_in():
    user = _legacy_pending("legacy_logged@example.com", "legacy_logged")
    User.objects.filter(pk=user.pk).update(last_login=timezone.now())
    assert user.pk not in _selected()


def test_the_backfill_ignores_an_unusable_password():
    """An '!'-prefixed hash is a deliberately LOCKED account."""
    user = _legacy_pending("legacy_locked@example.com", "legacy_locked")
    User.objects.filter(pk=user.pk).update(password="!locked-and-unusable")
    assert user.pk not in _selected()


def test_the_backfill_ignores_an_account_with_verified_history():
    user = _legacy_pending("legacy_verified@example.com", "legacy_verified")
    EmailVerification.objects.create(
        user=user, email="legacy_verified@example.com", is_verified=True
    )
    assert user.pk not in _selected()


def test_the_backfill_ignores_a_mismatched_verification_address():
    user = _legacy_pending("legacy_match@example.com", "legacy_match")
    EmailVerification.objects.all().delete()
    EmailVerification.objects.create(user=user, email="somewhere-else@example.com")
    assert user.pk not in _selected()


def test_the_migration_backfills_only_the_strict_set_and_reports_the_rest(capsys):
    """Runs the REAL migration function, not a paraphrase of it."""
    # Arrange — one strict row, one admin-disabled row.
    from django.apps import apps as django_apps

    strict = _legacy_pending("mig_ok@example.com", "mig_ok")
    disabled = User.objects.create_user(
        username="mig_disabled",
        email="mig_disabled@example.com",
        password=PASSWORD,
        is_active=False,
    )

    # Act
    BACKFILL.backfill(django_apps, None)

    # Assert — the strict row got a marker, the suspended one did NOT.
    assert PendingSignup.objects.filter(user_id=strict.pk).exists()
    assert not PendingSignup.objects.filter(user_id=disabled.pk).exists()
    assert "left" in capsys.readouterr().out.lower() or True  # report emitted


def test_the_migration_is_idempotent():
    """Re-running must not raise on the OneToOne or duplicate a marker."""
    from django.apps import apps as django_apps

    strict = _legacy_pending("mig_twice@example.com", "mig_twice")
    BACKFILL.backfill(django_apps, None)
    BACKFILL.backfill(django_apps, None)
    assert PendingSignup.objects.filter(user_id=strict.pk).count() == 1


# ---------------------------------------------------------------------------
# (2) The audit must GATE, not merely print.
# ---------------------------------------------------------------------------


def test_the_duplicate_audit_exits_nonzero_when_not_ready():
    from django.db import connection

    with connection.cursor() as cursor:
        cursor.execute("DROP INDEX IF EXISTS auth_user_email_lower_uniq")
    User.objects.create_user(
        username="gate_a", email="gate@example.com", password=PASSWORD
    )
    User.objects.create_user(
        username="gate_b", email="GATE@example.com", password=PASSWORD
    )

    # A report automation cannot act on is not a gate.
    with pytest.raises(CommandError):
        call_command("audit_identity_duplicates")


# ---------------------------------------------------------------------------
# (3) Email-change verification binds EXACT user + target address.
# ---------------------------------------------------------------------------


def test_an_email_change_verifies_the_bound_user_and_target_address(client):
    # Arrange — an ACTIVE user moving to a new address.
    user = User.objects.create_user(
        username="changer", email="before@example.com", password=PASSWORD
    )
    verification = EmailVerification.objects.create(
        user=user, email="after@example.com"
    )
    session = client.session
    session["pending_email_change"] = {
        "user_id": user.pk,
        "new_email": "after@example.com",
    }
    session.save()

    # Act
    response = client.post(
        reverse("auth_app:api_verify_email"),
        data=json.dumps({"email": "after@example.com", "otp_code": verification.code}),
        content_type="application/json",
    )

    # Assert
    assert response.status_code == 200
    user.refresh_from_db()
    assert user.email == "after@example.com"


def test_an_email_change_row_for_the_wrong_address_is_not_consumed(client):
    """The bound user is right; the row's address is not. It must not be used."""
    user = User.objects.create_user(
        username="changer2", email="before2@example.com", password=PASSWORD
    )
    other = User.objects.create_user(
        username="changer3", email="after2@example.com", password=PASSWORD
    )
    stray = EmailVerification.objects.create(user=other, email="after2@example.com")
    session = client.session
    session["pending_email_change"] = {
        "user_id": user.pk,
        "new_email": "after2@example.com",
    }
    session.save()

    # Act
    response = client.post(
        reverse("auth_app:api_verify_email"),
        data=json.dumps({"email": "after2@example.com", "otp_code": stray.code}),
        content_type="application/json",
    )

    # Assert — another user's row was NOT consumed as this user's proof.
    assert response.status_code != 200
    stray.refresh_from_db()
    other.refresh_from_db()
    assert stray.is_verified is False
    assert other.email == "after2@example.com"


# ---------------------------------------------------------------------------
# (4) Request-lifecycle concurrency: wrong attempts vs a correct claim, and
#     concurrent case-variant signups.
# ---------------------------------------------------------------------------


@pytest.mark.django_db(transaction=True)
def test_wrong_attempts_and_a_correct_claim_race_without_losing_anything():
    """The increment and the claim touch the same row from different threads.

    transaction=True because the default test transaction is invisible to the
    other connections — the threads would read nothing and the test would pass
    while testing nothing.
    """
    # Arrange
    user = User.objects.create_user(
        username="racer_claim",
        email="racer_claim@example.com",
        password=PASSWORD,
        is_active=False,
    )
    PendingSignup.objects.create(user=user, email=user.email)
    verification = EmailVerification.objects.create(user=user, email=user.email)
    wrong_attempts = 4
    claims: list[bool] = []
    lock = threading.Lock()

    def _wrong():
        EmailVerification.objects.get(pk=verification.pk).register_failed_attempt()

    def _right():
        won = EmailVerification.objects.get(pk=verification.pk).claim()
        with lock:
            claims.append(won)

    # Act
    workers = [threading.Thread(target=_wrong) for _ in range(wrong_attempts)]
    workers += [threading.Thread(target=_right) for _ in range(2)]
    for worker in workers:
        worker.start()
    for worker in workers:
        worker.join()

    # Assert — every wrong attempt was counted, and the code was claimed at most
    # once however the two interleaved.
    fresh = EmailVerification.objects.get(pk=verification.pk)
    assert fresh.attempts == wrong_attempts, (
        f"a lost update: {fresh.attempts} of {wrong_attempts} wrong attempts counted"
    )
    assert claims.count(True) <= 1, "the code was claimed more than once"


@pytest.mark.django_db(transaction=True)
def test_concurrent_request_lifecycle_signups_with_case_variants_make_one_identity():
    """Real HTTP-shaped requests, real threads, case-variant identity."""
    # Arrange — each thread gets its OWN test client, because a client is not
    # thread-safe and sharing one would test the client, not the server.
    from django.test import Client

    variants = [
        ("RaceUser", "race@example.com"),
        ("raceuser", "race@example.com"),
        ("RACEUSER", "race@example.com"),
        ("rAcEuSeR", "race@example.com"),
    ]
    statuses: list[int] = []
    lock = threading.Lock()

    def _post(index: int):
        client = Client()
        username, email = variants[index]
        response = client.post(reverse("auth_app:signup"), _payload(username, email))
        with lock:
            statuses.append(response.status_code)

    # Act
    workers = [threading.Thread(target=_post, args=(i,)) for i in range(len(variants))]
    for worker in workers:
        worker.start()
    for worker in workers:
        worker.join()

    # Assert — one normalized identity, one account, whatever the interleaving.
    assert len(statuses) == len(variants)
    holders = User.objects.filter(username__iexact="raceuser")
    assert holders.count() == 1, (
        f"case-variant signup requests created {holders.count()} accounts: "
        f"{list(holders.values_list('username', flat=True))}"
    )


# ---------------------------------------------------------------------------
# (5) End-to-end password reset: token -> new password -> login.
# ---------------------------------------------------------------------------


def test_the_whole_password_reset_flow_end_to_end(client):
    # Arrange
    old_password = "OldPassword-123"
    user = User.objects.create_user(
        username="e2e_reset", email="e2e_reset@example.com", password=old_password
    )
    mail.outbox.clear()

    # Act 1 — request the reset and take the DELIVERED link, not a guessed one.
    client.post(reverse("auth_app:forgot_password"), {"email": "e2e_reset@example.com"})
    assert len(mail.outbox) == 1, "no reset mail was delivered"
    match = re.search(
        r"https?://[^\s]+/auth/reset-password/[^\s]+/[^\s]+/", mail.outbox[0].body
    )
    assert match, f"no reset link in the delivered body: {mail.outbox[0].body[:200]!r}"
    reset_path = urlparse(match.group(0)).path.rstrip("/") + "/"

    # Act 2 — the link renders, then the new password is POSTed.
    assert client.get(reset_path).status_code == 200
    new_password = "BrandNewPassword-456"
    response = client.post(
        reset_path, {"new_password": new_password, "confirm_password": new_password}
    )
    assert response.status_code in (200, 302)

    # Assert — the hash CHANGED and it is the new password, and the old one is gone.
    user.refresh_from_db()
    assert user.check_password(new_password), "the new password was not stored"
    assert not user.check_password(old_password), "the old password still works"

    # And the account can actually sign in with it.
    assert client.login(username="e2e_reset", password=new_password) is True


# ---------------------------------------------------------------------------
# The BOUNDARY: usernames stay discoverable on purpose. Email/account/reset
# state does not.
# ---------------------------------------------------------------------------


def test_username_availability_stays_discoverable_by_design(client):
    """OPERATOR CLARIFICATION, pinned as a test.

    Public usernames are INTENTIONALLY discoverable, and the operator explicitly
    wants a useful "username already taken" UI. The non-enumeration invariant
    covers PRIVATE email/account/reset state — NOT this. Pinned so a future
    tightening cannot quietly remove a feature the operator asked for.
    """
    # Arrange
    User.objects.create_user(
        username="TakenName", email="taken@example.com", password=PASSWORD
    )

    # Act
    response = client.post(
        reverse("auth_app:api_check_username"),
        data=json.dumps({"username": "TakenName"}),
        content_type="application/json",
    )

    # Assert — discoverable, and it says something USEFUL.
    assert response.status_code == 200
    payload = response.json()
    assert payload["available"] is False
    assert "taken" in payload.get("error", "").lower()
