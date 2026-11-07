"""Installed Hub identity shared by template adapters and runtime checks."""

from importlib.metadata import PackageNotFoundError, metadata


def get_hub_package_metadata() -> dict[str, str]:
    """Read the wheel/editable distribution, without guessing from checkout files."""
    try:
        installed = metadata("scitex-hub")
    except PackageNotFoundError:
        return {"name": "scitex-hub", "version": "unknown", "description": ""}
    return {
        "name": installed.get("Name", "scitex-hub"),
        "version": installed.get("Version", "unknown"),
        "description": installed.get("Summary", ""),
    }
