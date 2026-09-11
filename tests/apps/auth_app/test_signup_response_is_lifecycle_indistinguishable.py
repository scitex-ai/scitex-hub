"""Cross-lifecycle signup-response indistinguishability (PR #775 review, P0).

THE ORACLE THIS CLOSES. Pending identities (live AND expired) returned **HTTP 200
with a rate-limit warning** once the resend budget was exhausted, while active,
split, one-sided and inactive-non-pending collisions returned **302 with the
generic message**. Unifying the message TEXT was not enough: an anonymous caller
could still read the account's lifecycle off the STATUS CODE, and the budget made
the difference reachable by simply repeating the request.

WHAT IS ASSERTED, in two directions.
  1. WITHIN each lifecycle — repeating the POST past any plausible resend budget
     must change nothing. This is what makes the difference reachable, so it is
     asserted rather than assumed.
  2. ACROSS lifecycles — every lifecycle must answer with the SAME status,
     Location, message LEVEL and message BODY. A response that varies by
     lifecycle IS the enumeration oracle.

The captured signature is the complete public response, so a fix that unified the
status but left the message level different would still fail here.
"""

from __future__ import annotations

import threading
from datetime import timedelta

import pytest
from django.contrib.auth.models import User
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from apps.infra.auth_app.models import EmailVerification, PendingSignup
from apps.infra.auth_app.pending_signup import PENDING_SIGNUP_WINDOW

PASSWORD = "TestPass123!"  # pragma: allowlist secret

#: Comfortably past any plausible resend budget, so the exhausted path is
#: genuinely exercised rather than hopefully reached.
REPEATS = 12


def _payload(username: str, email: str) -> dict:
    return {
        "username": username,
        "email": email,
        "password": PASSWORD,
        "password2": PASSWORD,
        "agree_terms": "on",
    }


def _record_messages(monkeypatch) -> list:
    """Capture what each response TELLS the caller, as (level, text) pairs."""
    import django.contrib.messages as messages_module

    recorded: list = []
    lock = threading.Lock()

    def _make(level):
        def _fn(request, message, *args, **kwargs):
            with lock:
                recorded.append((level, str(message)))

        return _fn

    for level in ("debug", "info", "success", "warning", "error"):
        monkeypatch.setattr(messages_module, level, _make(level))
    return recorded


def _pending(email: str, username: str, *, expired: bool):
    user = User.objects.create_user(
        username=username, email=email, password=PASSWORD, is_active=False
    )
    PendingSignup.objects.create(user=user, email=email)
    EmailVerification.objects.create(user=user, email=email)
    if expired:
        User.objects.filter(pk=user.pk).update(
            date_joined=timezone.now() - PENDING_SIGNUP_WINDOW - timedelta(hours=2)
        )
    return user


def _active(email: str, username: str):
    return User.objects.create_user(
        username=username,
        email=email,
        password=PASSWORD,  # is_active=True
    )


def _inactive_not_pending(email: str, username: str):
    return User.objects.create_user(
        username=username, email=email, password=PASSWORD, is_active=False
    )


#: The lifecycles a caller must not be able to tell apart.
LIFECYCLES = {
    "pending_live": lambda email, username: _pending(email, username, expired=False),
    "pending_expired": lambda email, username: _pending(email, username, expired=True),
    "active": _active,
    "inactive_not_pending": _inactive_not_pending,
}


@pytest.mark.django_db(transaction=True)
def test_every_lifecycle_answers_with_the_same_public_response(monkeypatch):
    """One indistinguishable answer, whatever state the address is in."""
    monkeypatch.setattr(
        "apps.infra.project_app.services.email_service.EmailService.send_otp_email",
        staticmethod(lambda **kwargs: (True, "sent")),
    )
    recorded = _record_messages(monkeypatch)

    observed_at = 0
    by_lifecycle: dict[str, list[tuple]] = {}

    for label, build in LIFECYCLES.items():
        username = f"probe-{label}"
        email = f"probe-{label}@example.com"
        build(email, username)

        client = Client()
        signatures = []
        for _ in range(REPEATS):
            response = client.post(
                reverse("auth_app:signup"), _payload(username, email)
            )
            level, text = recorded[observed_at]
            observed_at += 1
            # The Location ECHOES the address the caller just submitted, so the
            # caller's own input is normalised out before comparing: echoing back
            # what you sent is not a leak. Everything else is compared verbatim —
            # status, the rest of the redirect target, message level and message
            # body are all things the caller did NOT supply.
            location = response.get("Location", "").replace(email, "<EMAIL>")
            signatures.append(
                (
                    response.status_code,
                    location,
                    level,
                    text,
                )
            )
        by_lifecycle[label] = signatures

    # 1. WITHIN each lifecycle: repeating past the budget changes NOTHING.
    for label, signatures in by_lifecycle.items():
        distinct = sorted(set(signatures))
        assert len(distinct) == 1, (
            f"{label!r} answered differently across {REPEATS} repeated POSTs, so "
            f"the response changes once the resend budget is spent: {distinct}"
        )

    # 2. ACROSS lifecycles: indistinguishable.
    every = {sig for signatures in by_lifecycle.values() for sig in signatures}
    assert len(every) == 1, (
        "signup answers differently depending on the account's lifecycle, which "
        "lets an anonymous caller read the account state off the response — "
        f"the status/level/body triples observed were: {sorted(every)}"
    )

    # 3. And the shared shape is a redirect carrying one message, not a rendered
    #    page — a rendered 200 was half of the original oracle.
    status, location, level, text = next(iter(every))
    assert status == 302, f"the uniform response is not a redirect: {status}"
    assert location, "the uniform redirect carries no Location"
    assert text, "the uniform response carries no message"
    assert level == "success", f"the uniform message level is {level!r}"
