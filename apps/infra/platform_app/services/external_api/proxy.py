"""
ExternalAPIProxy: centralized HTTP proxy for user-app external calls.

Enforces method allow-listing, prepends base_url, applies default headers,
and rate-limits requests using a simple token-bucket via Django cache.
"""

import logging
import time
from typing import Any, Dict, List, Optional

import requests as http_client
from django.core.cache import cache

logger = logging.getLogger(__name__)

_DEFAULT_TIMEOUT = 30
_RATE_WINDOW = 60  # seconds


class MethodNotAllowedError(ValueError):
    """Raised when the requested method is not in the allowed list."""


class RateLimitExceededError(Exception):
    """Raised when the per-user per-api rate limit is exceeded."""


class ExternalAPIProxy:
    """
    Proxy for a single external API configured via a manifest.

    Args:
        app_name:   Name of the user app owning this proxy.
        api_config: Dict from the manifest containing:
                      base_url   (str)       — required
                      methods    (list[str]) — allowed HTTP methods
                      rate_limit (int)       — max requests per minute per user
                      headers    (dict)      — default request headers
    """

    def __init__(self, app_name: str, api_config: Dict[str, Any]) -> None:
        self.app_name = app_name
        self.base_url = api_config["base_url"].rstrip("/")
        self.allowed_methods: List[str] = [
            m.upper() for m in api_config.get("methods", ["GET"])
        ]
        self.rate_limit: int = int(api_config.get("rate_limit", 60))
        self.default_headers: Dict[str, str] = dict(api_config.get("headers", {}))
        self.timeout: int = int(api_config.get("timeout", _DEFAULT_TIMEOUT))

    # ------------------------------------------------------------------ #
    # Public interface                                                      #
    # ------------------------------------------------------------------ #

    def request(
        self,
        method: str,
        path: str,
        params: Optional[Dict] = None,
        data: Optional[Dict] = None,
        headers: Optional[Dict] = None,
        user_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Forward an HTTP request to the external API.

        Returns:
            Parsed JSON response as a dict.

        Raises:
            MethodNotAllowedError: Method not in the allowed list.
            RateLimitExceededError: Per-user rate limit exceeded.
            requests.HTTPError: Non-2xx response from the upstream API.
            requests.Timeout: Upstream API did not respond in time.
        """
        self._validate_method(method)
        if user_id is not None:
            self._check_rate_limit(user_id)

        url = self._build_url(path)
        merged_headers = {**self.default_headers, **(headers or {})}

        logger.debug("[ExternalAPI] %s %s (app=%s)", method.upper(), url, self.app_name)

        response = http_client.request(
            method.upper(),
            url,
            params=params,
            json=data,
            headers=merged_headers,
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()

    def get(
        self,
        path: str,
        params: Optional[Dict] = None,
        user_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Convenience wrapper for GET requests."""
        return self.request("GET", path, params=params, user_id=user_id)

    def post(
        self,
        path: str,
        data: Optional[Dict] = None,
        user_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Convenience wrapper for POST requests."""
        return self.request("POST", path, data=data, user_id=user_id)

    # ------------------------------------------------------------------ #
    # Helpers                                                               #
    # ------------------------------------------------------------------ #

    def _build_url(self, path: str) -> str:
        return self.base_url + "/" + path.lstrip("/")

    def _validate_method(self, method: str) -> None:
        if method.upper() not in self.allowed_methods:
            raise MethodNotAllowedError(
                f"Method '{method.upper()}' is not allowed for this API. "
                f"Allowed: {self.allowed_methods}"
            )

    def _rate_limit_key(self, user_id: int) -> str:
        return f"ext_api_rl:{self.app_name}:{user_id}"

    def _check_rate_limit(self, user_id: int) -> None:
        """Simple sliding-window token bucket stored in Django cache."""
        key = self._rate_limit_key(user_id)
        now = time.time()
        window_start = now - _RATE_WINDOW

        timestamps: List[float] = cache.get(key, [])
        timestamps = [ts for ts in timestamps if ts > window_start]

        if len(timestamps) >= self.rate_limit:
            retry_after = int(_RATE_WINDOW - (now - timestamps[0]))
            raise RateLimitExceededError(
                f"Rate limit of {self.rate_limit} requests/minute exceeded. "
                f"Retry after {retry_after}s."
            )

        timestamps.append(now)
        cache.set(key, timestamps, timeout=_RATE_WINDOW + 10)


# EOF
