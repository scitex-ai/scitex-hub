"""Per-user app preferences — stored as JSON at ~/.scitex/hub/apps/prefs.json.

No database needed. Each user has a single JSON file with per-app preferences.

Path migrated from ~/.scitex/cloud/ to ~/.scitex/hub/ per ADR-0003 §A.2 (Q2=b).
A compat symlink ~/.scitex/cloud -> ~/.scitex/hub stays for the deprecation
window so external tooling that still hardcodes the old path keeps working.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Optional

from scitex_config._ecosystem import local_state

logger = logging.getLogger(__name__)


def _default_prefs_path() -> Path:
    return local_state.path("hub", "apps", "prefs.json")


def get_prefs(app_name: str, *, prefs_path: Optional[Path] = None) -> dict[str, Any]:
    """Get saved preferences for an app.

    Returns empty dict if no preferences saved.
    """
    path = prefs_path or _default_prefs_path()
    all_prefs = _load_prefs(path)
    return all_prefs.get(app_name, {})


def set_prefs(
    app_name: str,
    prefs: dict[str, Any],
    *,
    prefs_path: Optional[Path] = None,
) -> None:
    """Save preferences for an app. Merges with existing preferences."""
    path = prefs_path or _default_prefs_path()
    all_prefs = _load_prefs(path)
    existing = all_prefs.get(app_name, {})
    existing.update(prefs)
    all_prefs[app_name] = existing
    _save_prefs(path, all_prefs)
    logger.info("[appmaker.prefs] Saved prefs for %s", app_name)


def delete_prefs(app_name: str, *, prefs_path: Optional[Path] = None) -> bool:
    """Delete all preferences for an app. Returns True if prefs existed."""
    path = prefs_path or _default_prefs_path()
    all_prefs = _load_prefs(path)
    if app_name in all_prefs:
        del all_prefs[app_name]
        _save_prefs(path, all_prefs)
        return True
    return False


def list_prefs(*, prefs_path: Optional[Path] = None) -> dict[str, Any]:
    """List all saved preferences for all apps."""
    path = prefs_path or _default_prefs_path()
    return _load_prefs(path)


def _load_prefs(path: Path) -> dict[str, Any]:
    """Load preferences from JSON file."""
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("[appmaker.prefs] Failed to load %s: %s", path, e)
        return {}


def _save_prefs(path: Path, data: dict[str, Any]) -> None:
    """Save preferences to JSON file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


# EOF
