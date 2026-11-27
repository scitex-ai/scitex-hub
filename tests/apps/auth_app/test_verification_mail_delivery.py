#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""scitex-hub#1234: from 2026-08 on, no prod sign-up was ever verified.

Root cause: prod's SMTP login was refused (SMTP 535), so no verification code
was ever delivered. The signup reply is deliberately the same either way, so
the failure was invisible. These tests guard the three fixes:

  1. ``check_mail_delivery`` / ``probe_mail_backend`` report a refused login
     loudly, WITHOUT sending, and without leaking the account or password.
  2. The verification mail states the expiry the model actually enforces,
     links to the verification page, and no longer threatens deletion.
  3. A pending account that signs in with the RIGHT password is sent back to
     verification with a fresh code, not told "Invalid username or password".

The refusing backend below is a real Django email backend selected through
EMAIL_BACKEND, the same mechanism production uses; nothing is patched.
Disposable addresses only (example.com). No real account is touched.
"""

from __future__ import annotations

import json
import re
import smtplib
from pathlib import Path

import pytest
from django.conf import settings
from django.contrib.auth.models import User
from django.core import mail
from django.core.cache import cache
from django.core.mail.backends.base import BaseEmailBackend
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import override_settings
from django.urls import reverse

from apps.infra.auth_app import pending_signup as ps
from apps.infra.auth_app.mail_health import probe_mail_backend

LOCMEM = "django.core.mail.backends.locmem.EmailBackend"
REFUSING = f"{__name__}.RefusingLoginBackend"
UNREACHABLE = f"{__name__}.UnreachableBackend"
PASSWORD = "Gx7-quiet-harbour-42"  # pragma: allowlist secret


class RefusingLoginBackend(BaseEmailBackend):
    """A server that answers like prod did: 535, with the account in the text."""

    def open(self):
        raise smtplib.SMTPAuthenticationError(535, b"5.7.8 auth failed for secret-user")

    def send_messages(self, email_messages):
        self.open()


class UnreachableBackend(BaseEmailBackend):
    """A server nobody is listening on."""

    def open(self):
        raise ConnectionRefusedError(111, "refused")

    def send_messages(self, email_messages):
        self.open()


# ---------------------------------------------------------------------------
# 1. The probe and the command (no database).
# ---------------------------------------------------------------------------


@pytest.fixture
def refused_probe():
    with override_settings(EMAIL_BACKEND=REFUSING):
        return probe_mail_backend()


@pytest.fixture
def unreachable_probe():
    with override_settings(EMAIL_BACKEND=UNREACHABLE):
        return probe_mail_backend()


def test_probe_reports_a_refused_login_as_failed(refused_probe):
    # Arrange
    probe = refused_probe
    # Act
    ok = probe.ok
    # Assert
    assert ok is False


def test_probe_names_the_login_stage_for_a_refused_login(refused_probe):
    # Arrange
    probe = refused_probe
    # Act
    stage = probe.stage
    # Assert
    assert stage == "login"


def test_probe_reports_the_smtp_code_of_a_refused_login(refused_probe):
    # Arrange
    probe = refused_probe
    # Act
    detail = probe.detail
    # Assert
    assert detail == "SMTP 535"


def test_probe_never_repeats_the_server_text_which_can_name_the_account(refused_probe):
    # Arrange
    probe = refused_probe
    # Act
    summary = probe.summary()
    # Assert
    assert "secret-user" not in summary


def test_probe_reports_an_unreachable_server_at_the_connect_stage(unreachable_probe):
    # Arrange
    probe = unreachable_probe
    # Act
    where = (probe.ok, probe.stage, probe.detail)
    # Assert
    assert where == (False, "connect", "ConnectionRefusedError")


@override_settings(EMAIL_BACKEND=LOCMEM)
def test_probe_passes_for_a_backend_that_cannot_fail():
    # Arrange
    mail.outbox = []
    # Act
    probe = probe_mail_backend()
    # Assert
    assert probe.ok is True


@override_settings(EMAIL_BACKEND=LOCMEM)
def test_command_without_send_to_sends_nothing():
    # Arrange
    mail.outbox = []
    # Act
    call_command("check_mail_delivery")
    # Assert
    assert mail.outbox == []


@override_settings(EMAIL_BACKEND=LOCMEM)
def test_command_send_to_delivers_one_message_to_that_address():
    # Arrange
    mail.outbox = []
    # Act
    call_command("check_mail_delivery", send_to="delivery-check@example.com")
    # Assert
    assert [m.to for m in mail.outbox] == [["delivery-check@example.com"]]


@override_settings(EMAIL_BACKEND=REFUSING)
def test_command_fails_loudly_naming_stage_and_code_when_login_is_refused():
    # Arrange
    command = "check_mail_delivery"
    # Act
    run = lambda: call_command(command)  # noqa: E731
    # Assert
    with pytest.raises(CommandError, match=r"login \(SMTP 535\)"):
        run()


@pytest.fixture
def rebuild_mail_block():
    text = (Path(settings.BASE_DIR) / "scripts/deploy/rebuild.sh").read_text()
    return text.split("7d. Can the deployment send mail?")[1].split(
        "Deployment verification ends"
    )[0]


def test_rebuild_runs_the_mail_check_after_the_swap(rebuild_mail_block):
    # Arrange
    block = rebuild_mail_block
    # Act
    runs = "manage.py check_mail_delivery" in block
    # Assert
    assert runs


def test_rebuild_fails_verification_when_mail_is_refused(rebuild_mail_block):
    # Arrange
    block = rebuild_mail_block
    # Act
    fails = "VERIFY_FAILED=1" in block
    # Assert
    assert fails


# ---------------------------------------------------------------------------
# 2. The verification mail itself (no database).
# ---------------------------------------------------------------------------


@pytest.fixture
def signup_code_mail():
    from apps.infra.project_app.services.email_service import EmailService

    with override_settings(EMAIL_BACKEND=LOCMEM, SITE_URL="https://hub.example.com"):
        mail.outbox = []
        EmailService.send_otp_email(
            email="new.user+x@example.com",
            otp_code="123456",
            verification_type="signup",
        )
        message = mail.outbox[0]
    return message.body, message.alternatives[0][0]


def _verify_link():
    return (
        "https://hub.example.com"
        + reverse("auth_app:verify_email")
        + "?email=new.user%2Bx%40example.com"
    )


def test_signup_code_mail_states_the_expiry_the_model_enforces(signup_code_mail):
    # Arrange
    from apps.infra.auth_app.models import CODE_VALIDITY

    minutes = int(CODE_VALIDITY.total_seconds() // 60)
    # Act
    body, _html = signup_code_mail
    # Assert
    assert f"expires in {minutes} minutes" in body


def test_signup_code_text_mail_links_the_verification_page(signup_code_mail):
    # Arrange
    link = _verify_link()
    # Act
    body, _html = signup_code_mail
    # Assert
    assert link in body


def test_signup_code_html_mail_links_the_verification_page(signup_code_mail):
    # Arrange
    link = _verify_link()
    # Act
    _body, html = signup_code_mail
    # Assert
    assert link in html


def test_signup_code_mail_no_longer_threatens_deletion(signup_code_mail):
    # Arrange: the verification page says unverified signups are kept.
    phrase = "will be deleted"
    # Act
    body, html = signup_code_mail
    # Assert
    assert phrase not in body + html


# ---------------------------------------------------------------------------
# 3. Signing in to a pending account resumes verification (database).
# ---------------------------------------------------------------------------


@pytest.fixture
def pending_user(db):
    from apps.infra.auth_app.models import EmailVerification, PendingSignup

    cache.clear()
    email = "pending_signin@example.com"
    user = User.objects.create_user(
        username="pending_signin", email=email, password=PASSWORD, is_active=False
    )
    PendingSignup.objects.create(user=user, email=email)
    EmailVerification.objects.create(user=user, email=email)
    mail.outbox = []
    return user


def _signin(client, username, password=PASSWORD):
    with override_settings(EMAIL_BACKEND=LOCMEM):
        return client.post(
            reverse("auth_app:signin"), {"username": username, "password": password}
        )


def test_signin_with_the_right_password_redirects_to_verification(client, pending_user):
    # Arrange
    expected = reverse("auth_app:verify_email") + "?email=pending_signin%40example.com"
    # Act
    resp = _signin(client, pending_user.username)
    # Assert
    assert resp["Location"] == expected


def test_signin_with_the_right_password_mails_a_fresh_code(client, pending_user):
    # Arrange
    user = pending_user
    # Act
    _signin(client, user.username)
    # Assert
    assert [m.to for m in mail.outbox] == [[user.email]]


def test_signin_does_not_activate_the_account_by_itself(client, pending_user):
    # Arrange
    user = pending_user
    # Act
    _signin(client, user.username)
    user.refresh_from_db()
    # Assert
    assert user.is_active is False


def test_signin_by_email_address_also_resumes_verification(client, pending_user):
    # Arrange
    user = pending_user
    # Act
    resp = _signin(client, user.email)
    # Assert
    assert resp["Location"].startswith(reverse("auth_app:verify_email"))


def test_signin_with_a_wrong_password_gets_the_generic_error(client, pending_user):
    # Arrange
    user = pending_user
    # Act
    resp = _signin(client, user.username, password="wrong-password")
    # Assert
    assert b"Invalid username or password." in resp.content


def test_signin_with_a_wrong_password_sends_nothing(client, pending_user):
    # Arrange
    user = pending_user
    # Act
    _signin(client, user.username, password="wrong-password")
    # Assert
    assert mail.outbox == []


@pytest.fixture
def disabled_user(db):
    cache.clear()
    mail.outbox = []
    return User.objects.create_user(
        username="disabled_one",
        email="disabled_one@example.com",
        password=PASSWORD,
        is_active=False,
    )


def test_signin_to_an_admin_disabled_account_gets_the_generic_error(
    client, disabled_user
):
    # Arrange: inactive with the right password, but NO pending marker.
    user = disabled_user
    # Act
    resp = _signin(client, user.username)
    # Assert
    assert b"Invalid username or password." in resp.content


def test_signin_to_an_admin_disabled_account_sends_no_code(client, disabled_user):
    # Arrange
    user = disabled_user
    # Act
    _signin(client, user.username)
    # Assert
    assert mail.outbox == []


def test_repeated_signins_stop_mailing_at_the_resend_budget(client, pending_user):
    # Arrange
    attempts = ps.RESENDS_ALLOWED_PER_WINDOW + 2
    # Act
    for _ in range(attempts):
        _signin(client, pending_user.username)
    # Assert
    assert len(mail.outbox) == ps.RESENDS_ALLOWED_PER_WINDOW


def test_the_code_mailed_at_signin_activates_the_account(client, pending_user):
    # Arrange: the whole recovery loop, signin -> mailed code -> verify.
    user = pending_user
    _signin(client, user.username)
    code = re.search(r"\b(\d{6})\b", mail.outbox[0].body).group(1)
    # Act
    client.post(
        reverse("auth_app:api_verify_email"),
        data=json.dumps({"email": user.email, "otp_code": code}),
        content_type="application/json",
    )
    user.refresh_from_db()
    # Assert
    assert user.is_active is True


# ---------------------------------------------------------------------------
# 4. A plus-addressed sign-up reaches a verify page that keeps the "+".
# ---------------------------------------------------------------------------


@pytest.fixture
def plus_signup_response(db, client):
    cache.clear()
    with override_settings(EMAIL_BACKEND=LOCMEM):
        return client.post(
            reverse("auth_app:signup"),
            {
                "username": "plus_probe",
                "email": "plus+tag@example.com",
                "password": PASSWORD,
                "agree_terms": "on",
            },
        )


def test_signup_redirect_url_encodes_a_plus_address(plus_signup_response):
    # Arrange: found on dev, a raw "+" arrived as a space and never verified.
    expected = reverse("auth_app:verify_email") + "?email=plus%2Btag%40example.com"
    # Act
    location = plus_signup_response["Location"]
    # Assert
    assert location == expected
