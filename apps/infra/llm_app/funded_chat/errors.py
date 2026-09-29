from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Final

ERROR_CATEGORIES: Final = {
    "insufficient_balance",
    "quota_reached",
    "provider_auth",
    "rate_limit",
    "model_unavailable",
    "timeout",
    "provider_outage",
}

_INSUFFICIENT_TYPES = frozenset(
    {"BudgetExceededError", "InsufficientCreditsError", "PaymentRequiredError"}
)
_AUTH_TYPES = frozenset({"AuthenticationError", "AuthorizationError"})
_RATE_TYPES = frozenset({"RateLimitError", "TooManyRequestsError"})
_MODEL_TYPES = frozenset(
    {
        "BadRequestError",
        "ModelNotFoundError",
        "NotFoundError",
        "PermissionDeniedError",
        "UnsupportedModelError",
    }
)
_TIMEOUT_TYPES = frozenset({"APITimeoutError", "Timeout", "TimeoutError"})
_OUTAGE_TYPES = frozenset(
    {"APIConnectionError", "APIError", "ServiceUnavailableError", "InternalServerError"}
)


@dataclass(frozen=True, slots=True)
class ClassifiedProviderError:
    """Sanitized provider failure safe to serialize to an untrusted client."""

    category: str
    retry_after_seconds: int | None
    support_id: str


def _status_code(exc: BaseException) -> int | None:
    value = getattr(exc, "status_code", None)
    if value is None:
        response = getattr(exc, "response", None)
        value = getattr(response, "status_code", None)
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _retry_after(exc: BaseException) -> int | None:
    value = getattr(exc, "retry_after", None)
    if value is None:
        response = getattr(exc, "response", None)
        headers = getattr(response, "headers", None)
        if headers is not None:
            value = headers.get("retry-after") or headers.get("Retry-After")
    try:
        seconds = int(float(value))
    except (TypeError, ValueError):
        return None
    return min(max(seconds, 1), 86_400)


def classify_provider_exception(exc: BaseException) -> ClassifiedProviderError:
    """Classify by typed/status metadata while discarding provider text.

    The exception itself is never retained, interpolated, logged, or serialized.
    Unknown failures fail closed to ``provider_outage`` with a random support id.
    """

    name = type(exc).__name__
    status = _status_code(exc)

    if name in _INSUFFICIENT_TYPES or status == 402:
        category = "insufficient_balance"
    elif name in _RATE_TYPES or status == 429:
        category = "rate_limit"
    elif name in _MODEL_TYPES or status in {400, 403, 404, 410}:
        category = "model_unavailable"
    elif (
        name in _TIMEOUT_TYPES or isinstance(exc, TimeoutError) or status in {408, 504}
    ):
        category = "timeout"
    elif name in _AUTH_TYPES or status == 401:
        category = "provider_auth"
    elif name in _OUTAGE_TYPES or status is None or status >= 500:
        category = "provider_outage"
    else:
        category = "provider_outage"

    support_id = getattr(exc, "_scitex_support_id", "")
    try:
        uuid.UUID(hex=str(support_id))
    except (ValueError, TypeError, AttributeError):
        support_id = uuid.uuid4().hex
        try:
            exc.__dict__["_scitex_support_id"] = support_id
        except Exception:
            pass

    retry_after = _retry_after(exc) if category == "rate_limit" else None
    if category == "rate_limit" and retry_after is None:
        retry_after = 60

    return ClassifiedProviderError(
        category=category,
        retry_after_seconds=retry_after,
        support_id=str(support_id),
    )


def provider_error_payload(
    exc: BaseException,
    *,
    remaining: int | None,
    reset_at: str,
    model: str,
) -> dict[str, str | int | None]:
    """Serialize only computed fields; the provider exception is never echoed."""

    classified = classify_provider_exception(exc)
    return {
        "category": classified.category,
        "remaining": remaining,
        "reset_at": reset_at,
        "model": model,
        "error": "AI provider request failed",
        "retry_after": classified.retry_after_seconds,
        "support_id": classified.support_id,
    }
