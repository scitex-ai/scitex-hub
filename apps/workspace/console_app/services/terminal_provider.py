#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Model-provider registry + env composition for hub terminal sessions.

"Option A" model-agnostic agent sessions (operator-approved 2026-07-08):
when a user picks a provider for a terminal session, the broker injects
``ANTHROPIC_BASE_URL`` / ``ANTHROPIC_API_KEY`` / ``ANTHROPIC_MODEL`` (+ a
clean ``CLAUDE_CONFIG_DIR`` so cached OAuth credentials cannot override
the key) into the PTY child environment. The stock ``claude`` CLI already
installed in user containers then talks to that Anthropic-compatible
backend. No agent-specific binary, no sac import.

Source of truth for the provider recipe: scitex-agent-container's
``config/_provider_registry.py`` and
``runtimes/_apptainer_provider.py::provider_env_flags`` (validated
end-to-end with A/B network proof). This module mirrors those semantics
hub-side; keep the two registries aligned. Longer term this constant
should probably move into ``scitex_container`` (the shared
Django <-> container seam) so hub and sac read one registry — kept
hub-local for now to keep this change small.

Security invariants (fail-loud, never silent):

* Provider ids are validated against this server-side registry — a
  client can never supply a free-form ``base_url`` or env var.
* API keys are resolved SERVER-SIDE from the user's encrypted
  ``IntegrationConnection`` rows (the existing llm_app key store, the
  same keys managed on /accounts/settings/ai-providers/). Nothing the
  client sends is ever treated as a credential.
* Key VALUES never appear in log records, error messages, or terminal
  echo — only key *presence* is ever reported.
* Missing key => :class:`ProviderKeyMissingError` with guidance, never a
  silent fallback to the default Anthropic backend (which would 401 on
  every turn while looking "connected").
"""

from __future__ import annotations

import logging
from typing import Callable, Optional

logger = logging.getLogger(__name__)

#: Where users manage per-provider API keys (llm_app key store UI).
AI_PROVIDER_SETTINGS_URL = "/accounts/settings/ai-providers/"

#: Default: the user's own Anthropic subscription sign-in inside the
#: container (``claude`` CLI OAuth flow). No env injection at all.
DEFAULT_PROVIDER = "anthropic-oauth"

#: provider id -> backend metadata.
#:
#: ``base_url``     Anthropic-compatible endpoint (None = Anthropic default).
#: ``key_service``  ``IntegrationConnection.service`` id holding the user's
#:                  API key (None = no key needed / OAuth).
#: ``model``        default model alias injected as ``ANTHROPIC_MODEL`` +
#:                  ``ANTHROPIC_SMALL_FAST_MODEL`` (None = backend default).
#:                  Without it the ``claude`` CLI would request Anthropic
#:                  model ids the gateway does not serve (sac ADR-0011).
#:
#: Mirrors sac ``config/_provider_registry.py`` — update both together.
TERMINAL_PROVIDERS: dict[str, dict[str, Optional[str]]] = {
    "anthropic-oauth": {
        "label": "Claude (subscription sign-in)",
        "base_url": None,
        "key_service": None,
        "model": None,
    },
    "anthropic-api-key": {
        "label": "Claude (your API key)",
        "base_url": None,
        "key_service": "anthropic",
        "model": None,
    },
    "deepseek": {
        "label": "DeepSeek (your API key)",
        "base_url": "https://api.deepseek.com/anthropic",
        "key_service": "deepseek",
        "model": "deepseek-chat",
    },
    "mimo": {
        "label": "Xiaomi MiMo (your API key)",
        "base_url": "https://token-plan-sgp.xiaomimimo.com/anthropic",
        "key_service": "mimo",
        "model": None,
    },
}


class TerminalProviderError(Exception):
    """Base for provider validation/resolution failures (message is
    user-safe: shown verbatim in the terminal, never contains a key)."""


class UnknownProviderError(TerminalProviderError):
    """Provider id not in the server-side registry."""


class ProviderKeyMissingError(TerminalProviderError):
    """Selected provider needs an API key the user has not stored."""


class ProviderNotAllowedError(TerminalProviderError):
    """Session role / ownership forbids this provider selection."""


def list_terminal_providers() -> list[str]:
    """Registered provider ids, sorted, for diagnostics and errors."""
    return sorted(TERMINAL_PROVIDERS)


def normalize_provider(provider_id: Optional[str]) -> str:
    """Map missing/empty to the default; reject unknown ids (fail-loud)."""
    provider_id = (provider_id or "").strip() or DEFAULT_PROVIDER
    if provider_id not in TERMINAL_PROVIDERS:
        raise UnknownProviderError(
            f"Unknown terminal provider '{provider_id}'. "
            f"Valid providers: {', '.join(list_terminal_providers())}."
        )
    return provider_id


def provider_requires_key(provider_id: str) -> bool:
    """True when the provider authenticates with a stored user API key."""
    return TERMINAL_PROVIDERS[normalize_provider(provider_id)][
        "key_service"
    ] is not None


def validate_provider_request(provider_id, user, project_owner) -> str:
    """Consumer-side gate: role + ownership rules for a provider request.

    Returns the normalized provider id, or raises
    :class:`TerminalProviderError` with a user-safe explanation.

    Rules (card: terminal model-provider, 2026-07-08):
    * default (``anthropic-oauth``) — allowed for every session that can
      open a terminal at all (auth is handled by the existing access
      check, this gate adds nothing for the default).
    * key-based providers — authenticated users only; the shared
      ``readonly-visitor`` account is rejected (it must never share one
      stored key across all readonly visitors); writable ``visitor-NNN``
      slots may use their own stored key; and the requester must BE the
      project owner, because the PTY runs as the owner and injecting any
      other account's key into the owner's environment would leak it.
    """
    from apps.infra.project_app.services.visitor_pool.session_role import (
        ROLE_READONLY_VISITOR,
        get_user_role,
    )

    provider_id = normalize_provider(provider_id)
    if provider_id == DEFAULT_PROVIDER:
        return provider_id

    label = TERMINAL_PROVIDERS[provider_id]["label"]
    role = get_user_role(user)

    if user is None or not getattr(user, "is_authenticated", False):
        raise ProviderNotAllowedError(
            f"Provider '{label}' needs your own API key — sign in first, "
            f"then add the key at {AI_PROVIDER_SETTINGS_URL}."
        )
    if role == ROLE_READONLY_VISITOR:
        raise ProviderNotAllowedError(
            "Read-only visitor sessions cannot use API-key providers — "
            "the shared read-only account stores no keys. Sign up or log "
            "in to use your own key."
        )
    if project_owner is not None and user.pk != project_owner.pk:
        raise ProviderNotAllowedError(
            f"Provider '{label}' runs on your own API key, but this "
            "terminal runs in the project owner's container. Only the "
            "project owner can select an API-key provider here."
        )
    return provider_id


def _default_key_lookup(username: str, key_service: str) -> str:
    """Resolve the user's decrypted API key from the llm_app key store.

    Server-side only. Returns "" when absent — the caller turns that
    into :class:`ProviderKeyMissingError`. The decrypted value is
    returned to the caller for env injection and NEVER logged.
    """
    from apps.infra.integrations_app.models import IntegrationConnection

    conn = (
        IntegrationConnection.objects.filter(
            user__username=username, service=key_service
        )
        .only("id", "api_key")
        .first()
    )
    if conn is None:
        return ""
    return conn.get_api_key() or ""


def resolve_provider_env(
    provider_id: str,
    username: str,
    key_lookup: Optional[Callable[[str, str], str]] = None,
) -> dict[str, str]:
    """Compose the PTY child env vars for a provider selection.

    Returns ``{}`` for the default (OAuth) provider — no injection, the
    ``claude`` CLI signs in with the user's own subscription as today.

    For key-based providers, returns the sac-proven recipe:

    * ``ANTHROPIC_API_KEY``          — the user's stored key (server-side).
    * ``ANTHROPIC_BASE_URL``         — only when the registry declares one.
    * ``ANTHROPIC_MODEL`` /
      ``ANTHROPIC_SMALL_FAST_MODEL`` — only when the registry declares a
      model alias (otherwise the gateway's default is intentional).
    * ``CLAUDE_CONFIG_DIR``          — a clean per-provider dir inside the
      user's container HOME. Conflict-breaker: without it, cached OAuth
      credentials in ``~/.claude`` would win and the CLI would talk to
      Anthropic instead of the selected backend.

    Raises :class:`ProviderKeyMissingError` (fail-loud) when the user
    has no stored key for the provider.
    """
    provider_id = normalize_provider(provider_id)
    entry = TERMINAL_PROVIDERS[provider_id]
    key_service = entry["key_service"]
    if key_service is None:
        return {}

    lookup = key_lookup or _default_key_lookup
    api_key = lookup(username, key_service)
    if not api_key:
        raise ProviderKeyMissingError(
            f"No {entry['label'].split(' (')[0]} API key stored for user "
            f"'{username}'. Add your key at {AI_PROVIDER_SETTINGS_URL} "
            "and reopen the terminal."
        )

    env = {
        "ANTHROPIC_API_KEY": api_key,
        # Per-provider clean config dir inside the container HOME so a
        # cached OAuth login can never override the injected key.
        "CLAUDE_CONFIG_DIR": (
            f"/home/{username}/.scitex/claude-provider/{provider_id}"
        ),
    }
    if entry["base_url"]:
        env["ANTHROPIC_BASE_URL"] = entry["base_url"]
    if entry["model"]:
        # Both vars: the CLI's main and background (haiku-class) calls
        # must hit a model alias the gateway actually serves.
        env["ANTHROPIC_MODEL"] = entry["model"]
        env["ANTHROPIC_SMALL_FAST_MODEL"] = entry["model"]
    logger.info(
        "Terminal provider env composed: provider=%s user=%s vars=%s",
        provider_id,
        username,
        sorted(env),  # names only — values (the key) are never logged
    )
    return env


def resolve_spawn_provider(
    msg: dict,
    key_lookup: Optional[Callable[[str, str], str]] = None,
) -> tuple[str, dict[str, str]]:
    """Broker-side resolution for a spawn message.

    Validates ``msg['provider']`` against the registry and composes the
    env server-side (key via ``key_lookup``, defaulting to the encrypted
    DB store — never from the client message). Returns
    ``(provider_id, provider_env)``; raises
    :class:`TerminalProviderError` with a user-safe message.
    """
    provider_id = normalize_provider(msg.get("provider"))
    provider_env = resolve_provider_env(
        provider_id, msg["username"], key_lookup=key_lookup
    )
    return provider_id, provider_env


# EOF
