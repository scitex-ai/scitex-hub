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


#: Rounds cap for the funded tool loop. The reservation covers the whole
#: loop, so this stays small: free-tier cost control first.
FUNDED_TOOL_LOOP_MAX_ROUNDS = 5


def _funded_tools(user):
    """User-scoped tools for the funded loop: (executor, tool_schemas).

    Only tools that act as *this user* are exposed here. ``ui_action``
    relays steps to the user's own browser via their relay group, so the
    user watches the agent work. The unscoped in-process MCP umbrella is
    deliberately NOT exposed on the free path.
    """

    from apps.infra.llm_app.relay_groups import relay_group_for
    from apps.infra.llm_app.services.mcp_client import _UI_ACTION_TOOL  # noqa: F401

    _BROWSER_EVAL_TOOL = {
        "type": "function",
        "function": {
            "name": "browser_eval",
            "description": (
                "Run JavaScript in the user's open browser tab and return "
                "the completion value as JSON. Use this to READ back UI "
                "state and verify your ui_action steps actually landed "
                "(e.g. return document.querySelector('#x').value). "
                "Pure expression or statements; the last value is returned."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "code": {
                        "type": "string",
                        "description": "JavaScript to evaluate and return.",
                    },
                    "timeout": {
                        "type": "integer",
                        "description": "Seconds to wait for the tab (default 10, max 20).",
                    },
                },
                "required": ["code"],
            },
        },
    }

    async def _browser_eval(code: str, timeout: int) -> str:
        import asyncio as _asyncio
        import json as _json
        import uuid as _uuid

        from asgiref.sync import sync_to_async
        from channels.layers import get_channel_layer
        from django.core.cache import cache

        timeout = max(1, min(int(timeout or 10), 20))
        request_id = str(_uuid.uuid4())[:8]
        result_key = f"eval_js_result_{request_id}"
        channel_layer = get_channel_layer()
        await channel_layer.group_send(
            relay_group_for(user),
            {"type": "eval_js", "code": code, "request_id": request_id},
        )
        for _ in range(timeout * 10):
            result = await sync_to_async(cache.get)(result_key)
            if result is not None:
                await sync_to_async(cache.delete)(result_key)
                return _json.dumps({"result": result}, ensure_ascii=False)[:4000]
            await _asyncio.sleep(0.1)
        return _json.dumps({"error": "browser did not answer in time"})

    async def _execute(name: str, arguments: dict) -> str:
        if name == "browser_eval":
            if not isinstance(arguments, dict) or not arguments.get("code"):
                return "Error: browser_eval needs a code string."
            return await _browser_eval(
                str(arguments["code"]), arguments.get("timeout", 10)
            )
        if name != "ui_action":
            return f"Error: tool {name!r} is not available on the free path."
        steps = arguments.get("steps", []) if isinstance(arguments, dict) else []
        if not steps:
            return "Error: ui_action needs a non-empty steps list."
        from channels.layers import get_channel_layer

        channel_layer = get_channel_layer()
        await channel_layer.group_send(
            relay_group_for(user),
            {
                "type": "ui_action",
                "steps": steps,
                "delay_ms": arguments.get("delay_ms", 900),
            },
        )
        return f"Sent {len(steps)} UI steps to your browser; they run now."

    return _execute, [_UI_ACTION_TOOL, _BROWSER_EVAL_TOOL]


def litellm_tool_loop_call(
    config: FundedChatConfig,
    request_body: bytes,
    _dispatch_key: str = "",
    *,
    user,
    max_rounds: int = 3,
) -> ProviderResult:
    """Bounded agentic loop for the funded path: at most ``max_rounds``
    provider calls under ONE reservation.

    Pre-dispatch, the single-call worst case times ``max_rounds`` must fit
    ``max_request_cost_usd``; otherwise this raises before anything is
    dispatched. Actual usage is accumulated per round and settled normally.
    """
    import asyncio

    import litellm

    from apps.infra.llm_app.services.mcp_client import run_tool_loop

    rounds = max(1, min(int(max_rounds), FUNDED_TOOL_LOOP_MAX_ROUNDS))
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
        (Decimal(str(prompt_cost)) + Decimal(str(completion_cost))) * rounds,
        name="provider worst-case estimate",
    )
    if worst_case_cost > config.max_request_cost_usd:
        raise ProviderBudgetEstimateError

    _exec, tools = _funded_tools(user)
    loop_timeout = max(10, min(config.timeout_seconds * rounds, 100))

    async def _run():
        return await run_tool_loop(
            litellm_model=config.litellm_model,
            api_key=config.api_key,
            messages=messages,
            tools=tools,
            max_tokens=config.max_tokens,
            temperature=0.3,
            max_rounds=rounds,
            tool_executor=_exec,
        )

    try:
        text, _tools_used, loop_usage = asyncio.run(
            asyncio.wait_for(_run(), timeout=loop_timeout)
        )
    except ProviderPreDispatchError:
        raise
    except (asyncio.TimeoutError, TimeoutError) as exc:
        # Dispatched already (or unknown): fail closed to reconciliation.
        raise ProviderAccountingError("funded tool loop timed out") from exc
    if not isinstance(text, str):
        raise ProviderAccountingError("provider response accounting is invalid")
    try:
        cost = _actual_money(
            Decimal(str(loop_usage.get("estimated_cost_usd", 0.0)))
        )
        prompt_used = int(loop_usage.get("prompt_tokens", 0))
        completion_used = int(loop_usage.get("completion_tokens", 0))
        if prompt_used < 0 or completion_used < 0:
            raise ValueError
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
