"""Account deactivation must apply to every shared API-key consumer."""

import pytest
from django.contrib.auth import get_user_model
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.test import APIRequestFactory

from apps.infra.accounts_app.auth import (
    KEY_INVALID,
    authenticate_api_key,
    resolve_api_key,
)
from apps.infra.accounts_app.authentication import APIKeyAuthentication
from apps.infra.accounts_app.models import APIKey


@pytest.fixture
def issued_key(db):
    # Persist real authentication rows without invoking unrelated OS/Gitea
    # account-provisioning signals.
    user = get_user_model()(username="test_user_key_owner", password="!")
    get_user_model().objects.bulk_create([user])
    key, token = APIKey.create_key(user, "owned-key", scopes=["api"])
    request = APIRequestFactory().get(
        "/owned-key-probe", HTTP_AUTHORIZATION=f"Bearer {token}"
    )
    return user, key, token, request


def test_previously_issued_key_stops_resolving_after_owner_deactivation(issued_key):
    user, _, token, _ = issued_key
    assert resolve_api_key(token)[0] is not None
    get_user_model().objects.filter(pk=user.pk).update(is_active=False)
    assert resolve_api_key(token) == (None, KEY_INVALID)


def test_direct_authentication_rejects_the_disabled_owner(issued_key):
    user, _, _, request = issued_key
    get_user_model().objects.filter(pk=user.pk).update(is_active=False)
    assert authenticate_api_key(request) is None


def test_rejected_owner_does_not_update_key_usage(issued_key):
    user, key, _, request = issued_key
    get_user_model().objects.filter(pk=user.pk).update(is_active=False)
    authenticate_api_key(request)
    key.refresh_from_db()
    assert key.last_used_at is None


def test_drf_rejects_disabled_owner_before_view_permissions(issued_key):
    user, _, _, request = issued_key
    get_user_model().objects.filter(pk=user.pk).update(is_active=False)
    with pytest.raises(AuthenticationFailed):
        APIKeyAuthentication().authenticate(request)


def test_active_owner_keeps_the_same_identity_and_usage_behavior(issued_key):
    user, key, _, request = issued_key
    resolved = authenticate_api_key(request)
    assert resolved.user_id == user.pk
    key.refresh_from_db()
    assert key.last_used_at is not None
