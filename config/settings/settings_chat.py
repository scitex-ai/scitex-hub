#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: config/settings/settings_chat.py
"""Campaign chat and SciTeX-funded chat settings.

Split out of settings_shared, which star-imports it at the same point, so the
override order of every environment module is unchanged.
"""

from config._env import getenv_with_legacy_alias as _getenv_alias

# Campaign Chat Mode
SCITEX_HUB_CAMPAIGN_ANTHROPIC_API_KEY = _getenv_alias(
    "SCITEX_HUB_CAMPAIGN_ANTHROPIC_API_KEY", ""
)
SCITEX_HUB_CAMPAIGN_MODEL = _getenv_alias(
    "SCITEX_HUB_CAMPAIGN_MODEL", "claude-haiku-4-5-20251001"
)
SCITEX_HUB_CAMPAIGN_DAILY_LIMIT = _getenv_alias("SCITEX_HUB_CAMPAIGN_DAILY_LIMIT", "10")

# SciTeX-funded Chat. Enabled is the operator kill switch: when false, the
# funded path cannot reserve quota or contact a provider. Provider/model/caps
# intentionally have no useful defaults; enabling an incomplete configuration
# fails closed in funded_chat.config rather than silently selecting a model.
SCITEX_FUNDED_CHAT_ENABLED = (
    _getenv_alias("SCITEX_FUNDED_CHAT_ENABLED", "false") or "false"
).lower() in ("1", "true", "yes", "on")
SCITEX_FUNDED_CHAT_PROVIDER = _getenv_alias("SCITEX_FUNDED_CHAT_PROVIDER", "")
SCITEX_FUNDED_CHAT_MODEL = _getenv_alias("SCITEX_FUNDED_CHAT_MODEL", "")
SCITEX_FUNDED_CHAT_API_KEY = _getenv_alias("SCITEX_FUNDED_CHAT_API_KEY", "")
SCITEX_FUNDED_CHAT_GLOBAL_DAILY_CAP_USD = _getenv_alias(
    "SCITEX_FUNDED_CHAT_GLOBAL_DAILY_CAP_USD", "0"
)
SCITEX_FUNDED_CHAT_PROVIDER_DAILY_CAP_USD = _getenv_alias(
    "SCITEX_FUNDED_CHAT_PROVIDER_DAILY_CAP_USD", "0"
)
SCITEX_FUNDED_CHAT_MAX_REQUEST_COST_USD = _getenv_alias(
    "SCITEX_FUNDED_CHAT_MAX_REQUEST_COST_USD", "0"
)
SCITEX_FUNDED_CHAT_REQUESTS_PER_MINUTE = int(
    _getenv_alias("SCITEX_FUNDED_CHAT_REQUESTS_PER_MINUTE", "3") or "3"
)
SCITEX_FUNDED_CHAT_DAILY_LIMIT = int(
    _getenv_alias("SCITEX_FUNDED_CHAT_DAILY_LIMIT", "10") or "10"
)
SCITEX_FUNDED_CHAT_MAX_TOKENS = int(
    _getenv_alias(
        "SCITEX_FUNDED_CHAT_MAX_TOKENS", "2048"
    )  # pragma: allowlist secret -- output-token count, not a credential
    or "2048"
)
SCITEX_FUNDED_CHAT_TIMEOUT_SECONDS = int(
    _getenv_alias("SCITEX_FUNDED_CHAT_TIMEOUT_SECONDS", "30") or "30"
)
SCITEX_FUNDED_CHAT_RESERVATION_LEASE_SECONDS = int(
    _getenv_alias("SCITEX_FUNDED_CHAT_RESERVATION_LEASE_SECONDS", "120") or "120"
)
SCITEX_FUNDED_CHAT_MAX_REQUEST_BYTES = int(
    _getenv_alias("SCITEX_FUNDED_CHAT_MAX_REQUEST_BYTES", "65536") or "65536"
)
SCITEX_FUNDED_CHAT_MAX_MESSAGES = int(
    _getenv_alias("SCITEX_FUNDED_CHAT_MAX_MESSAGES", "64") or "64"
)
SCITEX_FUNDED_CHAT_MAX_MESSAGE_CHARS = int(
    _getenv_alias("SCITEX_FUNDED_CHAT_MAX_MESSAGE_CHARS", "32768") or "32768"
)


# EOF
