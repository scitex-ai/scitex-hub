#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PR #775 review: legacy reconciliation, gating audit, email-change binding,
races, end-to-end reset, and the non-enumeration BOUNDARY.

THE AUTO-BACKFILL IS GONE, ON PURPOSE. This file previously tested a migration
that marked inactive users matching an evidence predicate. That was unsafe: an
ADMIN-DISABLED account that never signed in can also carry an old matching
unverified row, so the predicate cannot separate it from an abandoned signup and
applying it would GRANT SIGNUP AUTHORITY TO A SUSPENDED ACCOUNT. The tests below
assert the LIMITATION and the replacement process, not a capability we do not
have.

PRODUCT CLARIFICATION honoured: public usernames are INTENTIONALLY discoverable
and the username-already-taken UI is wanted. The non-enumeration invariant covers
PRIVATE email/account/reset state only; the boundary test pins that.
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

from apps.infra.auth_app import pending_signup as ps
from apps.infra.auth_app.models import EmailVerification, PendingSignup

pytestmark = pytest.mark.django_db

PASSWORD = "Gx7-quiet-harbour-42"
PROVENANCE = importlib.import_module(
    "apps.infra.auth_app.migrations.0010_pending_signup_provenance"
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
    """A pre-marker pending signup: inactive, unverified row, NO marker."""
    user = User.objects.create_user(
        username=username, email=email, password=PASSWORD, is_active=False
    )
    EmailVerification.objects.create(user=user, email=email)
    return user


def _candidate_ids() -> set[int]:
    return set(ps.legacy_pending_candidates().values_list("pk", flat=True))


# ---------------------------------------------------------------------------
# (1) The predicate's LIMITATION, and the process that replaced auto-grant.
# ---------------------------------------------------------------------------


def test_a_disabled_account_with_an_old_matching_row_is_indistinguishable():
    """THE REVIEW'S CASE, pinned as a test.

    Inactive, never signed in, usable password, no verified history, and an old
    matching unverified row — the predicate CANNOT tell it from an abandoned
    signup, so it IS a candidate. That is precisely why nothing auto-applies it.
    """
    disabled = User.objects.create_user(
        username="disabled_with_row",
        email="disabled_with_row@example.com",
        password=PASSWORD,
        is_active=False,
    )
    EmailVerification.objects.create(user=disabled, email=disabled.email)

    # Indistinguishable from a signup: it IS a candidate …
    assert disabled.pk in _candidate_ids()
    # … and that is the whole reason it must NOT be marked automatically.
    assert not PendingSignup.objects.filter(user_id=disabled.pk).exists()


def test_the_predicate_still_narrows_the_field():
    """It is not useless — it removes the clearly-not-signup shapes."""
    # Signed in at some point.
    logged_in = _legacy_pending("was_used@example.com", "was_used")
    User.objects.filter(pk=logged_in.pk).update(last_login=timezone.now())
    # Unusable password: a deliberately locked account.
    locked = _legacy_pending("locked@example.com", "locked")
    User.objects.filter(pk=locked.pk).update(password="!locked")
    # Already verified once.
    verified = _legacy_pending("verified@example.com", "verified")
    EmailVerification.objects.create(
        user=verified, email="verified@example.com", is_verified=True
    )
    # Address mismatch on the only row.
    mismatched = _legacy_pending("mismatch@example.com", "mismatch")
    EmailVerification.objects.all().delete()
    EmailVerification.objects.create(user=mismatched, email="elsewhere@example.com")

    candidates = _candidate_ids()
    for excluded in (logged_in, locked, verified, mismatched):
        assert excluded.pk not in candidates, f"{excluded.username} was a candidate"


def test_the_audit_lists_ids_with_evidence_and_writes_nothing(capsys):
    from io import StringIO

    candidate = _legacy_pending("audit_cand@example.com", "audit_cand")
    ambiguous = User.objects.create_user(
        username="audit_ambig",
        email="audit_ambig@example.com",
        password=PASSWORD,
        is_active=False,
    )
    before = (User.objects.count(), PendingSignup.objects.count())
    out = StringIO()

    call_command("audit_legacy_pending_signups", stdout=out)

    text = out.getvalue()
    assert f"user id={candidate.pk}" in text
    assert f"user id={ambiguous.pk}" in text
    assert "CANDIDATES" in text and "AMBIGUOUS" in text
    assert (User.objects.count(), PendingSignup.objects.count()) == before


def test_reconcile_requires_explicit_ids():
    """No default target, ever: a command that guesses is the auto-backfill."""
    with pytest.raises(CommandError):
        call_command("reconcile_legacy_pending_signups")


def test_reconcile_marks_a_named_candidate_with_provenance():
    candidate = _legacy_pending("reconcile_ok@example.com", "reconcile_ok")

    call_command(
        "reconcile_legacy_pending_signups",
        "--user-id",
        str(candidate.pk),
        "--reconciled-by",
        "operator-test",
    )

    marker = PendingSignup.objects.get(user_id=candidate.pk)
    assert marker.email == "reconcile_ok@example.com"
    assert marker.reconciled_at is not None
    assert marker.reconciled_by == "operator-test"


def test_reconcile_REFUSES_an_id_that_fails_the_recheck():
    """A non-candidate is refused loudly, not silently skipped."""
    non_candidate = User.objects.create_user(
        username="reconcile_no",
        email="reconcile_no@example.com",
        password=PASSWORD,
        is_active=False,
    )

    with pytest.raises(CommandError):
        call_command(
            "reconcile_legacy_pending_signups", "--user-id", str(non_candidate.pk)
        )

    assert not PendingSignup.objects.filter(user_id=non_candidate.pk).exists()


def test_reconcile_dry_run_writes_nothing():
    candidate = _legacy_pending("reconcile_dry@example.com", "reconcile_dry")

    call_command(
        "reconcile_legacy_pending_signups",
        "--user-id",
        str(candidate.pk),
        "--dry-run",
    )

    assert not PendingSignup.objects.filter(user_id=candidate.pk).exists()


def test_the_provenance_migration_cannot_delete_post_migration_markers():
    """Source-level, deliberately: the REVERSE must not recompute a predicate.

    The previous reverse re-derived the selection and deleted those markers —
    which would delete markers created by GENUINE signups after this migration
    ran. Dropping columns cannot delete a row, so the operation set is asserted to
    contain only AddField.
    """
    from django.db import migrations as dj_migrations

    operations = PROVENANCE.Migration.operations
    assert operations, "the migration has no operations"
    assert all(isinstance(op, dj_migrations.AddField) for op in operations), [
        type(op).__name__ for op in operations
    ]
    assert not any(isinstance(op, dj_migrations.RunPython) for op in operations)


def test_a_genuine_marker_has_no_reconciliation_provenance():
    """Control: provenance distinguishes reconciliation from a real signup."""
    user = User.objects.create_user(
        username="genuine",
        email="genuine@example.com",
        password=PASSWORD,
        is_active=False,
    )
    marker = PendingSignup.objects.create(user=user, email=user.email)
    assert marker.reconciled_at is None
    assert marker.reconciled_by == ""


# ---------------------------------------------------------------------------
# (2) The duplicate audit must GATE.
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

    with pytest.raises(CommandError):
        call_command("audit_identity_duplicates")


# ---------------------------------------------------------------------------
# (3) Email-change verification binds EXACT user + target address.
# ---------------------------------------------------------------------------


def test_an_email_change_verifies_the_bound_user_and_target_address(client):
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

    response = client.post(
        reverse("auth_app:api_verify_email"),
        data=json.dumps({"email": "after@example.com", "otp_code": verification.code}),
        content_type="application/json",
    )

    assert response.status_code == 200
    user.refresh_from_db()
    assert user.email == "after@example.com"


def test_an_email_change_row_belonging_to_another_user_is_not_consumed(client):
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

    client.post(
        reverse("auth_app:api_verify_email"),
        data=json.dumps({"email": "after2@example.com", "otp_code": stray.code}),
        content_type="application/json",
    )

    stray.refresh_from_db()
    assert stray.is_verified is False


# ---------------------------------------------------------------------------
# (4) Serialized terminal states: fifth wrong attempt vs the correct claim.
# ---------------------------------------------------------------------------


@pytest.mark.django_db(transaction=True)
def test_the_fifth_wrong_attempt_and_a_correct_claim_have_only_two_terminal_states():
    """Preload EXACTLY 4 failures, then release the 5th wrong and the correct
    claim TOGETHER from a barrier, so they genuinely race.

    Only two shapes are coherent afterwards:
        (a) the claim won  -> is_verified True  (it read attempts < MAX, so the
            claim was legitimate; the 5th wrong may still burn the code AFTER,
            which is why "verified" does not exclude "expired")
        (b) the claim lost -> is_verified False and the code is burned
    A third shape — verified with the increment LOST (attempts < 5) — is a lost
    update, and that is what this asserts against.
    """
    user = User.objects.create_user(
        username="race_terminal",
        email="race_terminal@example.com",
        password=PASSWORD,
        is_active=False,
    )
    PendingSignup.objects.create(user=user, email=user.email)
    verification = EmailVerification.objects.create(user=user, email=user.email)

    # Preload EXACTLY four failures, one at a time.
    for _ in range(4):
        EmailVerification.objects.get(pk=verification.pk).register_failed_attempt()
    assert EmailVerification.objects.get(pk=verification.pk).attempts == 4

    barrier = threading.Barrier(2)
    claimed: list[bool] = []
    lock = threading.Lock()

    def _fifth_wrong():
        try:
            barrier.wait()
            EmailVerification.objects.get(pk=verification.pk).register_failed_attempt()
        finally:
            # Each thread MUST close its own connection, or the dev Postgres
            # reaches "sorry, too many clients already" and the test fails for an
            # environmental reason that looks like a logic failure.
            from django.db import connection

            connection.close()

    def _correct_claim():
        try:
            barrier.wait()
            won = EmailVerification.objects.get(pk=verification.pk).claim()
            with lock:
                claimed.append(won)
        finally:
            from django.db import connection

            connection.close()

    threads = [
        threading.Thread(target=_fifth_wrong),
        threading.Thread(target=_correct_claim),
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    fresh = EmailVerification.objects.get(pk=verification.pk)
    won = bool(claimed and claimed[0])

    # The increment is exact — no lost update under the race.
    assert fresh.attempts == 5, f"lost update: attempts={fresh.attempts}, expected 5"

    if won:
        # State (a).
        assert fresh.is_verified is True
    else:
        # State (b).
        assert fresh.is_verified is False
        assert fresh.is_expired(), "a lost claim left the code neither used nor burned"


@pytest.mark.django_db(transaction=True)
def test_concurrent_case_variant_signup_requests_are_uniform_and_create_one_identity(
    monkeypatch,
):
    """Four case-variant REQUESTS, each with its own client.

    Asserts: uniform responses, and exactly ONE User, ONE PendingSignup for it,
    ONE usable OTP, and ONE delivery side effect. The delivery count matters —
    "one account" is not the same claim as "one email sent", and a request that
    re-sent would still leave one account.
    """
    from django.test import Client

    sent: list[dict] = []
    lock = threading.Lock()

    def _fake_send(**kwargs):
        with lock:
            sent.append(kwargs)
        return (True, "sent")

    monkeypatch.setattr(
        "apps.infra.project_app.services.email_service.EmailService.send_otp_email",
        staticmethod(_fake_send),
    )

    variants = [
        ("RaceUser", "race@example.com"),
        ("raceuser", "race@example.com"),
        ("RACEUSER", "race@example.com"),
    ]
    statuses: list[int] = []

    def _post(index: int):
        try:
            client = Client()
            username, email = variants[index]
            response = client.post(
                reverse("auth_app:signup"), _payload(username, email)
            )
            with lock:
                statuses.append(response.status_code)
        finally:
            # Per-thread connection close; see the note in the race test above.
            from django.db import connection

            connection.close()

    workers = [threading.Thread(target=_post, args=(i,)) for i in range(len(variants))]
    for worker in workers:
        worker.start()
    for worker in workers:
        worker.join()

    # Uniform responses: one shape for every caller, whatever happened.
    assert len(statuses) == len(variants)
    assert len(set(statuses)) == 1, f"responses differed: {statuses}"

    holders = User.objects.filter(username__iexact="raceuser")
    assert holders.count() == 1, (
        f"{holders.count()} accounts: {list(holders.values_list('username', flat=True))}"
    )
    holder = holders.get()
    assert PendingSignup.objects.filter(user=holder).count() == 1
    usable = EmailVerification.objects.filter(user=holder, is_verified=False)
    assert usable.count() == 1, f"{usable.count()} usable OTP rows"
    assert len(sent) == 1, f"{len(sent)} verification emails were sent"


# ---------------------------------------------------------------------------
# (5) End-to-end password reset.
# ---------------------------------------------------------------------------


def test_the_whole_password_reset_flow_end_to_end(client):
    old_password = "OldPassword-123"
    user = User.objects.create_user(
        username="e2e_reset", email="e2e_reset@example.com", password=old_password
    )
    mail.outbox.clear()

    client.post(reverse("auth_app:forgot_password"), {"email": "e2e_reset@example.com"})
    assert len(mail.outbox) == 1, "no reset mail was delivered"
    match = re.search(
        r"https?://[^\s]+/auth/reset-password/[^\s]+/[^\s]+/", mail.outbox[0].body
    )
    assert match, f"no reset link in the delivered body: {mail.outbox[0].body[:200]!r}"
    reset_path = urlparse(match.group(0)).path.rstrip("/") + "/"

    assert client.get(reset_path).status_code == 200
    new_password = "BrandNewPassword-456"
    response = client.post(
        reset_path, {"new_password": new_password, "confirm_password": new_password}
    )
    assert response.status_code in (200, 302)

    user.refresh_from_db()
    assert user.check_password(new_password), "the new password was not stored"
    assert not user.check_password(old_password), "the old password still works"
    assert client.login(username="e2e_reset", password=new_password) is True


# ---------------------------------------------------------------------------
# The BOUNDARY: usernames stay discoverable on purpose.
# ---------------------------------------------------------------------------


def test_username_availability_stays_discoverable_by_design(client):
    """OPERATOR CLARIFICATION, pinned as a test.

    Public usernames are INTENTIONALLY discoverable and the already-taken UI is
    wanted. The non-enumeration invariant covers PRIVATE email/account/reset
    state, NOT this — pinned so a future tightening cannot quietly remove a
    feature the operator asked for.
    """
    User.objects.create_user(
        username="TakenName", email="taken@example.com", password=PASSWORD
    )

    response = client.post(
        reverse("auth_app:api_check_username"),
        data=json.dumps({"username": "TakenName"}),
        content_type="application/json",
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["available"] is False
    assert "taken" in payload.get("error", "").lower()
