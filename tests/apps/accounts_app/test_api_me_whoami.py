#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""End-to-end contract tests for ``GET /api/me/`` ("who is this credential").

Card ``hub-api-me-whoami-endpoint-for-api-keys-20260905``. Every test drives
the real URL through the real middleware stack with a real Django ``Client``,
real ``User`` / ``APIKey`` / ``Subscription`` rows and the real migration
executor. **No mocks, no monkeypatch.** The one injected failure (test 9) is
a real authentication backend class activated with ``override_settings`` —
the same mechanism Django itself uses to swap backends.

1.  valid key -> 200, exactly the 7 keys, correct values, key_id set
2.  expired key -> 401 expired
3.  revoked key -> 401 revoked
4.  garbage key -> 401 invalid
5.  anonymous -> 401 missing (positive control: not 200)
6.  session-logged-in user -> 200, key_id null
7.  user with no plan -> "plan" present and null
8.  payload carries no email / secret fields (names or values)
9.  auth backend raising -> 5xx, never 401
10. id is not User.pk and is stable across calls; the 0015-0017 backfill
    gives distinct ids to pre-existing users
"""

from __future__ import annotations

import uuid
from datetime import timedelta

import pytest
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.models import User
from django.core.cache import cache
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import Client, override_settings
from django.utils import timezone

from apps.infra.accounts_app.models import APIKey
from apps.infra.public_app.models import Subscription, SubscriptionPlan

URL = "/api/me/"
RAISING_BACKEND = f"{__name__}.RaisingSessionBackend"
MIGRATE_FROM = [("accounts_app", "0015_userprofile_public_id_nullable")]
MIGRATE_TO = [("accounts_app", "0017_userprofile_public_id_unique")]


class RaisingSessionBackend(ModelBackend):
    """A real auth backend whose session lookup fails like a broken hub would."""

    def get_user(self, user_id):
        raise RuntimeError("simulated hub-side auth backend failure")


@pytest.fixture(autouse=True)
def _clear_rate_limit_cache():
    """/api/me/ is rate-limited per IP; keep buckets from bleeding across tests."""
    cache.clear()
    yield
    cache.clear()


def _user(username: str, **extra) -> User:
    return User.objects.create_user(
        username=username, email=f"{username}@example.com", password="x", **extra
    )


def _bearer(key: str) -> dict:
    return {"HTTP_AUTHORIZATION": f"Bearer {key}"}


def _subscribe(user: User, plan_type: str, period_end_offset: timedelta) -> None:
    plan = SubscriptionPlan.objects.create(
        name=plan_type, plan_type=plan_type, price_monthly=0
    )
    now = timezone.now()
    Subscription.objects.create(
        user=user,
        plan=plan,
        status="active",
        current_period_start=now - timedelta(days=60),
        current_period_end=now + period_end_offset,
    )


# 1 ---------------------------------------------------------------------------
@pytest.mark.django_db
def test_valid_key_returns_exactly_the_seven_keys_with_correct_values():
    # Arrange
    owner = _user("whoami-valid", is_staff=True)
    _subscribe(owner, "premium_a", timedelta(days=29))
    expiry = timezone.now() + timedelta(days=7)
    key_row, full_key = APIKey.create_key(
        user=owner, name="whoami", scopes=["publish"], expires_at=expiry
    )
    expected = {
        "id": str(owner.profile.public_id),
        "username": "whoami-valid",
        "is_staff": True,
        "is_superuser": False,
        "plan": "premium_a",
        "key_id": key_row.id,
        "expires_at": expiry.isoformat(),
    }

    # Act
    response = Client().get(URL, **_bearer(full_key))

    # Assert — dict equality pins both the exact key set and every value
    assert (response.status_code, response.json()) == (200, expected)


# 2 ---------------------------------------------------------------------------
@pytest.mark.django_db
def test_expired_key_is_401_expired():
    # Arrange
    key_row, full_key = APIKey.create_key(user=_user("whoami-expired"), name="k")
    key_row.expires_at = timezone.now() - timedelta(minutes=1)
    key_row.save(update_fields=["expires_at"])

    # Act
    response = Client().get(URL, **_bearer(full_key))

    # Assert
    assert (response.status_code, response.json()) == (401, {"error": "expired"})


# 3 ---------------------------------------------------------------------------
@pytest.mark.django_db
def test_revoked_key_is_401_revoked():
    # Arrange
    key_row, full_key = APIKey.create_key(user=_user("whoami-revoked"), name="k")
    key_row.is_active = False
    key_row.save(update_fields=["is_active"])

    # Act
    response = Client().get(URL, **_bearer(full_key))

    # Assert
    assert (response.status_code, response.json()) == (401, {"error": "revoked"})


# 4 ---------------------------------------------------------------------------
@pytest.mark.django_db
def test_garbage_key_is_401_invalid():
    # Arrange — well-formed prefix, no such row
    garbage = "scitex_" + "f" * 64

    # Act
    response = Client().get(URL, **_bearer(garbage))

    # Assert
    assert (response.status_code, response.json()) == (401, {"error": "invalid"})


# 5 ---------------------------------------------------------------------------
@pytest.mark.django_db
def test_anonymous_request_is_401_missing_not_200():
    # Arrange — no Authorization header, no session cookie
    client = Client()

    # Act
    response = client.get(URL)

    # Assert — positive control: exactly 401 missing, so never a 200
    assert (response.status_code, response.json()) == (401, {"error": "missing"})


# 6 ---------------------------------------------------------------------------
@pytest.mark.django_db
def test_session_logged_in_user_gets_200_with_null_key_fields():
    # Arrange
    user = _user("whoami-session")
    client = Client()
    client.force_login(user)
    expected = {
        "id": str(user.profile.public_id),
        "username": "whoami-session",
        "is_staff": False,
        "is_superuser": False,
        "plan": None,
        "key_id": None,
        "expires_at": None,
    }

    # Act
    response = client.get(URL)

    # Assert
    assert (response.status_code, response.json()) == (200, expected)


# 7 ---------------------------------------------------------------------------
@pytest.mark.django_db
def test_user_without_active_plan_has_plan_key_present_and_null():
    # Arrange — a lapsed subscription is not an active plan
    user = _user("whoami-noplan")
    _subscribe(user, "free", -timedelta(days=30))
    _row, full_key = APIKey.create_key(user=user, name="k")

    # Act
    body = Client().get(URL, **_bearer(full_key)).json()

    # Assert — null is not the same as missing
    assert ("plan" in body, body.get("plan", "MISSING")) == (True, None)


# 8 ---------------------------------------------------------------------------
@pytest.mark.django_db
def test_payload_contains_no_email_or_secret_fields_or_values():
    # Arrange
    user = _user("whoami-nosecret", first_name="Ada", last_name="Lovelace")
    key_row, full_key = APIKey.create_key(user=user, name="k")
    forbidden_names = {
        "email", "name", "display_name", "first_name", "last_name",
        "token", "key", "secret", "key_hash", "key_prefix", "password",
    }
    forbidden_values = [
        user.email, full_key, key_row.key_hash, key_row.key_prefix, "Lovelace",
    ]

    # Act
    response = Client().get(URL, **_bearer(full_key))

    # Assert
    raw = response.content.decode()
    leaked = sorted(forbidden_names & set(response.json())) + [
        v for v in forbidden_values if v in raw
    ]
    assert leaked == []


# 9 ---------------------------------------------------------------------------
@pytest.mark.django_db
def test_auth_backend_raising_is_5xx_not_401():
    # Arrange — a real session whose auth backend blows up on lookup
    user = _user("whoami-broken-backend")
    backends = [RAISING_BACKEND, "django.contrib.auth.backends.ModelBackend"]

    # Act
    with override_settings(AUTHENTICATION_BACKENDS=backends):
        client = Client(raise_request_exception=False)
        client.force_login(user, backend=RAISING_BACKEND)
        response = client.get(URL)

    # Assert — a hub-side failure must never masquerade as a bad credential
    assert 500 <= response.status_code < 600


# 10 --------------------------------------------------------------------------
@pytest.mark.django_db
def test_id_is_opaque_uuid4_not_pk_and_stable_across_calls():
    # Arrange
    user = _user("whoami-stable")
    _row, full_key = APIKey.create_key(user=user, name="k")
    client = Client()

    # Act
    first = client.get(URL, **_bearer(full_key)).json()["id"]
    second = client.get(URL, **_bearer(full_key)).json()["id"]

    # Assert
    assert (first == second, first != str(user.pk), uuid.UUID(first).version) == (
        True,
        True,
        4,
    )


@pytest.fixture
def backfilled_preexisting_profiles(transactional_db):
    """Roll accounts_app back to the nullable column, create two users the way
    they existed before the feature (profile, no public_id), then migrate
    forward through the backfill and the unique step.

    Returns ``(public_ids_before, public_ids_after)``.
    """
    executor = MigrationExecutor(connection)
    executor.migrate(MIGRATE_FROM)
    try:
        old_apps = executor.loader.project_state(MIGRATE_FROM).apps
        OldUser = old_apps.get_model("auth", "User")
        OldProfile = old_apps.get_model("accounts_app", "UserProfile")
        profile_pks = [
            OldProfile.objects.create(
                user=OldUser.objects.create(username=name, password="x")
            ).pk
            for name in ("pre-existing-a", "pre-existing-b")
        ]
        before = list(
            OldProfile.objects.filter(pk__in=profile_pks).values_list(
                "public_id", flat=True
            )
        )
        executor = MigrationExecutor(connection)
        executor.migrate(MIGRATE_TO)
    finally:
        # Always leave the schema at the latest state for the rest of the run.
        executor = MigrationExecutor(connection)
        executor.migrate(executor.loader.graph.leaf_nodes())
    new_apps = executor.loader.project_state(MIGRATE_TO).apps
    NewProfile = new_apps.get_model("accounts_app", "UserProfile")
    after = list(
        NewProfile.objects.filter(pk__in=profile_pks).values_list(
            "public_id", flat=True
        )
    )
    return before, after


def test_public_id_backfill_gives_distinct_ids_to_two_preexisting_users(
    backfilled_preexisting_profiles,
):
    # Arrange
    before, after = backfilled_preexisting_profiles

    # Act
    distinct_non_null_after = {pid for pid in after if pid is not None}

    # Assert — both started NULL; both ended with their own, different uuid
    assert (before, len(after), len(distinct_non_null_after)) == ([None, None], 2, 2)


# EOF
