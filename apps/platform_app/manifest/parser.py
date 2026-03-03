#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ManifestParser — reads and validates a manifest.yaml file for platform apps.

Usage:
    from apps.platform_app.manifest.parser import ManifestParser, ManifestError

    parser = ManifestParser()
    data = parser.parse("/path/to/manifest.yaml")
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Union

logger = logging.getLogger(__name__)

# Required top-level fields that every manifest must declare.
REQUIRED_FIELDS = {"name", "label", "version", "icon", "category", "description"}

# Optional top-level fields (presence is accepted but not enforced).
OPTIONAL_FIELDS = {
    "datastore",
    "jobs",
    "external_apis",
    "channels",
    "scitex_modules",
    "skill",
    "keyboard_shortcut",
    "order",
    "accent_color",
    "license",
}

ALL_KNOWN_FIELDS = REQUIRED_FIELDS | OPTIONAL_FIELDS


class ManifestError(ValueError):
    """Raised when a manifest.yaml is missing required fields or has bad structure."""


class ManifestParser:
    """Parses a manifest.yaml file and returns a validated dict."""

    def parse(self, manifest_path: Union[str, Path]) -> dict:
        """
        Read and do a top-level structural validation of manifest.yaml.

        Args:
            manifest_path: Filesystem path to the manifest.yaml file.

        Returns:
            Parsed manifest dict with all top-level keys preserved.

        Raises:
            ManifestError: On missing required fields or invalid top-level structure.
            FileNotFoundError: If the file does not exist.
        """
        path = Path(manifest_path)
        if not path.is_file():
            raise FileNotFoundError(f"Manifest not found: {path}")

        raw = self._read_yaml(path)
        self._validate_structure(raw, path)
        logger.debug("[ManifestParser] Parsed manifest: %s", path)
        return raw

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _read_yaml(self, path: Path) -> dict:
        """Load YAML from disk, raising ManifestError on parse failure."""
        try:
            import yaml
        except ImportError as exc:
            raise ManifestError(
                "PyYAML is required to parse manifest files. "
                "Install it with: pip install pyyaml"
            ) from exc

        try:
            with path.open("r", encoding="utf-8") as fh:
                data = yaml.safe_load(fh)
        except Exception as exc:
            raise ManifestError(f"Failed to parse YAML in '{path}': {exc}") from exc

        if not isinstance(data, dict):
            raise ManifestError(
                f"manifest.yaml must be a YAML mapping at the top level, "
                f"got {type(data).__name__} in '{path}'."
            )

        return data

    def _validate_structure(self, data: dict, path: Path) -> None:
        """Check that all required fields are present."""
        missing = REQUIRED_FIELDS - set(data.keys())
        if missing:
            raise ManifestError(
                f"manifest.yaml '{path}' is missing required fields: {sorted(missing)}"
            )

        unknown = set(data.keys()) - ALL_KNOWN_FIELDS
        if unknown:
            logger.warning(
                "[ManifestParser] Unknown fields in '%s': %s (they will be ignored)",
                path,
                sorted(unknown),
            )


# EOF
