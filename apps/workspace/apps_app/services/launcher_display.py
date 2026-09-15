"""Validated per-user launcher display overrides."""

from __future__ import annotations

import re

from .launcher_links import _owner_installation

DISPLAY_OVERRIDES_KEY = "launcher_display_overrides"
FAVORITES_KEY = "launcher_favorites"
_ICON_RE = re.compile(
    r"^(?:fas|far|fab|fal|fad|fat|fa-solid|fa-regular|fa-brands|fa-light|fa-duotone|fa-thin) fa-[a-z0-9-]+$"
)
_COLOR_RE = re.compile(r"^#[0-9a-fA-F]{6}$")


class DisplayOverrideRejected(ValueError):
    """A display override that is unsafe or malformed."""


def get_display_overrides(user) -> dict[str, dict[str, str]]:
    if not getattr(user, "is_authenticated", False):
        return {}
    installation = _owner_installation(user, create=False)
    saved = (
        (installation.config or {}).get(DISPLAY_OVERRIDES_KEY, {})
        if installation
        else {}
    )
    if not isinstance(saved, dict):
        return {}
    clean = {}
    for name, value in saved.items():
        if not isinstance(name, str):
            continue
        try:
            clean[name] = validate_display_override(value)
        except DisplayOverrideRejected:
            continue
    return clean


def validate_display_override(data) -> dict[str, str]:
    if not isinstance(data, dict):
        raise DisplayOverrideRejected("Request body must be an object.")
    display_name = data.get("display_name", "")
    icon = data.get("icon", "")
    icon_color = data.get("icon_color", "")
    if not all(isinstance(value, str) for value in (display_name, icon, icon_color)):
        raise DisplayOverrideRejected("Display values must be strings.")
    display_name = display_name.strip()
    icon = " ".join(icon.strip().split())
    icon_color = icon_color.strip().lower()
    if not display_name or len(display_name) > 100:
        raise DisplayOverrideRejected("Display name must be 1-100 characters.")
    if icon and not _ICON_RE.fullmatch(icon):
        raise DisplayOverrideRejected("Icon must be a Font Awesome class pair.")
    if icon_color and not _COLOR_RE.fullmatch(icon_color):
        raise DisplayOverrideRejected("Icon color must be a six-digit hex color.")
    return {"display_name": display_name, "icon": icon, "icon_color": icon_color}


def save_display_override(user, module_name: str, override: dict[str, str] | None) -> None:
    installation = _owner_installation(user, create=True)
    if installation is None:
        raise DisplayOverrideRejected("Launcher owner is not installed.")
    config = dict(installation.config or {})
    overrides = dict(config.get(DISPLAY_OVERRIDES_KEY, {}))
    if override is None:
        overrides.pop(module_name, None)
    else:
        overrides[module_name] = override
    if overrides:
        config[DISPLAY_OVERRIDES_KEY] = overrides
    else:
        config.pop(DISPLAY_OVERRIDES_KEY, None)
    installation.config = config
    installation.save(update_fields=["config"])


def get_favorites(user) -> list[str]:
    """Return ordered shortcut ids from the launcher owner's config."""
    if not getattr(user, "is_authenticated", False):
        return []
    installation = _owner_installation(user, create=False)
    saved = (installation.config or {}).get(FAVORITES_KEY, []) if installation else []
    if not isinstance(saved, list):
        return []
    return list(dict.fromkeys(name for name in saved if isinstance(name, str) and name))


def save_favorite(user, module_name: str, favorite: bool) -> None:
    installation = _owner_installation(user, create=True)
    if installation is None:
        raise DisplayOverrideRejected("Launcher owner is not installed.")
    config = dict(installation.config or {})
    favorites = get_favorites(user)
    if favorite and module_name not in favorites:
        favorites.append(module_name)
    elif not favorite:
        favorites = [name for name in favorites if name != module_name]
    if favorites:
        config[FAVORITES_KEY] = favorites
    else:
        config.pop(FAVORITES_KEY, None)
    installation.config = config
    installation.save(update_fields=["config"])
