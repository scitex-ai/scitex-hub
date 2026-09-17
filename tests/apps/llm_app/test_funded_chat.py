from __future__ import annotations

import pytest
from django.test import override_settings

from apps.infra.llm_app.funded_chat.config import (
    FundedChatConfigurationError,
    load_funded_chat_config,
)
from apps.infra.llm_app.funded_chat.errors import (
    ERROR_CATEGORIES,
    classify_provider_exception,
    provider_error_payload,
)


class ProviderFailure(Exception):
    def __init__(self, *, status_code=None, retry_after=None):
        super().__init__("SECRET provider detail must never escape")
        self.status_code = status_code
        self.retry_after = retry_after


class AuthenticationError(Exception):
    pass


def test_provider_classifier_maps_only_structural_signals_to_seven_categories():
    cases = [
        (ProviderFailure(status_code=402), "insufficient_balance"),
        (AuthenticationError("SECRET credential"), "provider_auth"),
        (ProviderFailure(status_code=401), "provider_auth"),
        (ProviderFailure(status_code=429, retry_after=37), "rate_limit"),
        (ProviderFailure(status_code=403), "model_unavailable"),
        (ProviderFailure(status_code=404), "model_unavailable"),
        (TimeoutError("SECRET timeout"), "timeout"),
        (ProviderFailure(status_code=503), "provider_outage"),
    ]

    assert ERROR_CATEGORIES == {
        "insufficient_balance",
        "quota_reached",
        "provider_auth",
        "rate_limit",
        "model_unavailable",
        "timeout",
        "provider_outage",
    }
    for exc, category in cases:
        result = classify_provider_exception(exc)
        assert result.category == category
        assert "SECRET" not in repr(result)
        assert "provider detail" not in repr(result)


def test_rate_limit_retry_window_is_bounded_and_sanitized():
    classified = classify_provider_exception(
        ProviderFailure(status_code=429, retry_after="120")
    )
    defaulted = classify_provider_exception(ProviderFailure(status_code=429))

    assert classified.category == "rate_limit"
    assert classified.retry_after_seconds == 120
    assert defaulted.retry_after_seconds == 60
    assert classified.support_id
    assert "SECRET" not in str(classified)


def test_unknown_provider_failure_fails_closed_without_raw_text():
    classified = classify_provider_exception(RuntimeError("sk-secret raw traceback"))

    assert classified.category == "provider_outage"
    assert classified.retry_after_seconds is None
    assert "sk-secret" not in repr(classified)


def test_serialized_provider_error_uses_ui_contract_and_never_raw_exception_text():
    import json

    payload = provider_error_payload(
        AuthenticationError("sk-secret raw traceback"),
        remaining=7,
        reset_at="2026-09-18T00:00:00Z",
        model="deepseek/deepseek-chat",
    )

    assert payload["category"] == "provider_auth"
    assert payload["remaining"] == 7
    assert payload["reset_at"] == "2026-09-18T00:00:00Z"
    assert payload["model"] == "deepseek/deepseek-chat"
    assert payload["error"] == "AI provider request failed"
    assert payload["support_id"]
    assert "sk-secret" not in json.dumps(payload)
    assert "raw traceback" not in json.dumps(payload)


@override_settings(SCITEX_FUNDED_CHAT_ENABLED=False)
def test_disabled_funded_chat_does_not_invent_a_provider_or_model():
    from apps.infra.llm_app.funded_chat.service import (
        FundedChatDenied,
        FundedChatService,
    )

    config = load_funded_chat_config()

    assert config.enabled is False
    assert config.provider == ""
    assert config.model == ""
    with pytest.raises(FundedChatDenied) as denied:
        FundedChatService(config=config).reserve(
            None, idempotency_key="blocked", request_body=b"never sent"
        )
    assert denied.value.category == "provider_outage"


@override_settings(
    SCITEX_FUNDED_CHAT_ENABLED=True,
    SCITEX_FUNDED_CHAT_PROVIDER="deepseek",
    SCITEX_FUNDED_CHAT_MODEL="deepseek-chat",
    SCITEX_FUNDED_CHAT_API_KEY="not-read-by-test",
    SCITEX_FUNDED_CHAT_GLOBAL_DAILY_CAP_USD="5.00",
    SCITEX_FUNDED_CHAT_PROVIDER_DAILY_CAP_USD="3.00",
    SCITEX_FUNDED_CHAT_MAX_REQUEST_COST_USD="0.05",
)
def test_enabled_funded_chat_uses_only_the_explicit_provider_and_model():
    config = load_funded_chat_config()

    assert config.provider == "deepseek"
    assert config.model == "deepseek-chat"
    assert config.litellm_model == "deepseek/deepseek-chat"


@override_settings(
    SCITEX_FUNDED_CHAT_ENABLED=True,
    SCITEX_FUNDED_CHAT_PROVIDER="",
    SCITEX_FUNDED_CHAT_MODEL="",
    SCITEX_FUNDED_CHAT_API_KEY="",
    SCITEX_FUNDED_CHAT_GLOBAL_DAILY_CAP_USD="0",
    SCITEX_FUNDED_CHAT_PROVIDER_DAILY_CAP_USD="0",
)
def test_enabled_funded_chat_fails_closed_when_controls_are_not_explicit():
    with pytest.raises(FundedChatConfigurationError):
        load_funded_chat_config()


@pytest.mark.django_db(transaction=True)
@override_settings(
    SCITEX_FUNDED_CHAT_ENABLED=True,
    SCITEX_FUNDED_CHAT_PROVIDER="deepseek",
    SCITEX_FUNDED_CHAT_MODEL="deepseek-chat",
    SCITEX_FUNDED_CHAT_API_KEY="not-read-by-test",
    SCITEX_FUNDED_CHAT_GLOBAL_DAILY_CAP_USD="5.00",
    SCITEX_FUNDED_CHAT_PROVIDER_DAILY_CAP_USD="3.00",
    SCITEX_FUNDED_CHAT_MAX_REQUEST_COST_USD="0.05",
    SCITEX_FUNDED_CHAT_REQUESTS_PER_MINUTE=100,
)
def test_verified_user_gets_ten_atomic_reservations_and_idempotent_replay():
    from datetime import datetime, timezone

    from django.contrib.auth.models import User

    from apps.infra.auth_app.models import EmailVerification
    from apps.infra.llm_app.funded_chat.service import (
        FundedChatDenied,
        FundedChatService,
    )
    from apps.infra.llm_app.models import FundedChatDailyQuota, FundedChatRequest

    user = User.objects.create_user(
        username="funded", email="funded@example.com", password="unused"
    )
    EmailVerification.objects.create(user=user, email=user.email, is_verified=True)
    service = FundedChatService(
        config=load_funded_chat_config(),
        now=lambda: datetime(2026, 9, 17, 12, 0, tzinfo=timezone.utc),
    )

    first = service.reserve(user, idempotency_key="request-0", request_body=b"hello")
    replay = service.reserve(user, idempotency_key="request-0", request_body=b"hello")
    assert replay.request.pk == first.request.pk
    assert replay.replayed is True

    for number in range(1, 10):
        service.reserve(
            user,
            idempotency_key=f"request-{number}",
            request_body=f"message {number}".encode(),
        )

    with pytest.raises(FundedChatDenied) as denied:
        service.reserve(user, idempotency_key="request-10", request_body=b"eleven")
    assert denied.value.category == "quota_reached"

    quota = FundedChatDailyQuota.objects.get(user=user)
    assert quota.claimed_count == 10
    assert FundedChatRequest.objects.filter(user=user).count() == 10
    snapshot = service.snapshot(user).as_payload()
    assert snapshot == {
        "category": "quota_reached",
        "remaining": 0,
        "reset_at": "2026-09-18T00:00:00Z",
        "model": "deepseek/deepseek-chat",
        "total": 10,
        "state": "exhausted",
    }


@pytest.mark.django_db(transaction=True)
@override_settings(
    SCITEX_FUNDED_CHAT_ENABLED=True,
    SCITEX_FUNDED_CHAT_PROVIDER="deepseek",
    SCITEX_FUNDED_CHAT_MODEL="deepseek-chat",
    SCITEX_FUNDED_CHAT_API_KEY="not-read-by-test",
    SCITEX_FUNDED_CHAT_GLOBAL_DAILY_CAP_USD="0.09",
    SCITEX_FUNDED_CHAT_PROVIDER_DAILY_CAP_USD="3.00",
    SCITEX_FUNDED_CHAT_MAX_REQUEST_COST_USD="0.05",
    SCITEX_FUNDED_CHAT_REQUESTS_PER_MINUTE=100,
)
def test_global_spend_cap_is_reserved_before_a_provider_call_can_start():
    from datetime import datetime, timezone
    from decimal import Decimal

    from django.contrib.auth.models import User

    from apps.infra.auth_app.models import EmailVerification
    from apps.infra.llm_app.funded_chat.service import (
        FundedChatDenied,
        FundedChatService,
    )
    from apps.infra.llm_app.models import FundedChatDailySpend, FundedChatRequest

    users = [
        User.objects.create_user(
            username=f"cap-{number}",
            email=f"cap-{number}@example.com",
            password="unused",
        )
        for number in range(2)
    ]
    for user in users:
        EmailVerification.objects.create(user=user, email=user.email, is_verified=True)
    service = FundedChatService(
        config=load_funded_chat_config(),
        now=lambda: datetime(2026, 9, 17, 12, 0, tzinfo=timezone.utc),
    )

    service.reserve(users[0], idempotency_key="cap-one", request_body=b"one")
    with pytest.raises(FundedChatDenied) as denied:
        service.reserve(users[1], idempotency_key="cap-two", request_body=b"two")

    assert denied.value.category == "insufficient_balance"
    assert FundedChatRequest.objects.count() == 1
    spend = FundedChatDailySpend.objects.get(scope=FundedChatDailySpend.GLOBAL_SCOPE)
    assert spend.reserved_subsidy_usd == Decimal("0.050000")


@pytest.mark.django_db(transaction=True)
@override_settings(
    SCITEX_FUNDED_CHAT_ENABLED=True,
    SCITEX_FUNDED_CHAT_PROVIDER="deepseek",
    SCITEX_FUNDED_CHAT_MODEL="deepseek-chat",
    SCITEX_FUNDED_CHAT_API_KEY="not-read-by-test",
    SCITEX_FUNDED_CHAT_GLOBAL_DAILY_CAP_USD="5.00",
    SCITEX_FUNDED_CHAT_PROVIDER_DAILY_CAP_USD="3.00",
    SCITEX_FUNDED_CHAT_MAX_REQUEST_COST_USD="0.05",
    SCITEX_FUNDED_CHAT_REQUESTS_PER_MINUTE=100,
)
def test_execute_records_provider_and_subsidy_cost_separately_and_replays_once():
    from datetime import datetime, timezone
    from decimal import Decimal

    from django.contrib.auth.models import User

    from apps.infra.auth_app.models import EmailVerification
    from apps.infra.llm_app.funded_chat.service import (
        FundedChatService,
        ProviderResult,
    )
    from apps.infra.llm_app.models import FundedChatDailySpend, FundedChatRequest

    user = User.objects.create_user(
        username="accounted", email="accounted@example.com", password="unused"
    )
    EmailVerification.objects.create(user=user, email=user.email, is_verified=True)
    service = FundedChatService(
        config=load_funded_chat_config(),
        now=lambda: datetime(2026, 9, 17, 12, 0, tzinfo=timezone.utc),
    )
    calls = []

    def provider_call(config, request_body):
        calls.append((config.litellm_model, request_body))
        return ProviderResult(
            text="answer",
            prompt_tokens=11,
            completion_tokens=7,
            provider_cost_usd=Decimal("0.012345"),
        )

    first = service.execute(
        user,
        idempotency_key="same-request",
        request_body=b"question",
        provider_call=provider_call,
    )
    replay = service.execute(
        user,
        idempotency_key="same-request",
        request_body=b"question",
        provider_call=provider_call,
    )

    assert first == replay
    assert first.text == "answer"
    assert len(calls) == 1
    request = FundedChatRequest.objects.get(user=user)
    assert request.provider_cost_usd == Decimal("0.012345")
    assert request.subsidy_cost_usd == Decimal("0.012345")
    assert request.provider_prompt_tokens == 11
    assert request.provider_completion_tokens == 7
    global_spend = FundedChatDailySpend.objects.get(
        day=request.day, scope=FundedChatDailySpend.GLOBAL_SCOPE
    )
    assert global_spend.provider_cost_usd == Decimal("0.012345")
    assert global_spend.subsidy_cost_usd == Decimal("0.012345")
    assert global_spend.reserved_subsidy_usd == Decimal("0")


@pytest.mark.django_db(transaction=True)
@override_settings(
    SCITEX_FUNDED_CHAT_ENABLED=True,
    SCITEX_FUNDED_CHAT_PROVIDER="deepseek",
    SCITEX_FUNDED_CHAT_MODEL="deepseek-chat",
    SCITEX_FUNDED_CHAT_API_KEY="not-read-by-test",
    SCITEX_FUNDED_CHAT_GLOBAL_DAILY_CAP_USD="5.00",
    SCITEX_FUNDED_CHAT_PROVIDER_DAILY_CAP_USD="3.00",
    SCITEX_FUNDED_CHAT_MAX_REQUEST_COST_USD="0.05",
    SCITEX_FUNDED_CHAT_REQUESTS_PER_MINUTE=100,
)
def test_provider_failure_releases_quota_and_persists_only_sanitized_classification():
    from datetime import datetime, timezone

    from django.contrib.auth.models import User

    from apps.infra.auth_app.models import EmailVerification
    from apps.infra.llm_app.funded_chat.service import (
        FundedChatDenied,
        FundedChatService,
    )
    from apps.infra.llm_app.models import FundedChatDailyQuota, FundedChatRequest

    user = User.objects.create_user(
        username="failure", email="failure@example.com", password="unused"
    )
    EmailVerification.objects.create(user=user, email=user.email, is_verified=True)
    service = FundedChatService(
        config=load_funded_chat_config(),
        now=lambda: datetime(2026, 9, 17, 12, 0, tzinfo=timezone.utc),
    )

    def provider_call(config, request_body):
        raise ProviderFailure(status_code=429, retry_after=29)

    with pytest.raises(FundedChatDenied) as denied:
        service.execute(
            user,
            idempotency_key="failed-request",
            request_body=b"question",
            provider_call=provider_call,
        )

    assert denied.value.category == "rate_limit"
    assert denied.value.retry_after_seconds == 29
    request = FundedChatRequest.objects.get(user=user)
    assert request.status == FundedChatRequest.STATUS_FAILED
    assert request.error_category == "rate_limit"
    assert "SECRET" not in request.error_category
    assert FundedChatDailyQuota.objects.get(user=user).claimed_count == 0


@pytest.mark.django_db(transaction=True)
@override_settings(
    SCITEX_FUNDED_CHAT_ENABLED=True,
    SCITEX_FUNDED_CHAT_PROVIDER="deepseek",
    SCITEX_FUNDED_CHAT_MODEL="deepseek-chat",
    SCITEX_FUNDED_CHAT_API_KEY="not-read-by-test",
    SCITEX_FUNDED_CHAT_GLOBAL_DAILY_CAP_USD="5.00",
    SCITEX_FUNDED_CHAT_PROVIDER_DAILY_CAP_USD="3.00",
    SCITEX_FUNDED_CHAT_MAX_REQUEST_COST_USD="0.05",
    SCITEX_FUNDED_CHAT_REQUESTS_PER_MINUTE=100,
)
def test_parallel_distinct_requests_cannot_claim_more_than_ten():
    from concurrent.futures import ThreadPoolExecutor
    from datetime import datetime, timezone

    from django.contrib.auth.models import User
    from django.db import close_old_connections

    from apps.infra.auth_app.models import EmailVerification
    from apps.infra.llm_app.funded_chat.service import (
        FundedChatDenied,
        FundedChatService,
    )
    from apps.infra.llm_app.models import FundedChatDailyQuota

    user = User.objects.create_user(
        username="parallel", email="parallel@example.com", password="unused"
    )
    EmailVerification.objects.create(user=user, email=user.email, is_verified=True)
    config = load_funded_chat_config()

    def claim(number):
        close_old_connections()
        thread_user = User.objects.get(pk=user.pk)
        service = FundedChatService(
            config=config,
            now=lambda: datetime(2026, 9, 17, 12, 0, tzinfo=timezone.utc),
        )
        try:
            service.reserve(
                thread_user,
                idempotency_key=f"parallel-{number}",
                request_body=f"message-{number}".encode(),
            )
            return "claimed"
        except FundedChatDenied as exc:
            return exc.category
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=12) as executor:
        outcomes = list(executor.map(claim, range(12)))

    assert outcomes.count("claimed") == 10
    assert outcomes.count("quota_reached") == 2
    assert FundedChatDailyQuota.objects.get(user=user).claimed_count == 10


def test_provider_adapter_uses_exact_configured_model_without_fallback(monkeypatch):
    import json
    from decimal import Decimal
    from types import SimpleNamespace

    import litellm

    from apps.infra.llm_app.funded_chat.provider import litellm_provider_call

    calls = []
    response = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content="answer"))],
        usage=SimpleNamespace(prompt_tokens=3, completion_tokens=4),
    )

    def completion(**kwargs):
        calls.append(kwargs)
        return response

    monkeypatch.setattr(litellm, "completion", completion)
    monkeypatch.setattr(litellm, "completion_cost", lambda **kwargs: 0.001)
    monkeypatch.setattr(litellm, "token_counter", lambda **kwargs: 3)
    monkeypatch.setattr(litellm, "cost_per_token", lambda **kwargs: (0.0004, 0.0006))
    with override_settings(
        SCITEX_FUNDED_CHAT_ENABLED=True,
        SCITEX_FUNDED_CHAT_PROVIDER="deepseek",
        SCITEX_FUNDED_CHAT_MODEL="deepseek-chat",
        SCITEX_FUNDED_CHAT_API_KEY="not-read-by-test",
        SCITEX_FUNDED_CHAT_GLOBAL_DAILY_CAP_USD="5.00",
        SCITEX_FUNDED_CHAT_PROVIDER_DAILY_CAP_USD="3.00",
        SCITEX_FUNDED_CHAT_MAX_REQUEST_COST_USD="0.05",
    ):
        config = load_funded_chat_config()
        result = litellm_provider_call(
            config,
            json.dumps({"messages": [{"role": "user", "content": "hi"}]}).encode(),
        )

    assert result.text == "answer"
    assert result.provider_cost_usd == Decimal("0.001")
    assert [call["model"] for call in calls] == ["deepseek/deepseek-chat"]
    assert "fallbacks" not in calls[0]


def test_provider_adapter_refuses_a_call_above_the_reserved_cost(monkeypatch):
    import json

    import litellm

    from apps.infra.llm_app.funded_chat.provider import (
        ProviderBudgetEstimateError,
        litellm_provider_call,
    )

    calls = []
    monkeypatch.setattr(litellm, "completion", lambda **kwargs: calls.append(kwargs))
    monkeypatch.setattr(litellm, "token_counter", lambda **kwargs: 10_000)
    monkeypatch.setattr(litellm, "cost_per_token", lambda **kwargs: (0.04, 0.02))
    with override_settings(
        SCITEX_FUNDED_CHAT_ENABLED=True,
        SCITEX_FUNDED_CHAT_PROVIDER="deepseek",
        SCITEX_FUNDED_CHAT_MODEL="deepseek-chat",
        SCITEX_FUNDED_CHAT_API_KEY="not-read-by-test",
        SCITEX_FUNDED_CHAT_GLOBAL_DAILY_CAP_USD="5.00",
        SCITEX_FUNDED_CHAT_PROVIDER_DAILY_CAP_USD="3.00",
        SCITEX_FUNDED_CHAT_MAX_REQUEST_COST_USD="0.05",
    ):
        with pytest.raises(ProviderBudgetEstimateError):
            litellm_provider_call(
                load_funded_chat_config(),
                json.dumps(
                    {"messages": [{"role": "user", "content": "expensive"}]}
                ).encode(),
            )

    assert calls == []


@override_settings(
    SCITEX_FUNDED_CHAT_ENABLED=True,
    SCITEX_FUNDED_CHAT_PROVIDER="",
    SCITEX_FUNDED_CHAT_MODEL="",
    SCITEX_FUNDED_CHAT_API_KEY="",
    SCITEX_FUNDED_CHAT_GLOBAL_DAILY_CAP_USD="0",
    SCITEX_FUNDED_CHAT_PROVIDER_DAILY_CAP_USD="0",
)
def test_django_system_check_blocks_unsafe_enabled_configuration():
    from apps.infra.llm_app.checks import check_funded_chat_configuration

    errors = check_funded_chat_configuration(None)

    assert [error.id for error in errors] == ["llm_app.E002"]
    assert "API key" not in errors[0].msg


def test_allowance_read_endpoint_has_a_stable_named_route():
    from django.urls import reverse

    assert reverse("llm_app:api_funded_chat_allowance") == (
        "/apps/llm/api/chat/funded-allowance/"
    )


def test_chat_endpoints_never_serialize_provider_exception_text():
    import inspect

    from apps.infra.llm_app.services.llm_service import UserLLMService
    from apps.infra.llm_app.views.chat import api_chat, api_chat_stream
    from apps.infra.llm_app.views.providers import api_test_provider

    source = (
        inspect.getsource(api_chat)
        + inspect.getsource(api_chat_stream)
        + inspect.getsource(api_test_provider)
        + inspect.getsource(UserLLMService.complete)
        + inspect.getsource(UserLLMService.complete_with_tools)
        + inspect.getsource(UserLLMService.complete_with_tools_streaming)
    )
    assert '"error": str(e)' not in source
    assert "error_message=str(e)" not in source
    assert "Connection test failed" not in source
    assert "Campaign chat failed: {e}" not in source
    assert "AI request failed: {e}" not in source
