from __future__ import annotations

import json
from decimal import Decimal, InvalidOperation

from .config import FundedChatConfig, FundedChatConfigurationError, quantize_money
from .service import ProviderResult


class ProviderPreDispatchError(Exception):
    """A validated failure that happened before any provider request was sent."""

    definitely_not_dispatched = True
    status_code: int | None = None
    retry_after: int | None = None


class ProviderBudgetEstimateError(ProviderPreDispatchError):
    """The configured model's worst-case cost exceeds its reservation."""

    status_code = 402


class ProviderAccountingError(Exception):
    """The provider responded but did not return trustworthy accounting."""


def _content_size(value) -> int:
    if isinstance(value, str):
        return len(value)
    if isinstance(value, list):
        return sum(_content_size(item) for item in value)
    if isinstance(value, dict):
        return sum(len(str(key)) + _content_size(item) for key, item in value.items())
    if value is None or isinstance(value, (bool, int, float)):
        return len(str(value))
    raise ProviderPreDispatchError("unsupported message content")


def _validated_messages(config: FundedChatConfig, request_body: bytes) -> list[dict]:
    if (
        not isinstance(request_body, bytes)
        or len(request_body) > config.max_request_bytes
    ):
        raise ProviderPreDispatchError("request body exceeds the configured bound")
    try:
        payload = json.loads(request_body)
    except (json.JSONDecodeError, UnicodeDecodeError, TypeError) as exc:
        raise ProviderPreDispatchError("request body must be JSON") from exc
    if not isinstance(payload, dict) or set(payload) != {"messages"}:
        raise ProviderPreDispatchError("only server-built messages are accepted")
    messages = payload["messages"]
    if (
        not isinstance(messages, list)
        or not messages
        or len(messages) > config.max_messages
    ):
        raise ProviderPreDispatchError("messages exceed the configured bound")
    total_chars = 0
    for message in messages:
        if not isinstance(message, dict):
            raise ProviderPreDispatchError("message must be an object")
        if message.get("role") not in {"system", "user", "assistant", "tool"}:
            raise ProviderPreDispatchError("message role is invalid")
        if "content" not in message:
            raise ProviderPreDispatchError("message content is required")
        total_chars += _content_size(message["content"])
        if total_chars > config.max_message_chars:
            raise ProviderPreDispatchError(
                "message content exceeds the configured bound"
            )
    return messages


def _pre_dispatch_money(value, *, name: str) -> Decimal:
    try:
        return quantize_money(Decimal(str(value)), name=name)
    except (
        FundedChatConfigurationError,
        InvalidOperation,
        TypeError,
        ValueError,
    ) as exc:
        raise ProviderPreDispatchError("provider estimate is invalid") from exc


def _actual_money(value) -> Decimal:
    try:
        return quantize_money(Decimal(str(value)), name="provider actual cost")
    except (
        FundedChatConfigurationError,
        InvalidOperation,
        TypeError,
        ValueError,
    ) as exc:
        raise ProviderAccountingError("provider accounting is invalid") from exc


def litellm_provider_call(
    config: FundedChatConfig,
    request_body: bytes,
    _dispatch_key: str = "",
) -> ProviderResult:
    """Call the allowlisted model once with bounded work and no fallbacks.

    ``_dispatch_key`` is the service's internal durable identity only. The
    configured providers do not document request idempotency for chat
    completions, so it is deliberately never forwarded to LiteLLM or the wire.
    Validation and token counting happen before dispatch. Once ``completion`` is
    invoked, failures are intentionally not rewritten as pre-dispatch failures;
    the service will preserve the reservation for reconciliation.
    """

    import litellm

    messages = _validated_messages(config, request_body)
    try:
        prompt_tokens = int(
            litellm.token_counter(model=config.litellm_model, messages=messages)
        )
        if prompt_tokens < 0:
            raise ValueError
        prompt_cost, completion_cost = litellm.cost_per_token(
            model=config.litellm_model,
            prompt_tokens=prompt_tokens,
            completion_tokens=config.max_tokens,
        )
    except ProviderPreDispatchError:
        raise
    except Exception as exc:
        raise ProviderPreDispatchError("unable to compute a bounded estimate") from exc

    worst_case_cost = _pre_dispatch_money(
        Decimal(str(prompt_cost)) + Decimal(str(completion_cost)),
        name="provider worst-case estimate",
    )
    if worst_case_cost > config.max_request_cost_usd:
        raise ProviderBudgetEstimateError

    response = litellm.completion(
        model=config.litellm_model,
        api_key=config.api_key,
        messages=messages,
        max_tokens=config.max_tokens,
        num_retries=0,
        timeout=config.timeout_seconds,
    )
    try:
        # Pin the provider explicitly: litellm re-derives it from the model
        # ID, which misfires on nested IDs (groq/openai/gpt-oss-20b is read
        # as provider "openai" and misses the cost map).
        cost = _actual_money(
            litellm.completion_cost(
                completion_response=response,
                custom_llm_provider=config.provider,
            )
        )
        usage = getattr(response, "usage", None)
        prompt_used = int(getattr(usage, "prompt_tokens", 0) or 0)
        completion_used = int(getattr(usage, "completion_tokens", 0) or 0)
        if prompt_used < 0 or completion_used < 0:
            raise ValueError
        text = response.choices[0].message.content or ""
        if not isinstance(text, str):
            raise TypeError
    except ProviderAccountingError:
        raise
    except Exception as exc:
        raise ProviderAccountingError(
            "provider response accounting is invalid"
        ) from exc

    return ProviderResult(
        text=text,
        prompt_tokens=prompt_used,
        completion_tokens=completion_used,
        provider_cost_usd=cost,
    )
