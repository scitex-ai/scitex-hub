"""App management API — programmatic control of SciTeX apps.

All functions use verb forms. Works both inside containers
(via env vars and local files) and from the Django side (via registry).
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


def get_current() -> str:
    """Get the name of the currently active app.

    Reads from SCITEX_CURRENT_APP environment variable.
    Returns empty string if not set.
    """
    return os.environ.get("SCITEX_CURRENT_APP", "")


def list_all(*, server_url: Optional[str] = None) -> list[dict]:
    """List all available apps.

    If running inside Django, reads from the registry directly.
    Otherwise, queries the server API.
    """
    # Try Django registry first
    try:
        from apps.infra.workspace_app.registry import get_all_modules

        return [
            {
                "name": m.name,
                "label": m.label,
                "icon": m.icon_fa,
                "order": m.order,
                "ai_hint": m.ai_hint,
                "accent_color": m.accent_color,
                "is_dev": m.is_dev,
            }
            for m in get_all_modules()
        ]
    except ImportError:
        pass

    # Fallback: server API
    url = server_url or os.environ.get("SCITEX_HUB_URL", "http://127.0.0.1:8000")
    return _fetch_app_list(url)


def get_info(app_name: str) -> dict[str, Any]:
    """Get detailed info for a specific app from its manifest.

    Tries Django registry first, then falls back to reading
    manifest.json from the app directory.
    """
    # Try Django registry
    try:
        from apps.infra.workspace_app.registry import get_module

        mod = get_module(app_name)
        if mod:
            return {
                "name": mod.name,
                "label": mod.label,
                "app_name": mod.app_name,
                "icon": mod.icon_fa,
                "order": mod.order,
                "keyboard_shortcut": mod.keyboard_shortcut,
                "ai_hint": mod.ai_hint,
                "accent_color": mod.accent_color,
                "url": mod.get_url(),
                "license": mod.license,
                "allowed_extensions": mod.allowed_extensions,
            }
    except ImportError:
        pass

    # Fallback: read local manifest.json
    manifest_path = Path("manifest.json")
    if manifest_path.is_file():
        return json.loads(manifest_path.read_text(encoding="utf-8"))

    return {}


def switch_to(app_name: str) -> bool:
    """Switch the active app.

    Sets the SCITEX_CURRENT_APP env var for the current process.
    For browser-side switching, use the UI automation API.
    """
    os.environ["SCITEX_CURRENT_APP"] = app_name
    logger.info("[appmaker.api] Switched to app: %s", app_name)
    return True


def install_app(
    app_name: str, *, server_url: Optional[str] = None, token: Optional[str] = None
) -> dict:
    """Install an app from the store.

    Requires authentication. Returns result dict with success/error.
    """
    url = server_url or os.environ.get("SCITEX_HUB_URL", "http://127.0.0.1:8000")
    endpoint = f"{url.rstrip('/')}/apps/store/api/install/"

    import requests

    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    try:
        resp = requests.post(
            endpoint,
            json={"module_name": app_name},
            headers=headers,
            timeout=30,
        )
        return resp.json()
    except Exception as exc:
        return {"success": False, "error": str(exc)}


def _fetch_app_list(server_url: str) -> list[dict]:
    """Fetch app list from server API."""
    import requests

    endpoint = f"{server_url.rstrip('/')}/apps/store/api/list/"
    try:
        resp = requests.get(endpoint, timeout=15)
        data = resp.json()
        return data.get("apps", [])
    except Exception as exc:
        logger.warning("[appmaker.api] Failed to fetch app list: %s", exc)
        return []


# EOF
