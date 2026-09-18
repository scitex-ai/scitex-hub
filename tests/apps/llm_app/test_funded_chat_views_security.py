from __future__ import annotations

import json
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from django.contrib.auth.models import User
from django.test import Client, override_settings
from django.urls import reverse

from apps.infra.llm_app.funded_chat.service import ProviderResult

FUNDED_SETTINGS = {
    "SCITEX_FUNDED_CHAT_ENABLED": True,
    "SCITEX_FUNDED_CHAT_PROVIDER": "deepseek",
    "SCITEX_FUNDED_CHAT_MODEL": "deepseek-chat",
    "SCITEX_FUNDED_CHAT_API_KEY": "not-read-by-test",
    "SCITEX_FUNDED_CHAT_GLOBAL_DAILY_CAP_USD": "5",
    "SCITEX_FUNDED_CHAT_PROVIDER_DAILY_CAP_USD": "3",
    "SCITEX_FUNDED_CHAT_MAX_REQUEST_COST_USD": "0.05",
}


@pytest.mark.django_db
@pytest.mark.parametrize("route", ["llm_app:api_chat", "llm_app:api_chat_stream"])
def test_chat_routes_require_authentication(route):
    response = Client().post(
        reverse(route),
        data=json.dumps({"prompt": "hello"}),
        content_type="application/json",
    )

    assert response.status_code == 302
    assert "/auth/login/" in response.url


@pytest.mark.django_db
@pytest.mark.parametrize("route", ["llm_app:api_chat", "llm_app:api_chat_stream"])
def test_chat_routes_enforce_csrf(route):
    user = User.objects.create_user("csrf-user", password="unused")
    client = Client(enforce_csrf_checks=True)
    client.force_login(user)

    response = client.post(
        reverse(route),
        data=json.dumps({"prompt": "hello"}),
        content_type="application/json",
    )

    assert response.status_code == 403


@pytest.mark.django_db(transaction=True)
@override_settings(**FUNDED_SETTINGS)
def test_no_byok_request_uses_authenticated_tenant_and_ignores_client_billing_fields():
    user = User.objects.create_user("tenant-a", password="unused")
    captured = {}

    def execute(tenant, messages, idempotency_key):
        captured.update(
            tenant=tenant,
            messages=messages,
            idempotency_key=idempotency_key,
        )
        return ProviderResult(
            text="answer",
            prompt_tokens=1,
            completion_tokens=1,
            provider_cost_usd=Decimal("0.01"),
        )

    client = Client()
    client.force_login(user)
    fake_service = SimpleNamespace(connection=None, llm_connection=None)
    with (
        patch(
            "apps.infra.llm_app.views.chat.UserLLMService", return_value=fake_service
        ),
        patch(
            "apps.infra.llm_app.views.chat._build_system_prompt",
            return_value="server system prompt",
        ),
        patch(
            "apps.infra.llm_app.views.chat._inject_project_root",
            new=AsyncMock(return_value="server system prompt"),
        ),
        patch(
            "apps.infra.llm_app.views.chat._execute_funded_chat", side_effect=execute
        ),
    ):
        response = client.post(
            reverse("llm_app:api_chat"),
            data=json.dumps(
                {
                    "prompt": "hello",
                    "provider": "attacker",
                    "model": "attacker/model",
                    "cost": "0",
                }
            ),
            content_type="application/json",
            HTTP_IDEMPOTENCY_KEY="stable-key",
        )

    assert response.status_code == 200
    assert response.json()["text"] == "answer"
    assert captured["tenant"].pk == user.pk
    assert captured["idempotency_key"] == "stable-key"
    serialized = json.dumps(captured["messages"])
    assert "attacker" not in serialized
    assert '"cost"' not in serialized


@pytest.mark.django_db
@override_settings(**FUNDED_SETTINGS)
def test_chat_rejects_large_body_before_provider_resolution():
    user = User.objects.create_user("large-body", password="unused")
    client = Client()
    client.force_login(user)

    with patch("apps.infra.llm_app.views.chat.UserLLMService") as service:
        response = client.post(
            reverse("llm_app:api_chat"),
            data=b"x" * 131_073,
            content_type="application/json",
        )

    assert response.status_code == 413
    service.assert_not_called()
