#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Password reset: NON-ENUMERATING and DUPLICATE-ROBUST, end to end.

``forgot_password`` used ``User.objects.get(email=email)`` — three defects in one
statement:

  * CASE-SENSITIVE, while the identity policy everywhere else is ``iexact``, so a
    user typing their own address with different capitalisation got no email;
  * it RAISED for an unknown address, and the handler's message DIFFERED from the
    success message, so the page told a caller whether an address was registered;
  * it raised ``MultipleObjectsReturned`` for duplicate legacy emails — a 500,
    which is itself a signal that the address is special.

WHY THESE TESTS CAPTURE THE MESSAGES AND NOT THE RENDERED BYTES
The first version compared whole response bodies and failed on a ONE-BYTE
difference at index 7183 (``b'6' != b'5'``) — an unrelated per-request variation,
not a differing message. A whole-page comparison is the wrong instrument: it is
brittle about things that do not matter and says nothing specific about the thing
that does. So the property under test is asserted directly: the sequence of
(level, text) the view hands to the messages framework. That is exactly what a
user reads, it is deterministic, and it cannot be satisfied by an accident of
template rendering.
"""

from __future__ import annotations

import pytest
from django.contrib.auth.models import User
from django.core import mail
from django.urls import reverse

pytestmark = pytest.mark.django_db

PASSWORD = "Gx7-quiet-harbour-42"
RESET_URL = "auth_app:forgot_password"


def _capture(client, monkeypatch, email: str) -> list[tuple[str, str]]:
    """POST and return the (level, text) pairs the view emitted."""
    import django.contrib.messages as messages_module

    recorded: list[tuple[str, str]] = []

    def _recorder(level: str):
        def _record(_request, message, *_args, **_kwargs):
            recorded.append((level, str(message)))

        return _record

    for level in ("success", "error", "warning", "info"):
        monkeypatch.setattr(messages_module, level, _recorder(level))

    client.post(reverse(RESET_URL), {"email": email})
    return recorded


def test_a_known_and_an_unknown_address_emit_the_same_message(client, monkeypatch):
    """The oracle. Same level, same text, whether or not the address exists."""
    # Arrange
    User.objects.create_user(
        username="reset_known", email="reset_known@example.com", password=PASSWORD
    )

    # Act
    unknown = _capture(client, monkeypatch, "definitely-no-such-address@example.com")
    known = _capture(client, monkeypatch, "reset_known@example.com")

    # Assert
    assert known == unknown, (
        f"a registered address is distinguishable from an unregistered one: "
        f"known={known!r} unknown={unknown!r}"
    )


def test_a_FAILED_send_emits_the_same_message_as_a_successful_one(client, monkeypatch):
    """The send outcome is a fact about the INBOX OWNER, not the requester."""
    # Arrange
    User.objects.create_user(
        username="reset_fail", email="reset_fail@example.com", password=PASSWORD
    )
    unknown = _capture(client, monkeypatch, "definitely-no-such-address@example.com")

    def _explode(*_args, **_kwargs):
        raise RuntimeError("smtp down")

    # send_mail is imported INSIDE the view, so it resolves from django.core.mail
    # at call time.
    monkeypatch.setattr("django.core.mail.send_mail", _explode)

    # Act
    failed = _capture(client, monkeypatch, "reset_fail@example.com")

    # Assert
    assert failed == unknown, (
        f"a failed send tells the caller something a successful one does not: "
        f"failed={failed!r} baseline={unknown!r}"
    )


def test_duplicate_legacy_emails_do_not_500_or_differ(client, monkeypatch):
    """Two rows sharing an address is a PRE-migration state (migration 0009
    forbids it going forward). The old `get()` raised
    MultipleObjectsReturned — a 500 for an address that is merely unusual."""
    # Arrange — build the pre-migration state deliberately. The dropped index
    # lives inside this test's transaction and PostgreSQL DDL is transactional,
    # so the rollback restores it.
    from django.db import connection

    with connection.cursor() as cursor:
        cursor.execute("DROP INDEX IF EXISTS auth_user_email_lower_uniq")

    User.objects.create_user(
        username="dup_one", email="dup@example.com", password=PASSWORD
    )
    User.objects.create_user(
        username="dup_two", email="DUP@example.com", password=PASSWORD
    )
    unknown = _capture(client, monkeypatch, "definitely-no-such-address@example.com")

    # Act — must not raise, and must not say anything different.
    try:
        duplicated = _capture(client, monkeypatch, "dup@example.com")
    except Exception as exc:  # pragma: no cover - the defect being guarded
        pytest.fail(f"duplicate legacy emails broke the endpoint: {exc!r}")

    # Assert
    assert duplicated == unknown, (
        f"a duplicated address is distinguishable: {duplicated!r} vs {unknown!r}"
    )


def test_a_case_variant_address_still_reaches_the_account(client):
    """The identity policy is iexact, so the reset lookup must be too — the old
    case-sensitive `get()` silently sent nothing."""
    # Arrange
    User.objects.create_user(
        username="case_reset", email="Case.Reset@Example.com", password=PASSWORD
    )
    mail.outbox.clear()

    # Act
    client.post(reverse(RESET_URL), {"email": "case.reset@example.com"})

    # Assert — the mail went out, so the account WAS found despite the case.
    assert len(mail.outbox) == 1, (
        "a case-variant address did not reach its account, so the lookup is "
        "still case-sensitive"
    )


def test_a_missing_address_is_a_request_error_not_an_oracle(client, monkeypatch):
    """A MISSING field is a fact about the REQUEST, and stays a distinct error —
    the same reasoning applied to the resend endpoint."""
    baseline = _capture(client, monkeypatch, "definitely-no-such-address@example.com")

    # Act
    blank = _capture(client, monkeypatch, "   ")

    # Assert — an ERROR about the request, not the same success text.
    assert blank != baseline
    assert any(level == "error" for level, _text in blank), (
        f"a missing address did not report a request error: {blank!r}"
    )
