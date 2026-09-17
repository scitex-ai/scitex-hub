from __future__ import annotations

import json
from decimal import Decimal

from .config import FundedChatConfig
from .service import ProviderResult


class ProviderBudgetEstimateError(Exception):
    """The worst-case configured-model cost exceeds the reserved request budget."""

    status_code = 402


def litellm_provider_call(
    config: FundedChatConfig, request_body: bytes
) -> ProviderResult:
    """Call exactly the configured model once, with LiteLLM fallbacks disabled."""

    import litellm

    payload = json.loads(request_body)
    messages = payload["messages"]
    if not isinstance(messages, list) or not messages:
        raise ValueError("messages must be a non-empty list")

    prompt_tokens = litellm.token_counter(
        model=config.litellm_model,
        messages=messages,
    )
    prompt_cost, completion_cost = litellm.cost_per_token(
        model=config.litellm_model,
        prompt_tokens=prompt_tokens,
        completion_tokens=config.max_tokens,
    )
    worst_case_cost = Decimal(str(prompt_cost)) + Decimal(str(completion_cost))
    if worst_case_cost > config.max_request_cost_usd:
        raise ProviderBudgetEstimateError

    response = litellm.completion(
        model=config.litellm_model,
        api_key=config.api_key,
        messages=messages,
        max_tokens=config.max_tokens,
        num_retries=0,
    )
    try:
        cost = Decimal(str(litellm.completion_cost(completion_response=response)))
    except Exception:
        # A provider response already happened and may already be billable. Record
        # the reserved worst-case estimate rather than retrying or pretending $0.
        cost = config.max_request_cost_usd

    usage = getattr(response, "usage", None)
    return ProviderResult(
        text=response.choices[0].message.content or "",
        prompt_tokens=int(getattr(usage, "prompt_tokens", 0) or 0),
        completion_tokens=int(getattr(usage, "completion_tokens", 0) or 0),
        provider_cost_usd=cost,
    )
