"""The umbrella HTTP MCP endpoint carries host, not per-project, authority."""

import json

import pytest
from asgiref.sync import async_to_sync
from django.contrib.auth import get_user_model
from django.db import connection
from django.utils import timezone

from apps.infra.accounts_app.mcp_authentication import authorize_host_mcp
from apps.infra.accounts_app.models import APIKey


def _key(*, operator=True, active=True, key_active=True, expired=False, scopes=None):
    user = get_user_model()(
        username="test_user_mcp_host",
        password="!",
        is_staff=True,
        is_superuser=operator,
        is_active=active,
    )
    get_user_model().objects.bulk_create([user])
    key, token = APIKey.create_key(
        user,
        "owned-host-key",
        scopes=["mcp"] if scopes is None else scopes,
        expires_at=timezone.now() - timezone.timedelta(days=1) if expired else None,
    )
    if not key_active:
        APIKey.objects.filter(pk=key.pk).update(is_active=False)
    scope = {
        "type": "http",
        "path": "/mcp",
        "headers": [(b"authorization", f"Bearer {token}".encode())],
    }
    return key, scope


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize(
    "options,expected",
    [
        ({"operator": False}, 403),
        ({"operator": False, "scopes": ["*"]}, 403),
        ({"active": False}, 401),
        ({"key_active": False}, 401),
        ({"expired": True}, 401),
        ({"scopes": ["api"]}, 403),
        ({"scopes": []}, 403),
        ({"scopes": ["mcp"]}, 200),
        ({"scopes": ["*"]}, 200),
    ],
)
def test_host_mcp_requires_active_operator_and_key_scope(options, expected):
    key, scope = _key(**options)
    result = async_to_sync(authorize_host_mcp)(scope)
    assert result.status == expected
    key.refresh_from_db()
    assert (key.last_used_at is not None) is (expected == 200)


@pytest.mark.django_db(transaction=True)
def test_authentication_store_failure_returns_503_instead_of_credential_rejection():
    key, scope = _key()
    table = connection.ops.quote_name(APIKey._meta.db_table)
    renamed = connection.ops.quote_name(APIKey._meta.db_table + "_owned_unavailable")
    # A real schema failure in this isolated test database, restored afterward.
    try:
        with connection.cursor() as cursor:
            cursor.execute(f"ALTER TABLE {table} RENAME TO {renamed}")
        result = async_to_sync(authorize_host_mcp)(scope)
    finally:
        with connection.cursor() as cursor:
            cursor.execute(f"ALTER TABLE {renamed} RENAME TO {table}")
    assert result.status == 503
    key.refresh_from_db()
    assert key.last_used_at is None


@pytest.mark.django_db(transaction=True)
def test_http_router_refuses_non_operator_before_starting_mcp():
    import config.asgi as asgi

    _, scope = _key(operator=False)
    messages = []
    previous_lifespan = asgi._mcp_lifespan_task

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message):
        messages.append(message)

    async_to_sync(asgi._http_router)(scope, receive, send)
    assert messages[0]["status"] == 403
    assert "operator" in json.loads(messages[1]["body"])["error"]
    assert asgi._mcp_lifespan_task is previous_lifespan
