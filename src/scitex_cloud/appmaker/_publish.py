#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Publish a SciTeX app to the cloud server."""

from __future__ import annotations

import json
from pathlib import Path


def publish(app_dir: str | Path, server_url: str, token: str) -> dict:
    """Validate locally then submit the app for review via JWT endpoint.

    Parameters
    ----------
    app_dir : path
        Directory containing the app with manifest.json.
    server_url : str
        Base URL of the SciTeX Cloud server (e.g. http://127.0.0.1:8000).
    token : str
        JWT access token (Bearer auth).

    Returns
    -------
    dict
        Server response with 'success' and 'pr_url' keys.
    """
    import requests

    from ._validate import validate

    app_path = Path(app_dir).resolve()

    # Local validation first
    errors = validate(str(app_path))
    if errors:
        return {"success": False, "errors": errors}

    # Read manifest
    manifest_path = app_path / "manifest.json"
    if not manifest_path.is_file():
        return {"success": False, "errors": ["manifest.json not found"]}

    with open(manifest_path, encoding="utf-8") as f:
        manifest = json.load(f)

    project_name = manifest.get("name", app_path.name)

    # Submit via JWT-authenticated endpoint
    url = f"{server_url.rstrip('/')}/api/apps/submit/"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    payload = {
        "project_name": project_name,
        "manifest": manifest,
    }
    resp = requests.post(url, headers=headers, json=payload, timeout=30)
    return resp.json()


# EOF
