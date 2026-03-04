#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Manifest validator — deep-validates a parsed manifest dict.

Usage:
    from apps.platform_app.manifest.validator import validate_manifest

    errors = validate_manifest(manifest_dict)
    if errors:
        raise ValueError("\\n".join(errors))
"""

from __future__ import annotations

import re
from typing import Any

from apps.platform_app.services.datastore.schema import ALLOWED_FIELD_TYPES

# Semver: major.minor.patch, optionally with pre-release and build metadata.
_SEMVER_RE = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-((?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)"
    r"(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?"
    r"(?:\+([0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?$"
)

# App name: lowercase letters, digits, and hyphens only.
_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")

ALLOWED_CATEGORIES = {
    "analysis",
    "visualization",
    "writing",
    "data",
    "productivity",
    "science",
    "communication",
    "developer",
    "other",
}

ALLOWED_CHANNEL_TYPES = {"broadcast", "presence", "ot"}


def validate_manifest(manifest: dict) -> list[str]:
    """
    Deep-validate a parsed manifest dict.

    Args:
        manifest: Dict returned by ManifestParser.parse().

    Returns:
        List of human-readable error strings. Empty list means valid.
    """
    errors: list[str] = []

    _validate_name(manifest.get("name"), errors)
    _validate_version(manifest.get("version"), errors)
    _validate_icon(manifest.get("icon"), errors)
    _validate_category(manifest.get("category"), errors)

    datastore = manifest.get("datastore")
    if datastore is not None:
        _validate_datastore(datastore, errors)

    jobs = manifest.get("jobs")
    if jobs is not None:
        _validate_jobs(jobs, errors)

    external_apis = manifest.get("external_apis")
    if external_apis is not None:
        _validate_external_apis(external_apis, errors)

    channels = manifest.get("channels")
    if channels is not None:
        _validate_channels(channels, errors)

    return errors


# ---------------------------------------------------------------------------
# Field-level validators
# ---------------------------------------------------------------------------


def _validate_name(name: Any, errors: list[str]) -> None:
    if not isinstance(name, str) or not name:
        errors.append("'name' must be a non-empty string.")
        return
    if not _NAME_RE.match(name):
        errors.append(
            f"'name' must be lowercase alphanumeric with optional hyphens, "
            f"got '{name}'."
        )


def _validate_version(version: Any, errors: list[str]) -> None:
    if not isinstance(version, str) or not version:
        errors.append("'version' must be a non-empty string.")
        return
    if not _SEMVER_RE.match(str(version)):
        errors.append(f"'version' must follow semver (e.g. 1.0.0), got '{version}'.")


def _validate_icon(icon: Any, errors: list[str]) -> None:
    if not isinstance(icon, str) or not icon:
        errors.append("'icon' must be a non-empty string.")
        return
    if not (icon.startswith("fas ") or icon.startswith("far ")):
        errors.append(
            f"'icon' must start with 'fas ' or 'far ' (FontAwesome), got '{icon}'."
        )


def _validate_category(category: Any, errors: list[str]) -> None:
    if not isinstance(category, str) or not category:
        errors.append("'category' must be a non-empty string.")
        return
    if category not in ALLOWED_CATEGORIES:
        errors.append(
            f"'category' must be one of {sorted(ALLOWED_CATEGORIES)}, got '{category}'."
        )


def _validate_datastore(datastore: Any, errors: list[str]) -> None:
    if not isinstance(datastore, dict):
        errors.append("'datastore' must be a mapping of schema definitions.")
        return
    for schema_name, schema_def in datastore.items():
        prefix = f"datastore.{schema_name}"
        if not isinstance(schema_def, dict):
            errors.append(f"'{prefix}' must be a mapping.")
            continue
        fields = schema_def.get("fields", {})
        if not isinstance(fields, dict):
            errors.append(f"'{prefix}.fields' must be a mapping.")
            continue
        for field_name, field_def in fields.items():
            if not isinstance(field_def, dict):
                errors.append(f"'{prefix}.fields.{field_name}' must be a mapping.")
                continue
            field_type = field_def.get("type")
            if not field_type:
                errors.append(f"'{prefix}.fields.{field_name}' is missing 'type'.")
            elif field_type not in ALLOWED_FIELD_TYPES:
                errors.append(
                    f"'{prefix}.fields.{field_name}.type' is '{field_type}'; "
                    f"must be one of {sorted(ALLOWED_FIELD_TYPES)}."
                )


def _validate_jobs(jobs: Any, errors: list[str]) -> None:
    if not isinstance(jobs, dict):
        errors.append("'jobs' must be a mapping of job definitions.")
        return
    for job_name, job_def in jobs.items():
        prefix = f"jobs.{job_name}"
        if not isinstance(job_def, dict):
            errors.append(f"'{prefix}' must be a mapping.")
            continue
        if not job_def.get("handler"):
            errors.append(f"'{prefix}' is missing required 'handler' field.")


def _validate_external_apis(external_apis: Any, errors: list[str]) -> None:
    if not isinstance(external_apis, dict):
        errors.append("'external_apis' must be a mapping of API definitions.")
        return
    for api_name, api_def in external_apis.items():
        prefix = f"external_apis.{api_name}"
        if not isinstance(api_def, dict):
            errors.append(f"'{prefix}' must be a mapping.")
            continue
        if not api_def.get("base_url"):
            errors.append(f"'{prefix}' is missing required 'base_url' field.")


def _validate_channels(channels: Any, errors: list[str]) -> None:
    if not isinstance(channels, dict):
        errors.append("'channels' must be a mapping of channel definitions.")
        return
    for channel_name, channel_def in channels.items():
        prefix = f"channels.{channel_name}"
        if not isinstance(channel_def, dict):
            errors.append(f"'{prefix}' must be a mapping.")
            continue
        channel_type = channel_def.get("type")
        if not channel_type:
            errors.append(f"'{prefix}' is missing required 'type' field.")
        elif channel_type not in ALLOWED_CHANNEL_TYPES:
            errors.append(
                f"'{prefix}.type' is '{channel_type}'; "
                f"must be one of {sorted(ALLOWED_CHANNEL_TYPES)}."
            )


# EOF
