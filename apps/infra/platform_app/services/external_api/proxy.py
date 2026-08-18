"""
ExternalAPIProxy: centralized HTTP proxy for user-app external calls.

Enforces method allow-listing, prepends base_url, applies default headers,
and rate-limits requests using a simple token-bucket via Django cache.
"""

import logging
import time
from typing import Any, Dict, List, Optional
from urllib.parse import unquote, urljoin, urlsplit

import requests as http_client
from django.core.cache import cache

logger = logging.getLogger(__name__)

_DEFAULT_TIMEOUT = 30
_RATE_WINDOW = 60  # seconds


class MethodNotAllowedError(ValueError):
    """Raised when the requested method is not in the allowed list."""


class PathEscapesBaseURLError(ValueError):
    """Raised when `path` resolves outside the API's configured base_url."""


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
        """Join `path` onto base_url, refusing anything that escapes it.

        `path` is caller-supplied (external_proxy reads it straight out of the
        request body), so this is a containment boundary, not a formatting
        helper.

        NORMALISE FIRST, THEN CHECK. The bug this replaces was not a missing
        check — it was concatenation whose result only *looked* contained:
        `base + "/" + path.lstrip("/")` renders "../admin" as the harmless
        string ".../v1/../admin", and then `requests` resolves the `..` at send
        time. The string that was inspected and the URL that went on the wire
        were different. urljoin resolves the traversal up front so the value
        checked here is the value sent.

        Containment is COMPONENT-WISE, not a prefix match: a prefix test lets
        base "https://api.example.com/v1" accept "https://api.example.com/v1x".
        """
        # Refuse protocol-relative input EXPLICITLY rather than defusing it.
        # `path.lstrip("/")` below would turn "//evil.net/x" into the relative
        # segment "evil.net/x", which is safe but silently sends the caller
        # somewhere they plainly did not ask for. A caller writing "//host/..."
        # means an origin, so say no instead of quietly rewriting it.
        if path.startswith("//"):
            raise PathEscapesBaseURLError(
                f"path {path!r} is protocol-relative and would name a "
                f"different origin. Pass a path relative to base_url "
                f"({self.base_url}) for api '{self.app_name}'."
            )

        candidate = urljoin(self.base_url + "/", path.lstrip("/"))
        base, got = urlsplit(self.base_url), urlsplit(candidate)

        # urljoin honours an absolute URL in `path` and would swap the host out
        # entirely, so origin is checked explicitly rather than assumed.
        if (got.scheme, got.netloc) != (base.scheme, base.netloc):
            raise PathEscapesBaseURLError(
                f"path {path!r} resolves to {got.scheme}://{got.netloc}, "
                f"outside the configured base_url "
                f"{base.scheme}://{base.netloc} for api '{self.app_name}'. "
                f"Pass a path relative to base_url, not an absolute URL."
            )

        base_parts = [p for p in base.path.split("/") if p]

        # Checked TWICE: once as sent, once as the upstream might decode it.
        # urljoin resolves "../" but treats "..%2Fadmin" as a single opaque
        # segment, so an encoded separator survives this check and then
        # traverses on any upstream that percent-decodes before routing. We do
        # not know which upstreams do — and "unknown" is not "safe" — so a path
        # that escapes under EITHER reading is refused.
        for label, candidate_path in (
            ("resolves to", got.path),
            ("percent-decodes to", unquote(got.path)),
        ):
            got_parts = [p for p in candidate_path.split("/") if p]
            # Re-resolve the decoded form: "/v1/../admin" must collapse before
            # comparison, or the ".." lands in got_parts as a literal segment
            # and the prefix check passes it.
            if ".." in got_parts:
                got_parts = [
                    p
                    for p in urlsplit(
                        urljoin(f"{candidate_path}", ".")
                    ).path.split("/")
                    if p
                ]
            if got_parts[: len(base_parts)] != base_parts:
                raise PathEscapesBaseURLError(
                    f"path {path!r} {label} {candidate_path!r}, which escapes "
                    f"the base_url path {base.path!r} for api "
                    f"'{self.app_name}'. Remove the '..' segments (encoded or "
                    f"not); a path may only address resources under base_url."
                )

        return candidate

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
