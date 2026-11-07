"""Scholar's legacy key decorators obey expiry and disabled-owner checks."""

from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.http import JsonResponse
from django.test import RequestFactory
from django.utils import timezone

from apps.infra.accounts_app.models import APIKey
from apps.workspace.scholar_app.api_auth import api_key_optional, require_api_key


@pytest.mark.parametrize(
    ("active", "owner_active", "expiry_days", "expected"),
    [
        (True, True, None, True),
        (True, True, 1, True),
        (True, True, -1, False),
        (False, True, None, False),
        (True, False, None, False),
        (True, False, 1, False),
    ],
)
def test_model_validity(active, owner_active, expiry_days, expected):
    user = get_user_model()(username="local-model-key-owner", is_active=owner_active)
    expiry = (
        None if expiry_days is None else timezone.now() + timedelta(days=expiry_days)
    )
    key = APIKey(user=user, name="model-only", is_active=active, expires_at=expiry)
    assert key.is_valid() is expected


@pytest.fixture
def issued_key(db):
    user = get_user_model()(username="scholar-validity-owner", password="!")
    get_user_model().objects.bulk_create([user])
    key, token = APIKey.create_key(user, "scholar-probe", scopes=["scholar:read"])
    return user, key, token


def _request(token):
    return RequestFactory().get(
        "/scholar-key-probe", HTTP_AUTHORIZATION=f"Bearer {token}"
    )


@require_api_key(scopes=["scholar:read"])
def _required_view(request):
    return JsonResponse({"owner_id": request.api_user.pk})


@api_key_optional
def _optional_view(request):
    return JsonResponse({"key_authenticated": hasattr(request, "api_user")})


def test_scholar_accepts_unexpired_key_without_timestamp_error(issued_key):
    user, key, token = issued_key
    key.expires_at = timezone.now() + timedelta(days=1)
    key.save(update_fields=["expires_at"])
    response = _required_view(_request(token))
    assert response.status_code == 200
    assert str(user.pk).encode() in response.content
    key.refresh_from_db()
    assert key.last_used_at is not None


def test_scholar_rejects_expired_key_without_marking_it_used(issued_key):
    _, key, token = issued_key
    key.expires_at = timezone.now() - timedelta(days=1)
    key.save(update_fields=["expires_at"])
    assert _required_view(_request(token)).status_code == 401
    key.refresh_from_db()
    assert key.last_used_at is None


def test_scholar_decorators_reject_disabled_owner_before_usage_update(issued_key):
    user, key, token = issued_key
    get_user_model().objects.filter(pk=user.pk).update(is_active=False)
    assert _required_view(_request(token)).status_code == 401
    assert _optional_view(_request(token)).content == b'{"key_authenticated": false}'
    key.refresh_from_db()
    assert key.last_used_at is None


@require_api_key(scopes=["scholar:read", "scholar:write"])
def _multi_scope_view(request):
    return JsonResponse({"owner_id": request.api_user.pk})


@pytest.mark.parametrize(
    ("scopes", "expected_status"),
    [
        (["*"], 200),
        (["scholar:read", "scholar:write"], 200),
        (["scholar:read"], 403),
        (["unrelated:read"], 403),
        ([], 403),
    ],
)
def test_scholar_uses_shared_scope_policy_without_recording_denied_keys(
    issued_key, scopes, expected_status
):
    # Arrange
    _, key, token = issued_key
    key.scopes = scopes
    key.save(update_fields=["scopes"])
    # Act
    response = _multi_scope_view(_request(token))
    key.refresh_from_db()
    # Assert
    assert (response.status_code, key.last_used_at is not None) == (
        expected_status,
        expected_status == 200,
    )
