#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Manifest loader — top-level entry point that ties parser, validator,
and registry together.

Usage:
    from apps.platform_app.manifest.loader import load_app_from_manifest

    config = load_app_from_manifest("/path/to/manifest.yaml", project=my_project)
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Union

logger = logging.getLogger(__name__)


def load_app_from_manifest(
    manifest_path: Union[str, Path],
    project=None,
) -> "ModuleConfig":
    """
    Parse, validate, and register an app described by a manifest.yaml file.

    Steps:
      1. Parse the YAML via ManifestParser.
      2. Validate all fields via validate_manifest(); raise on errors.
      3. Build a ModuleConfig from the manifest fields.
      4. Register any external_apis in the ExternalAPI registry.
      5. Parse any datastore schemas via parse_manifest_schema().
      6. Register the ModuleConfig in the workspace registry.

    Args:
        manifest_path: Path to the manifest.yaml file.
        project: Optional Django project model instance (stored for reference).

    Returns:
        The registered ModuleConfig instance.

    Raises:
        ManifestError: If the manifest is structurally or semantically invalid.
        FileNotFoundError: If the manifest file does not exist.
    """
    from apps.platform_app.manifest.parser import ManifestError, ManifestParser
    from apps.platform_app.manifest.validator import validate_manifest
    from apps.platform_app.services.datastore.schema import parse_manifest_schema
    from apps.platform_app.services.external_api.registry import register_api
    from apps.workspace_app.registry import register_module

    parser = ManifestParser()
    manifest = parser.parse(manifest_path)

    errors = validate_manifest(manifest)
    if errors:
        raise ManifestError(
            f"Manifest '{manifest_path}' has {len(errors)} validation error(s):\n"
            + "\n".join(f"  - {e}" for e in errors)
        )

    config = _build_module_config(manifest, project)

    _register_external_apis(manifest, config.name, register_api)
    _register_datastore_schemas(manifest, parse_manifest_schema)

    register_module(config)
    logger.info(
        "[manifest.loader] Registered app '%s' from %s", config.name, manifest_path
    )

    return config


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _build_module_config(manifest: dict, project) -> "ModuleConfig":
    """Construct a ModuleConfig from manifest fields."""
    from apps.workspace_app.registry import ModuleConfig

    name = manifest["name"]
    label = manifest["label"]
    icon = manifest["icon"]
    description = manifest.get("description", "")

    # Derive app_name: use project slug if available, else name
    app_name = getattr(project, "slug", None) or name

    return ModuleConfig(
        name=name,
        label=label,
        app_name=app_name,
        icon_fa=icon,
        partial_template=f"apps_app/user_apps/{name}_partial.html",
        context_builder="apps.apps_app.services.app_context.build_user_app_context",
        keyboard_shortcut=manifest.get("keyboard_shortcut", ""),
        order=int(manifest.get("order", 90)),
        accent_color=manifest.get("accent_color", ""),
        license=manifest.get("license", "AGPL-3.0"),
        ai_hint=description,
        default_enabled=False,
        status="wip",
    )


def _register_external_apis(manifest: dict, app_name: str, register_api) -> None:
    """Register all external_apis declared in the manifest."""
    external_apis = manifest.get("external_apis")
    if not external_apis:
        return

    for api_name, api_config in external_apis.items():
        try:
            register_api(app_name, api_name, dict(api_config))
            logger.debug(
                "[manifest.loader] Registered external API '%s' for app '%s'",
                api_name,
                app_name,
            )
        except Exception as exc:
            logger.warning(
                "[manifest.loader] Could not register API '%s' for '%s': %s",
                api_name,
                app_name,
                exc,
            )


def _register_datastore_schemas(manifest: dict, parse_manifest_schema) -> None:
    """Parse all schemas in the datastore section (validates at load time)."""
    datastore = manifest.get("datastore")
    if not datastore:
        return

    for schema_name in datastore:
        try:
            parse_manifest_schema(manifest, schema_name)
            logger.debug("[manifest.loader] Parsed datastore schema '%s'", schema_name)
        except Exception as exc:
            logger.warning(
                "[manifest.loader] Datastore schema '%s' parse error: %s",
                schema_name,
                exc,
            )


# EOF
