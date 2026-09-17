from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation

from django.conf import settings


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

    @property
    def litellm_model(self) -> str:
        prefix = f"{self.provider}/"
        return self.model if self.model.startswith(prefix) else prefix + self.model


def _decimal_setting(name: str) -> Decimal:
    try:
        return Decimal(str(getattr(settings, name, "0")))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise FundedChatConfigurationError(f"{name} must be a decimal") from exc


def load_funded_chat_config() -> FundedChatConfig:
    """Load the one configured provider/model; never infer or fall back."""

    enabled = bool(getattr(settings, "SCITEX_FUNDED_CHAT_ENABLED", False))
    provider = str(getattr(settings, "SCITEX_FUNDED_CHAT_PROVIDER", "")).strip()
    model = str(getattr(settings, "SCITEX_FUNDED_CHAT_MODEL", "")).strip()
    api_key = str(getattr(settings, "SCITEX_FUNDED_CHAT_API_KEY", "")).strip()
    global_cap = _decimal_setting("SCITEX_FUNDED_CHAT_GLOBAL_DAILY_CAP_USD")
    provider_cap = _decimal_setting("SCITEX_FUNDED_CHAT_PROVIDER_DAILY_CAP_USD")
    request_cap = _decimal_setting("SCITEX_FUNDED_CHAT_MAX_REQUEST_COST_USD")

    config = FundedChatConfig(
        enabled=enabled,
        provider=provider,
        model=model,
        api_key=api_key,
        requests_per_minute=int(
            getattr(settings, "SCITEX_FUNDED_CHAT_REQUESTS_PER_MINUTE", 3)
        ),
        global_daily_cap_usd=global_cap,
        provider_daily_cap_usd=provider_cap,
        max_request_cost_usd=request_cap,
        max_tokens=int(getattr(settings, "SCITEX_FUNDED_CHAT_MAX_TOKENS", 2048)),
    )
    if not enabled:
        return config

    if not provider or not model or not api_key:
        raise FundedChatConfigurationError(
            "enabled funded chat requires an explicit provider, model, and API key"
        )
    if min(global_cap, provider_cap, request_cap) <= 0:
        raise FundedChatConfigurationError(
            "enabled funded chat requires positive global, provider, and request caps"
        )
    if config.requests_per_minute <= 0 or config.max_tokens <= 0:
        raise FundedChatConfigurationError(
            "enabled funded chat requires positive abuse and token limits"
        )
    return config
