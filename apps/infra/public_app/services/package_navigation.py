"""Thin host adapter for SDK package navigation; no package inventory here."""


def build_package_navigation(distributions):
    """Report discovery state separately from stable allocation metadata."""
    try:
        from scitex_sdk.app.package_navigation import (
            PackageNavigationUnavailable,
            build_package_navigation as project,
        )
    except ImportError:
        return _unknown("unavailable")
    try:
        return {"discovery": "available", **project(distributions)}
    except PackageNavigationUnavailable:
        return _unknown("unavailable")
    except (ValueError, OSError):
        return _unknown("invalid")


def _unknown(state):
    # No catalog was read: selected packages must not be called unindexed.
    return {
        "schema_version": 1, "discovery": state, "trees": [], "packages": [],
        "unindexed": None, "declarations_only": True, "live_verified": False,
    }
