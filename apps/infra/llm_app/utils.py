"""LLM provider registry — uses litellm for dynamic model discovery."""

from __future__ import annotations

import importlib.metadata

# Curated providers that accept a simple API key (or no key for local).
# Keys must fit IntegrationConnection.service max_length=20.
# "curated_models": explicit list shown in UI (None = discover from litellm)
LLM_PROVIDERS: dict[str, dict] = {
    "anthropic": {
        "display": "Anthropic (Claude)",
        "needs_key": True,
        "model_prefix": "",
        "curated_models": [
            "claude-opus-4-6",
            "claude-sonnet-4-6",
            "claude-haiku-4-5-20251001",
            "claude-3-5-sonnet-20241022",
            "claude-3-5-haiku-20241022",
            "claude-3-opus-20240229",
        ],
    },
    "openai": {
        "display": "OpenAI (GPT)",
        "needs_key": True,
        "model_prefix": "",
        "curated_models": [
            "gpt-4o",
            "gpt-4o-mini",
            "o1",
            "o1-mini",
            "o3",
            "o3-mini",
        ],
    },
    "gemini": {
        "display": "Google (Gemini)",
        "needs_key": True,
        "model_prefix": "gemini/",
        "curated_models": [
            "gemini-2.0-flash",
            "gemini-2.0-flash-lite",
            "gemini-1.5-pro",
            "gemini-1.5-flash",
        ],
    },
    "mistral": {
        "display": "Mistral AI",
        "needs_key": True,
        "model_prefix": "mistral/",
        "curated_models": [
            "mistral-large-latest",
            "mistral-small-latest",
            "codestral-latest",
            "mistral-nemo",
        ],
    },
    "xai": {
        "display": "xAI (Grok)",
        "needs_key": True,
        "model_prefix": "xai/",
        "curated_models": [
            "grok-2",
            "grok-2-mini",
            "grok-beta",
        ],
    },
    "deepseek": {
        "display": "DeepSeek",
        "needs_key": True,
        "model_prefix": "deepseek/",
        "curated_models": [
            "deepseek-chat",
            "deepseek-reasoner",
        ],
    },
    "mimo": {
        # Xiaomi MiMo token plan — consumed by the terminal model-provider
        # picker (Anthropic-compatible endpoint; the gateway serves its
        # default model, hence no curated chat models here yet).
        "display": "Xiaomi MiMo",
        "needs_key": True,
        "model_prefix": "",
        "curated_models": [],
    },
    "openrouter": {
        "display": "OpenRouter",
        "needs_key": True,
        "model_prefix": "openrouter/",
        "curated_models": None,  # discover from litellm
    },
    "ollama": {
        "display": "Ollama (local)",
        "needs_key": False,
        "model_prefix": "ollama/",
        "curated_models": None,  # discover from litellm
    },
}

# Legacy service ID kept for backward-compat with existing DB rows.
_LEGACY_ALIASES: dict[str, str] = {"local_llm": "ollama"}

# All valid service IDs accepted for LLM connections
ALL_LLM_SERVICE_IDS: set[str] = set(LLM_PROVIDERS) | set(_LEGACY_ALIASES)

# Cache key includes litellm version + curated list revision so changes invalidate cache.
_LITELLM_VERSION = importlib.metadata.version("litellm")
_CURATED_REVISION = "3"  # bump when curated_models lists change
_CACHE_KEY = f"llm_providers_v{_LITELLM_VERSION.replace('.', '_')}_r{_CURATED_REVISION}"


def get_provider_models(provider_id: str) -> list[str]:
    """Return chat-capable model names for a provider.

    Uses the curated list when defined; falls back to litellm discovery.
    """
    info = LLM_PROVIDERS.get(provider_id)
    if not info:
        return []

    curated = info.get("curated_models")
    if curated is not None:
        return curated

    # Dynamic discovery via litellm (for OpenRouter, Ollama, etc.)
    import litellm

    prefix = info["model_prefix"]
    costs = litellm.model_cost

    if prefix:
        models = [
            m[len(prefix) :]
            for m, data in costs.items()
            if m.startswith(prefix) and data.get("mode") == "chat"
        ]
    else:
        models = []

    return sorted(set(models))


def get_all_providers_cached() -> list[dict]:
    """
    Return the full provider+model list, cached by litellm version.

    The first call imports litellm (~12 s cold). All subsequent calls within
    the same Django deployment return instantly from the cache.
    Cache is keyed by litellm version, so upgrading litellm auto-invalidates.
    """
    from django.core.cache import cache

    cached = cache.get(_CACHE_KEY)
    if cached is not None:
        return cached

    providers = [
        {
            "id": pid,
            "display": info["display"],
            "needs_key": info["needs_key"],
            "models": get_provider_models(pid),
        }
        for pid, info in LLM_PROVIDERS.items()
    ]
    # timeout=None means never expire (valid for the lifetime of this litellm version)
    cache.set(_CACHE_KEY, providers, timeout=None)
    return providers


def litellm_model_string(service: str, model: str) -> str:
    """Build the model string passed to litellm for *service* + *model*."""
    service = _LEGACY_ALIASES.get(service, service)
    prefix = LLM_PROVIDERS.get(service, {}).get("model_prefix", f"{service}/")
    return f"{prefix}{model}"
