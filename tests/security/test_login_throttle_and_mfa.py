"""Failed sign-in throttling and two-factor sign-in, through real requests.

Throttling: repeated wrong passwords lock the (account, client) pair, the
account, and the client address for a window. While locked, even the right
password is refused with the ordinary generic answer.

Two-factor: an account with TOTP is asked for its code after the password;
staff cookie sessions must have a second factor in place and must have
passed it.
"""

from __future__ import annotations

import time

import pytest
from allauth.mfa import app_settings as mfa_settings
from allauth.mfa.totp.internal.auth import (
    TOTP,
    format_hotp_value,
    generate_totp_secret,
    hotp_value,
)
from django.contrib.auth.models import User
from django.test import Client

pytestmark = [pytest.mark.security, pytest.mark.django_db]

PASSWORD = "Correct-Horse-Battery-9"  # pragma: allowlist secret
WRONG = "not-the-password"  # pragma: allowlist secret
SIGNIN = "/auth/signin/"
ATTACKER_IP = "203.0.113.50"
OTHER_IP = "198.51.100.77"
LOCKED_TEXT = "Too many failed sign-in attempts"


@pytest.fixture
def member():
    return User.objects.create_user(
        username="member", email="member@example.org", password=PASSWORD
    )


@pytest.fixture
def staff():
    return User.objects.create_user(
        username="operator",
        email="operator@example.org",
        password=PASSWORD,
        is_staff=True,
    )


def _sign_in(client, username, password, ip=ATTACKER_IP, **extra):
    return client.post(
        SIGNIN, {"username": username, "password": password}, REMOTE_ADDR=ip, **extra
    )


def _signed_in_as(client, user) -> bool:
    return client.session.get("_auth_user_id") == str(user.pk)


def _fail(client, username, times, ip=ATTACKER_IP):
    for _ in range(times):
        _sign_in(client, username, WRONG, ip=ip)


def _enable_totp(user) -> str:
    secret = generate_totp_secret()
    TOTP.activate(user, secret)
    return secret


def _current_code(secret: str) -> str:
    counter = int(time.time() // mfa_settings.TOTP_PERIOD)
    return format_hotp_value(hotp_value(secret, counter))


# -- throttling ------------------------------------------------------------------


def test_right_password_is_refused_after_five_failures(member):
    # Arrange
    client = Client()
    _fail(client, member.username, 5)
    # Act
    _sign_in(client, member.username, PASSWORD)
    # Assert
    assert not _signed_in_as(client, member)


def test_locked_attempt_shows_the_lockout_message(member):
    # Arrange
    client = Client()
    _fail(client, member.username, 5)
    # Act
    response = _sign_in(client, member.username, PASSWORD)
    # Assert
    assert LOCKED_TEXT in response.content.decode()


def test_unknown_account_gets_the_same_lockout_message():
    # Arrange
    client = Client()
    _fail(client, "nobody-here", 5)
    # Act
    response = _sign_in(client, "nobody-here", PASSWORD)
    # Assert
    assert LOCKED_TEXT in response.content.decode()


def test_pair_lock_does_not_block_the_owner_elsewhere(member):
    # Arrange
    _fail(Client(), member.username, 5)
    owner = Client()
    # Act
    _sign_in(owner, member.username, PASSWORD, ip=OTHER_IP)
    # Assert
    assert _signed_in_as(owner, member)


def test_success_resets_the_pair_counter(member):
    # Arrange
    client = Client()
    _fail(client, member.username, 4)
    _sign_in(Client(), member.username, PASSWORD)
    _fail(client, member.username, 4)
    owner = Client()
    # Act
    _sign_in(owner, member.username, PASSWORD)
    # Assert
    assert _signed_in_as(owner, member)


def test_one_address_guessing_many_accounts_is_locked(member, settings):
    # Arrange
    settings.LOGIN_THROTTLE = {**settings.LOGIN_THROTTLE, "ip_limit": 3}
    client = Client()
    for name in ("a1", "a2", "a3"):
        _fail(client, name, 1)
    # Act
    _sign_in(client, member.username, PASSWORD)
    # Assert
    assert not _signed_in_as(client, member)


def test_token_mint_is_refused_while_the_account_is_locked(member):
    # Arrange
    client = Client()
    _fail(client, member.username, 5)
    # Act
    response = client.post(
        "/api/me/token/",
        {"username": member.username, "password": PASSWORD},
        content_type="application/json",
        REMOTE_ADDR=ATTACKER_IP,
    )
    # Assert
    assert response.status_code == 401


def test_password_check_endpoint_is_gone(member):
    # Arrange
    client = Client()
    # Act
    response = client.post(
        "/auth/api/login/",
        {"username": member.username, "password": PASSWORD},
        content_type="application/json",
    )
    # Assert
    assert response.status_code == 404


# -- two-factor sign-in ------------------------------------------------------------


def test_totp_account_is_not_signed_in_by_password_alone(member):
    # Arrange
    _enable_totp(member)
    client = Client()
    # Act
    _sign_in(client, member.username, PASSWORD)
    # Assert
    assert not _signed_in_as(client, member)


def test_totp_account_is_sent_to_the_code_step(member):
    # Arrange
    _enable_totp(member)
    client = Client()
    # Act
    response = _sign_in(client, member.username, PASSWORD)
    # Assert
    assert response["Location"].startswith("/auth/social/2fa/authenticate/")


def test_totp_account_signs_in_with_the_code(member):
    # Arrange
    secret = _enable_totp(member)
    client = Client()
    _sign_in(client, member.username, PASSWORD)
    # Act
    client.post("/auth/social/2fa/authenticate/", {"code": _current_code(secret)})
    # Assert
    assert _signed_in_as(client, member)


# -- staff must use a second factor -------------------------------------------------


@pytest.mark.staff_mfa
def test_staff_without_totp_is_sent_to_setup(staff):
    # Arrange
    client = Client()
    client.force_login(staff)
    # Act
    response = client.get("/accounts/settings/profile/")
    # Assert
    assert response["Location"] == "/auth/social/2fa/totp/activate/"


@pytest.mark.staff_mfa
def test_staff_session_that_skipped_the_code_is_signed_out(staff):
    # Arrange
    _enable_totp(staff)
    client = Client()
    client.force_login(staff)
    # Act
    client.get("/accounts/settings/profile/")
    # Assert
    assert not _signed_in_as(client, staff)


@pytest.mark.staff_mfa
def test_staff_that_passed_the_code_is_let_through(staff):
    # Arrange
    secret = _enable_totp(staff)
    client = Client()
    _sign_in(client, staff.username, PASSWORD)
    client.post("/auth/social/2fa/authenticate/", {"code": _current_code(secret)})
    # Act
    response = client.get("/accounts/settings/profile/")
    # Assert
    assert response.status_code == 200


@pytest.mark.staff_mfa
def test_member_without_totp_is_not_held(member):
    # Arrange
    client = Client()
    client.force_login(member)
    # Act
    response = client.get("/accounts/settings/profile/")
    # Assert
    assert response.status_code == 200
