"""Platform API HTTP client — shared base for all platform service wrappers.

Auth resolution: SCITEX_API_TOKEN env var (JWT).
URL resolution: SCITEX_API_URL env var (default: http://127.0.0.1:8000).
"""

from __future__ import annotations

import json
import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)


class PlatformClient:
    """Low-level HTTP client for Platform REST APIs."""

    def __init__(
        self,
        token: Optional[str] = None,
        base_url: Optional[str] = None,
    ):
        self.token = token or os.environ.get("SCITEX_API_TOKEN", "")
        self.base_url = (
            base_url or os.environ.get("SCITEX_API_URL") or "http://127.0.0.1:8000"
        ).rstrip("/")

    def request(
        self,
        method: str,
        endpoint: str,
        data: Optional[dict] = None,
        params: Optional[dict] = None,
        files: Optional[dict] = None,
    ) -> dict:
        """Make authenticated HTTP request to Platform API."""
        import requests

        url = f"{self.base_url}{endpoint}"
        headers = {"X-Requested-With": "XMLHttpRequest"}

        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        method = method.upper()
        if method == "GET":
            resp = requests.get(url, headers=headers, params=params, timeout=60)
        elif method == "POST":
            if files:
                resp = requests.post(
                    url, headers=headers, data=data, files=files, timeout=120
                )
            else:
                resp = requests.post(url, headers=headers, json=data, timeout=60)
        elif method == "PUT":
            resp = requests.put(url, headers=headers, json=data, timeout=60)
        elif method == "DELETE":
            resp = requests.delete(url, headers=headers, params=params, timeout=60)
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")

        resp.raise_for_status()

        try:
            return resp.json()
        except json.JSONDecodeError:
            return {"content": resp.text}


# Module-level singleton (lazy)
_default_client: Optional[PlatformClient] = None


def get_client() -> PlatformClient:
    """Get or create the default PlatformClient singleton."""
    global _default_client
    if _default_client is None:
        _default_client = PlatformClient()
    return _default_client


def reset_client() -> None:
    """Reset the default client (useful after env var changes)."""
    global _default_client
    _default_client = None


# EOF
