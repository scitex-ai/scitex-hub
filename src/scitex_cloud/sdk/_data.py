"""DataStore client — CRUD + search for app-scoped JSON data.

REST endpoints:
  GET/POST   /platform/api/data/<app>/<schema>/
  GET/PUT/DELETE /platform/api/data/<app>/<schema>/<pk>/
  POST       /platform/api/data/<app>/<schema>/search/
"""

from __future__ import annotations

from typing import Any, Optional

from ._client import get_client


def create(app: str, schema: str, data: dict, **kwargs: Any) -> dict:
    """Create a new record in the DataStore."""
    client = get_client()
    return client.request("POST", f"/platform/api/data/{app}/{schema}/", data=data)


def list_records(
    app: str,
    schema: str,
    *,
    filters: Optional[dict] = None,
    project_id: Optional[str] = None,
) -> dict:
    """List records for an app/schema, optionally filtered."""
    client = get_client()
    params = filters or {}
    if project_id:
        params["project_id"] = project_id
    return client.request("GET", f"/platform/api/data/{app}/{schema}/", params=params)


def get(app: str, schema: str, record_id: str) -> dict:
    """Get a single record by ID."""
    client = get_client()
    return client.request("GET", f"/platform/api/data/{app}/{schema}/{record_id}/")


def update(app: str, schema: str, record_id: str, data: dict) -> dict:
    """Update a record by ID."""
    client = get_client()
    return client.request(
        "PUT", f"/platform/api/data/{app}/{schema}/{record_id}/", data=data
    )


def delete(app: str, schema: str, record_id: str) -> dict:
    """Delete a record by ID."""
    client = get_client()
    return client.request("DELETE", f"/platform/api/data/{app}/{schema}/{record_id}/")


def search(app: str, schema: str, query: str) -> dict:
    """Full-text search across records."""
    client = get_client()
    return client.request(
        "POST", f"/platform/api/data/{app}/{schema}/search/", data={"query": query}
    )


# EOF
