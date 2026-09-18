from __future__ import annotations

import re
from dataclasses import dataclass, field
from decimal import ROUND_DOWN, ROUND_UP, Decimal, InvalidOperation

from django.conf import settings

MONEY_QUANTUM = Decimal("0.000001")
MAX_DATABASE_MONEY = Decimal("999999.999999")
RESERVED_GLOBAL_SCOPE = "__global__"
_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")


class FundedChatConfigurationError(RuntimeError):
    """The funded path is enabled without all fail-closed controls."""


@dataclass(frozen=True, slots=True)
class FundedChatConfig:
    enabled: bool
    provider: str
    model: str
    api_key: str = field(repr=False)
    daily_limit: int = 10
    requests_per_minute: int = 3
    global_daily_cap_usd: Decimal = Decimal("0")
    provider_daily_cap_usd: Decimal = Decimal("0")
    max_request_cost_usd: Decimal = Decimal("0")
    max_tokens: int = 2048
    timeout_seconds: int = 30
    reservation_lease_seconds: int = 120
    max_request_bytes: int = 65_536
    max_messages: int = 64
    max_message_chars: int = 32_768
    allowed_providers: tuple[str, ...] = ()
    allowed_models: tuple[str, ...] = ()

    @property
    def litellm_model(self) -> str:
        prefix = f"{self.provider}/"
        return self.model if self.model.startswith(prefix) else prefix + self.model


def quantize_money(
    value: Decimal, *, name: str = "amount", rounding=ROUND_UP
) -> Decimal:
    """Return a finite DB-representable amount with explicit rounding.

    Callers use ``ROUND_UP`` for reservations and positive spend so sub-micro
    charges cannot disappear, and ``ROUND_DOWN`` for caps so quantization never
    widens an operator's spending limit.
    """

    if not isinstance(value, Decimal):
        try:
            value = Decimal(str(value))
        except (InvalidOperation, TypeError, ValueError) as exc:
            raise FundedChatConfigurationError(f"{name} must be a decimal") from exc
    if not value.is_finite() or value < 0 or value > MAX_DATABASE_MONEY:
        raise FundedChatConfigurationError(
            f"{name} must be finite, non-negative, and database-representable"
        )
    try:
        quantized = value.quantize(MONEY_QUANTUM, rounding=rounding)
    except InvalidOperation as exc:
        raise FundedChatConfigurationError(
            f"{name} must be database-representable"
        ) from exc
    if quantized > MAX_DATABASE_MONEY:
        raise FundedChatConfigurationError(f"{name} exceeds database capacity")
    return quantized


def _decimal_setting(name: str, *, rounding=ROUND_DOWN) -> Decimal:
    try:
        raw = Decimal(str(getattr(settings, name, "0")))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise FundedChatConfigurationError(f"{name} must be a decimal") from exc
    return quantize_money(raw, name=name, rounding=rounding)


def _positive_int_setting(name: str, default: int) -> int:
    try:
        value = int(getattr(settings, name, default))
    except (TypeError, ValueError, OverflowError) as exc:
        raise FundedChatConfigurationError(f"{name} must be an integer") from exc
    if value <= 0:
        raise FundedChatConfigurationError(f"{name} must be positive")
    return value


def _validate_provider_model(provider: str, model: str) -> None:
    if (
        not provider
        or len(provider) > 64
        or not _IDENTIFIER.fullmatch(provider)
        or provider == RESERVED_GLOBAL_SCOPE
        or RESERVED_GLOBAL_SCOPE in provider
    ):
        raise FundedChatConfigurationError("funded provider is not allowlisted")
    if not model or len(model) > 200 or any(ch.isspace() for ch in model):
        raise FundedChatConfigurationError("funded model is not allowlisted")
    if RESERVED_GLOBAL_SCOPE in model:
        raise FundedChatConfigurationError(
            "funded model collides with a reserved namespace"
        )
    if "/" in model:
        prefix, suffix = model.split("/", 1)
        if prefix != provider or not suffix or "/" in suffix:
            raise FundedChatConfigurationError(
                "funded model is outside the provider allowlist"
            )
    elif not _IDENTIFIER.fullmatch(model):
        raise FundedChatConfigurationError("funded model is not allowlisted")


def load_funded_chat_config() -> FundedChatConfig:
    """Load and validate the operator's one-entry provider/model allowlist."""

    enabled = bool(getattr(settings, "SCITEX_FUNDED_CHAT_ENABLED", False))
    provider = str(getattr(settings, "SCITEX_FUNDED_CHAT_PROVIDER", "")).strip()
    model = str(getattr(settings, "SCITEX_FUNDED_CHAT_MODEL", "")).strip()
    api_key = str(getattr(settings, "SCITEX_FUNDED_CHAT_API_KEY", "")).strip()
    global_cap = _decimal_setting("SCITEX_FUNDED_CHAT_GLOBAL_DAILY_CAP_USD")
    provider_cap = _decimal_setting("SCITEX_FUNDED_CHAT_PROVIDER_DAILY_CAP_USD")
    request_cap = _decimal_setting(
        "SCITEX_FUNDED_CHAT_MAX_REQUEST_COST_USD", rounding=ROUND_UP
    )

    config = FundedChatConfig(
        enabled=enabled,
        provider=provider,
        model=model,
        api_key=api_key,
        daily_limit=_positive_int_setting("SCITEX_FUNDED_CHAT_DAILY_LIMIT", 10),
        requests_per_minute=_positive_int_setting(
            "SCITEX_FUNDED_CHAT_REQUESTS_PER_MINUTE", 3
        ),
        global_daily_cap_usd=global_cap,
        provider_daily_cap_usd=provider_cap,
        max_request_cost_usd=request_cap,
        max_tokens=_positive_int_setting("SCITEX_FUNDED_CHAT_MAX_TOKENS", 2048),
        timeout_seconds=_positive_int_setting("SCITEX_FUNDED_CHAT_TIMEOUT_SECONDS", 30),
        reservation_lease_seconds=_positive_int_setting(
            "SCITEX_FUNDED_CHAT_RESERVATION_LEASE_SECONDS", 120
        ),
        max_request_bytes=_positive_int_setting(
            "SCITEX_FUNDED_CHAT_MAX_REQUEST_BYTES", 65_536
        ),
        max_messages=_positive_int_setting("SCITEX_FUNDED_CHAT_MAX_MESSAGES", 64),
        max_message_chars=_positive_int_setting(
            "SCITEX_FUNDED_CHAT_MAX_MESSAGE_CHARS", 32_768
        ),
        allowed_providers=(provider,) if provider else (),
        allowed_models=(model,) if model else (),
    )
    if not enabled:
        return config

    if not provider or not model or not api_key:
        raise FundedChatConfigurationError(
            "enabled funded chat requires an explicit provider, model, and API key"
        )
    _validate_provider_model(provider, model)
    if min(global_cap, provider_cap, request_cap) <= 0:
        raise FundedChatConfigurationError(
            "enabled funded chat requires positive global, provider, and request caps"
        )
    if request_cap > provider_cap or request_cap > global_cap:
        raise FundedChatConfigurationError(
            "funded request cap must not exceed provider or global cap"
        )
    if config.daily_limit > 10:
        raise FundedChatConfigurationError(
            "funded daily limit exceeds the durable database constraint"
        )
    return config
