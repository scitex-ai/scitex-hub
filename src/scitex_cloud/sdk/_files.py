"""FileVault client — per-app namespaced file storage.

REST endpoints:
  GET    /platform/api/files/<app>/                 (list root)
  GET    /platform/api/files/<app>/<file_path>      (read file)
  POST   /platform/api/files/<app>/<file_path>      (upload/write)
  DELETE /platform/api/files/<app>/<file_path>       (delete file)
"""

from __future__ import annotations

from typing import Any, Optional, Union

from ._client import get_client


def list_files(
    app: str,
    *,
    path: str = "",
    project: Optional[str] = None,
    extensions: Optional[str] = None,
) -> dict:
    """List files in an app's vault."""
    client = get_client()
    params: dict[str, Any] = {}
    if project:
        params["project"] = project
    if extensions:
        params["extensions"] = extensions

    endpoint = f"/platform/api/files/{app}/"
    if path:
        endpoint = f"/platform/api/files/{app}/{path}"
    return client.request("GET", endpoint, params=params)


def download(app: str, file_path: str, *, project: Optional[str] = None) -> dict:
    """Download a file from the vault."""
    client = get_client()
    params: dict[str, Any] = {}
    if project:
        params["project"] = project
    return client.request(
        "GET", f"/platform/api/files/{app}/{file_path}", params=params
    )


def upload(
    app: str,
    file_path: str,
    content: Union[str, bytes],
    *,
    project: Optional[str] = None,
) -> dict:
    """Upload a file to the vault."""
    client = get_client()
    data: dict[str, Any] = {}
    if project:
        data["project"] = project

    if isinstance(content, bytes):
        files = {"file": (file_path.split("/")[-1], content)}
        return client.request(
            "POST", f"/platform/api/files/{app}/{file_path}", data=data, files=files
        )
    else:
        data["content"] = content
        return client.request(
            "POST", f"/platform/api/files/{app}/{file_path}", data=data
        )


def delete(app: str, file_path: str, *, project: Optional[str] = None) -> dict:
    """Delete a file from the vault."""
    client = get_client()
    params: dict[str, Any] = {}
    if project:
        params["project"] = project
    return client.request(
        "DELETE", f"/platform/api/files/{app}/{file_path}", params=params
    )


# EOF
