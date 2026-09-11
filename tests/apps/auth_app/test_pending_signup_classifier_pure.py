#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The pending-signup CLASSIFIER, without a database.

SECURITY HOLD on PR #775. The takeover was a classification bug: a one-sided
collision returned the matched row as if the submitter owned it. The end-to-end
regression suite (test_pending_signup_takeover_regression.py) needs postgres;
this file does not, because it stubs the two lookup helpers and asserts the
DECISION.

Why this file exists separately: that suite carries a module-level
``pytestmark = pytest.mark.django_db``, so it errors wholesale in an
environment without postgres — which means the classifier's behaviour, the
thing that actually broke, would be unverifiable exactly where the fix was
written. Nobody needs a database to answer "does a one-sided match name a row?"
"""

from __future__ import annotations

from datetime import timedelta

from django.utils import timezone

from apps.infra.auth_app import pending_signup as ps

ATTACKER_EMAIL = "attacker@evil.example"


class _Row:
    """Stand-in for a User row: only the attributes the classifier reads."""

    def __init__(self, pk, *, email, username, is_active=False, age=timedelta(0)):
        self.pk = pk
        self.email = email
        self.username = username
        self.is_active = is_active
        self.date_joined = timezone.now() - age


def _stub(monkeypatch, *, by_email=None, by_username=None):
    monkeypatch.setattr(ps, "_by_email", lambda _email: by_email)
    monkeypatch.setattr(ps, "_by_username", lambda _username: by_username)


# ---------------------------------------------------------------------------
# The attack: exactly ONE of the submitted values matches.
# ---------------------------------------------------------------------------


def test_username_only_match_names_no_user(monkeypatch):
    # Arrange — the victim's row, and an attacker who knows only the username.
    victim = _Row(1, email="victim@example.com", username="victim_pending")
    _stub(monkeypatch, by_email=None, by_username=victim)

    # Act
    collision, found = ps.classify_pending_signup(ATTACKER_EMAIL, "victim_pending")

    # Assert — this is the takeover's exact precondition, now refused.
    assert collision is ps.SignupCollision.ONE_SIDED
    assert found is None


def test_username_only_match_names_no_user_even_when_the_row_is_expired(monkeypatch):
    # Arrange — past the window the old code also DELETED the victim's row.
    victim = _Row(
        1,
        email="victim@example.com",
        username="victim_pending",
        age=ps.PENDING_SIGNUP_WINDOW + timedelta(hours=3),
    )
    _stub(monkeypatch, by_email=None, by_username=victim)

    # Act
    collision, found = ps.classify_pending_signup(ATTACKER_EMAIL, "victim_pending")

    # Assert — expired does not make a one-sided match any more trustworthy.
    assert collision is ps.SignupCollision.ONE_SIDED
    assert found is None


def test_email_only_match_names_no_user(monkeypatch):
    # Arrange — the mirror: the attacker knows only the email.
    victim = _Row(1, email="victim@example.com", username="victim_pending")
    _stub(monkeypatch, by_email=victim, by_username=None)

    # Act
    collision, found = ps.classify_pending_signup(
        "victim@example.com", "attacker_chosen"
    )

    # Assert
    assert collision is ps.SignupCollision.ONE_SIDED
    assert found is None


def test_crossed_rows_name_no_user(monkeypatch):
    # Arrange — two different rows, one per submitted value.
    row_a = _Row(1, email="a@example.com", username="row_a")
    row_b = _Row(2, email="b@example.com", username="row_b")
    _stub(monkeypatch, by_email=row_a, by_username=row_b)

    # Act
    collision, found = ps.classify_pending_signup("a@example.com", "row_b")

    # Assert
    assert collision is ps.SignupCollision.SPLIT
    assert found is None


def test_an_active_row_reached_one_sidedly_names_no_user(monkeypatch):
    # Arrange — the winning move if it worked: mint a code for a live account.
    active = _Row(
        1, email="victim@example.com", username="victim_pending", is_active=True
    )
    _stub(monkeypatch, by_email=None, by_username=active)

    # Act
    collision, found = ps.classify_pending_signup(ATTACKER_EMAIL, "victim_pending")

    # Assert
    assert collision is ps.SignupCollision.ONE_SIDED
    assert found is None


# ---------------------------------------------------------------------------
# POSITIVE CONTROL: the legitimate path must survive the fix.
# ---------------------------------------------------------------------------


def test_the_exact_pair_still_names_the_row(monkeypatch):
    # Arrange — the same row holds BOTH submitted values.
    victim = _Row(1, email="victim@example.com", username="victim_pending")
    _stub(monkeypatch, by_email=victim, by_username=victim)

    # Act
    collision, found = ps.classify_pending_signup(
        "victim@example.com", "victim_pending"
    )

    # Assert
    assert collision is ps.SignupCollision.PENDING_LIVE
    assert found is victim


def test_the_exact_pair_still_expires(monkeypatch):
    # Arrange
    victim = _Row(
        1,
        email="victim@example.com",
        username="victim_pending",
        age=ps.PENDING_SIGNUP_WINDOW + timedelta(hours=3),
    )
    _stub(monkeypatch, by_email=victim, by_username=victim)

    # Act
    collision, found = ps.classify_pending_signup(
        "victim@example.com", "victim_pending"
    )

    # Assert — resume is still reachable, which is the feature the fix must not
    # have destroyed: a fix that refuses everything would pass the attacks too.
    assert collision is ps.SignupCollision.PENDING_EXPIRED
    assert found is victim


def test_the_exact_pair_of_an_active_account_is_still_active(monkeypatch):
    # Arrange
    active = _Row(
        1, email="victim@example.com", username="victim_pending", is_active=True
    )
    _stub(monkeypatch, by_email=active, by_username=active)

    # Act
    collision, found = ps.classify_pending_signup(
        "victim@example.com", "victim_pending"
    )

    # Assert
    assert collision is ps.SignupCollision.ACTIVE
    assert found is active


def test_nothing_matching_is_still_a_fresh_signup(monkeypatch):
    # Arrange
    _stub(monkeypatch, by_email=None, by_username=None)

    # Act
    collision, found = ps.classify_pending_signup("nobody@example.com", "nobody")

    # Assert
    assert collision is ps.SignupCollision.NONE
    assert found is None


# ---------------------------------------------------------------------------
# The request-level tests must actually REACH the branches they claim to test.
# ---------------------------------------------------------------------------


def test_no_test_posts_a_field_the_signup_form_ignores():
    """PR #775 re-review blocker 5.

    The request tests posted ``confirm_password`` while ``SignupForm`` expects
    ``password2``. The extra key is ignored and the REQUIRED one is missing, so
    every such POST re-rendered the form with a 200 and the 302 assertions were
    never reached — a test that exercises nothing proves nothing, and a fix's
    safety must not rest on one.
    """
    import pathlib

    here = pathlib.Path(__file__).parent
    for name in (
        "test_pending_signup_lifecycle.py",
        "test_pending_signup_takeover_regression.py",
    ):
        text = (here / name).read_text(encoding="utf-8")
        # Matches the KEY, not the bare word: both files contain explanatory
        # comments quoting the wrong name, and a guard that trips on its own
        # documentation is a false alarm rather than a catch.
        assert '"confirm_password":' not in text, (
            f"{name} posts a key SignupForm does not read, so its payload is "
            "form-invalid and its assertions are never reached"
        )


def test_the_signup_form_expects_password2():
    # Arrange
    from apps.infra.auth_app.forms import SignupForm

    # Act
    names = set(SignupForm.base_fields)

    # Assert
    assert "password2" in names
    assert "confirm_password" not in names


def test_the_request_payload_shape_is_actually_form_valid():
    """Runs the validator rather than restating its field list."""
    # Arrange
    from apps.infra.auth_app.forms import SignupForm

    form = SignupForm(
        data={
            "username": "payload_probe",
            "email": "payload_probe@example.com",
            "password": "Gx7-quiet-harbour-42",
            "password2": "Gx7-quiet-harbour-42",
            "agree_terms": "on",
        }
    )

    # Act / Assert — if this fails, every 302 assertion in the suite is dead.
    assert form.is_valid(), form.errors


def test_verification_codes_come_from_the_csprng_not_random():
    """PR #775 re-review blocker 2.

    ``random.choices`` is a Mersenne Twister: deterministic from its state, and
    a handful of observed outputs is enough to reconstruct that state. An OTP is
    a bearer credential, so it must come from the CSPRNG.
    """
    import pathlib

    from apps.infra.auth_app import models as auth_models

    # Arrange
    source = pathlib.Path(auth_models.__file__).read_text(encoding="utf-8")
    start = source.index("def generate_code")

    # Act
    body = source[start : start + 700]

    # Assert
    assert "secrets.choice" in body
    assert "random.choices" not in body


def test_a_generated_code_is_six_digits():
    # Arrange
    from apps.infra.auth_app.models import EmailVerification

    # Act / Assert
    for _ in range(25):
        code = EmailVerification.generate_code()
        assert len(code) == 6
        assert code.isdigit()


def test_the_code_validity_used_in_the_message_is_the_models_own():
    """PR #775 re-review blocker 3: the response promised 60 minutes while the
    model enforced 10. The message is now DERIVED, so this asserts the
    derivation rather than a retyped number."""
    # Arrange
    from apps.infra.auth_app.models import CODE_VALIDITY
    from apps.infra.auth_app.views import authentication

    # Act
    expected = int(CODE_VALIDITY.total_seconds() // 60)

    # Assert
    assert expected == 10
    assert f"valid for {expected} minutes" in authentication._SIGNUP_RESPONSE_MESSAGE
    assert "60 minutes" not in authentication._SIGNUP_RESPONSE_MESSAGE
