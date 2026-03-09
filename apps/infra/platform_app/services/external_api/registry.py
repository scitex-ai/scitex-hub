"""
ExternalAPI registry.

Stores API configurations keyed by (app_name, api_name).
Configurations come from app manifests and are registered at startup
or on-demand. Thread-safe for concurrent reads; write conflicts on
startup are benign (last write wins with identical data).
"""

import logging
import threading
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

# Internal store: { app_name: { api_name: config_dict } }
_registry: Dict[str, Dict[str, Dict[str, Any]]] = {}
_lock = threading.Lock()


class APINotFoundError(KeyError):
    """Raised when a requested API is not registered."""


def register_api(app_name: str, api_name: str, config: Dict[str, Any]) -> None:
    """
    Register an external API configuration.

    Args:
        app_name:  Owner app identifier (e.g. "my_app").
        api_name:  Logical API name (e.g. "crossref").
        config:    Dict with at minimum {"base_url": "https://..."},
                   optionally methods, rate_limit, headers, timeout.

    Raises:
        ValueError: If base_url is missing from config.
    """
    if "base_url" not in config:
        raise ValueError(
            f"API config for '{app_name}/{api_name}' must include 'base_url'."
        )

    with _lock:
        if app_name not in _registry:
            _registry[app_name] = {}
        _registry[app_name][api_name] = config

    logger.debug("[ExternalAPI] Registered '%s/%s'", app_name, api_name)


def get_api(app_name: str, api_name: str) -> Dict[str, Any]:
    """
    Retrieve a registered API configuration.

    Args:
        app_name: Owner app identifier.
        api_name: Logical API name.

    Returns:
        Config dict as registered.

    Raises:
        APINotFoundError: If the API has not been registered.
    """
    app_apis = _registry.get(app_name, {})
    if api_name not in app_apis:
        available = list(app_apis.keys()) if app_apis else []
        raise APINotFoundError(
            f"API '{api_name}' not registered for app '{app_name}'. "
            f"Available: {available}"
        )
    return app_apis[api_name]


def list_apis(app_name: str) -> List[str]:
    """
    List all registered API names for a given app.

    Args:
        app_name: Owner app identifier.

    Returns:
        Sorted list of API names (empty list if app has none).
    """
    return sorted(_registry.get(app_name, {}).keys())


def unregister_api(app_name: str, api_name: str) -> None:
    """
    Remove a registered API (mainly useful for tests).

    Args:
        app_name: Owner app identifier.
        api_name: Logical API name.
    """
    with _lock:
        if app_name in _registry and api_name in _registry[app_name]:
            del _registry[app_name][api_name]
            logger.debug("[ExternalAPI] Unregistered '%s/%s'", app_name, api_name)


# EOF
