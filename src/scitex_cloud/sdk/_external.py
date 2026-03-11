"""External API proxy client — rate-limited third-party API calls.

REST endpoint:
  POST /platform/api/external/<api_name>/
"""

from __future__ import annotations

from typing import Any, Optional

from ._client import get_client


def proxy(
    api_name: str,
    *,
    method: str = "GET",
    path: str = "",
    params: Optional[dict] = None,
    data: Optional[dict] = None,
) -> dict:
    """Call a whitelisted external API via the Platform proxy."""
    client = get_client()
    body: dict[str, Any] = {"method": method}
    if path:
        body["path"] = path
    if params:
        body["params"] = params
    if data:
        body["data"] = data
    return client.request("POST", f"/platform/api/external/{api_name}/", data=body)


# EOF
